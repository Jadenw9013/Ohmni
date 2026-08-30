import hashlib
from datetime import date
from decimal import Decimal

from ..adapters import PartCatalog
from ..domain import CircuitIR, EngineeringEvent, EventKind
from .models import *


def generate_bom(circuit:CircuitIR,catalog:PartCatalog)->Bom:
    groups={}
    for item in sorted(circuit.components,key=lambda x:x.ref):
        spec=catalog.require(item.part_id);package=spec.package(item.package);value_key=item.value.model_dump_json() if item.value else None
        identity=ManufacturerPartIdentity(part_id=spec.part_id,manufacturer=spec.manufacturer,mpn=spec.mpn,package=item.package,value_key=value_key)
        key=identity.key
        if key not in groups:groups[key]=BomLine(identity=identity,description=spec.description,quantity_per_board=0,references=[],footprint=package.kicad_footprint or "",evidence_status="CATALOG_REPORTED")
        groups[key].quantity_per_board+=1;groups[key].references.append(item.ref)
    event=_event(circuit.content_hash,EventKind.BOM_GENERATED,"BOM generated",{"references":len(circuit.components),"unique_lines":len(groups)})
    return Bom(circuit_fingerprint=circuit.content_hash,lines=sorted(groups.values(),key=lambda x:(x.identity.part_id,x.identity.package,x.identity.value_key or "")),events=[event])

def synthetic_fixture_supplier(bom:Bom)->StaticSupplierProvider:
    offers=[]
    for index,line in enumerate(bom.lines):
        if line.identity.part_id=="BME280":continue # deliberate UNKNOWN coverage case
        base=Decimal("0.05")*(index+1)
        offers.append(SupplierOffer(supplier="OHMNI_SYNTHETIC_FIXTURE",returned_identity=line.identity,currency="USD",price_breaks=[PriceBreak(quantity=1,unit_price=base),PriceBreak(quantity=10,unit_price=(base*Decimal("0.8")).quantize(Decimal("0.001")))],moq=10 if line.identity.part_id in {"GENERIC_RESISTOR","GENERIC_CAPACITOR"} else 1,purchase_increment=1,available_quantity=1000,lifecycle="fixture-only",verified_on=date(2026,8,1),provenance="synthetic deterministic fixture; not live supplier data"))
    return StaticSupplierProvider(offers)

def classify_assembly(bom:Bom)->AssemblyReport:
    risks=[]
    for line in bom.lines:
        name=line.identity.package.upper();under=any(x in name for x in ("LGA","QFN","DFN","BGA"))
        if "THT" in name or "2.54" in name:d=AssemblyDifficulty.EASY
        elif "BGA" in name:d=AssemblyDifficulty.UNSUPPORTED_FOR_HAND_ASSEMBLY
        elif under:d=AssemblyDifficulty.REFLOW_RECOMMENDED
        elif any(x in name for x in ("0805","SOT","MODULE","USB-C")):d=AssemblyDifficulty.MODERATE
        else:d=AssemblyDifficulty.UNKNOWN
        orientation=line.identity.part_id in {"GENERIC_LED_GREEN","USB_C_RECEPTACLE_16P"}
        risks.append(AssemblyRisk(references=line.references,package=line.identity.package,difficulty=d,exposed_or_underside_pads=under,orientation_sensitive=orientation,detail="underside pads require reflow/hot-air access" if under else "package-based deterministic classification"))
    satisfied=not any(x.difficulty in {AssemblyDifficulty.REFLOW_RECOMMENDED,AssemblyDifficulty.UNSUPPORTED_FOR_HAND_ASSEMBLY,AssemblyDifficulty.UNKNOWN} for x in risks)
    events=[_event(bom.circuit_fingerprint,EventKind.ASSEMBLY_RISK_IDENTIFIED,f"Assembly risk: {x.package}",x.model_dump(mode="json")) for x in risks if x.difficulty not in {AssemblyDifficulty.EASY,AssemblyDifficulty.MODERATE}]
    return AssemblyReport(risks=risks,hand_solder_requirement_satisfied=satisfied,events=events)

def _event(circuit_hash,kind,summary,payload):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit_hash,payload=payload)
