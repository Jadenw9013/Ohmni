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

def classify_assembly(bom:Bom,catalog:PartCatalog|None=None)->AssemblyReport:
    """Keep catalog hand-solderability distinct from package difficulty.

    A supplied catalog must match the full BOM identity and footprint before
    its guidance is used. Without a catalog, preserve the existing package-name
    estimates; neither path establishes that a board has been assembled.
    """
    risks=[];hand_solderable=[]
    for line in bom.lines:
        name=line.identity.package.upper();under=any(x in name for x in ("LGA","QFN","DFN","BGA"))
        if "THT" in name or "2.54" in name:d=AssemblyDifficulty.EASY
        elif "BGA" in name:d=AssemblyDifficulty.UNSUPPORTED_FOR_HAND_ASSEMBLY
        elif under:d=AssemblyDifficulty.REFLOW_RECOMMENDED
        elif any(x in name for x in ("0805","SOT","MODULE","USB-C")):d=AssemblyDifficulty.MODERATE
        else:d=AssemblyDifficulty.UNKNOWN
        detail="underside pads require reflow/hot-air access" if under else "package-based deterministic classification"
        decision=d in {AssemblyDifficulty.EASY,AssemblyDifficulty.MODERATE}
        if catalog is not None:
            spec=catalog.get(line.identity.part_id)
            package=spec.package(line.identity.package) if spec else None
            matching=(package is not None and spec.manufacturer==line.identity.manufacturer
                      and spec.mpn==line.identity.mpn and (package.kicad_footprint or "")==line.footprint)
            if not matching:
                d=AssemblyDifficulty.UNKNOWN;decision=None
                detail="No exact catalog part, manufacturer, package and footprint match; assembly guidance is unknown."
            elif "hand_solderable" not in package.model_fields_set:
                d=AssemblyDifficulty.UNKNOWN;decision=None
                detail="The catalog package has no explicitly recorded hand-solderability guidance."
            else:
                decision=package.hand_solderable
                if decision:
                    if name.startswith("SOIC-"):
                        d=AssemblyDifficulty.MODERATE
                    elif d in {AssemblyDifficulty.REFLOW_RECOMMENDED,AssemblyDifficulty.UNSUPPORTED_FOR_HAND_ASSEMBLY}:
                        # Contradictory name-based and catalog guidance must
                        # remain a review item, not an invented easy package.
                        d=AssemblyDifficulty.UNKNOWN
                    detail="The exact catalog package is marked hand-solderable; difficulty is package-based guidance."
                    if d is AssemblyDifficulty.UNKNOWN:
                        detail+=" Its assembly difficulty is not classified."
                else:
                    if d not in {AssemblyDifficulty.REFLOW_RECOMMENDED,AssemblyDifficulty.UNSUPPORTED_FOR_HAND_ASSEMBLY}:
                        d=AssemblyDifficulty.DIFFICULT
                    detail="The exact catalog package is marked not hand-solderable; review the assembly method and equipment."
                if package.notes:
                    detail+=f" {package.notes}"
        orientation=line.identity.part_id in {"GENERIC_LED_GREEN","USB_C_RECEPTACLE_16P"}
        hand_solderable.append(decision)
        risks.append(AssemblyRisk(references=line.references,package=line.identity.package,difficulty=d,exposed_or_underside_pads=under,orientation_sensitive=orientation,detail=detail))
    satisfied=bool(hand_solderable) and all(value is True for value in hand_solderable)
    events=[_event(bom.circuit_fingerprint,EventKind.ASSEMBLY_RISK_IDENTIFIED,f"Assembly risk: {x.package}",x.model_dump(mode="json")) for x in risks if x.difficulty not in {AssemblyDifficulty.EASY,AssemblyDifficulty.MODERATE}]
    limitations=["Classification is package-based guidance, not a guarantee of assembly success."]
    if catalog is not None:
        limitations.append("Hand-solderability uses exact catalog package guidance, not machine-verified assembly or a bench result.")
    return AssemblyReport(risks=risks,hand_solder_requirement_satisfied=satisfied,limitations=limitations,events=events)

def _event(circuit_hash,kind,summary,payload):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit_hash,payload=payload)
