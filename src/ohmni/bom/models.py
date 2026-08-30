"""Identity-safe BOM, supplier, cost, and assembly models."""
from __future__ import annotations

import hashlib
import math
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field, model_validator

from ..domain.events import EngineeringEvent, EventKind


class ManufacturerPartIdentity(BaseModel):
    part_id:str
    manufacturer:str|None=None
    mpn:str|None=None
    package:str
    value_key:str|None=None

    @property
    def key(self):return (self.part_id,self.manufacturer,self.mpn,self.package,self.value_key)
class BomLine(BaseModel): identity:ManufacturerPartIdentity; description:str; quantity_per_board:int; references:list[str]; footprint:str; evidence_status:str
class Bom(BaseModel):
    circuit_fingerprint:str
    lines:list[BomLine]
    events:list[EngineeringEvent]=Field(default_factory=list)

    @property
    def reference_count(self):return sum(x.quantity_per_board for x in self.lines)
    @property
    def content_hash(self):return hashlib.sha256(self.model_dump_json(exclude={"events"}).encode()).hexdigest()
class PriceBreak(BaseModel): quantity:int=Field(ge=1); unit_price:Decimal=Field(ge=0)
class AvailabilityStatus(StrEnum): AVAILABLE="available"; UNAVAILABLE="unavailable"; UNKNOWN="unknown"
class SupplierOffer(BaseModel):
    supplier:str
    returned_identity:ManufacturerPartIdentity
    currency:str
    price_breaks:list[PriceBreak]
    moq:int=Field(default=1,ge=1)
    purchase_increment:int=Field(default=1,ge=1)
    available_quantity:int|None=None
    lifecycle:str|None=None
    verified_on:date
    provenance:str

    @model_validator(mode="after")
    def ordered(self):
        if [x.quantity for x in self.price_breaks]!=sorted(x.quantity for x in self.price_breaks):raise ValueError("price breaks must be ordered")
        return self
class SupplierLookupResult(BaseModel): requested_identity:ManufacturerPartIdentity; offer:SupplierOffer|None=None; error:str|None=None
class SupplierProvider(Protocol):
    def lookup(self,part:ManufacturerPartIdentity,quantity:int)->SupplierLookupResult:...
class StaticSupplierProvider:
    def __init__(self,offers:list[SupplierOffer]):self.offers={x.returned_identity.key:x for x in offers}
    def lookup(self,part,quantity):
        offer=self.offers.get(part.key)
        if offer is None:return SupplierLookupResult(requested_identity=part,error="UNKNOWN: no fixture offer")
        if offer.returned_identity.key!=part.key:return SupplierLookupResult(requested_identity=part,error="supplier identity mismatch")
        return SupplierLookupResult(requested_identity=part,offer=offer)
class CostKnowledge(StrEnum): KNOWN="known"; ESTIMATED="estimated"; UNKNOWN="unknown"
class BomLineCost(BaseModel): identity:ManufacturerPartIdentity; boards:int; consumed_quantity:int; purchase_quantity:int|None=None; leftovers:int|None=None; unit_price:Decimal|None=None; consumption_cost:Decimal|None=None; purchase_cost:Decimal|None=None; currency:str|None=None; knowledge:CostKnowledge; reason:str|None=None
class PrototypeCostReport(BaseModel): boards:int; lines:list[BomLineCost]; pricing_coverage:float; known_consumption_cost:Decimal; known_purchase_requirement:Decimal; fabrication:CostKnowledge=CostKnowledge.UNKNOWN; shipping:CostKnowledge=CostKnowledge.UNKNOWN; assembly:CostKnowledge=CostKnowledge.ESTIMATED; tooling:CostKnowledge=CostKnowledge.UNKNOWN; events:list[EngineeringEvent]=Field(default_factory=list)
class AssemblyDifficulty(StrEnum): EASY="easy"; MODERATE="moderate"; DIFFICULT="difficult"; REFLOW_RECOMMENDED="reflow_recommended"; UNSUPPORTED_FOR_HAND_ASSEMBLY="unsupported_for_hand_assembly"; UNKNOWN="unknown"
class AssemblyRisk(BaseModel): references:list[str]; package:str; difficulty:AssemblyDifficulty; exposed_or_underside_pads:bool=False; orientation_sensitive:bool=False; detail:str
class AssemblyReport(BaseModel): risks:list[AssemblyRisk]; hand_solder_requirement_satisfied:bool; limitations:list[str]=Field(default_factory=lambda:["Classification is package-based guidance, not a guarantee of assembly success."]); events:list[EngineeringEvent]=Field(default_factory=list)
class AffordabilityMode(StrEnum): CHEAPEST="cheapest"; EASIEST_TO_BUILD="easiest_to_build"; BALANCED="balanced"; SMALLEST="smallest"

def calculate_cost(bom:Bom,provider:SupplierProvider,boards:int)->PrototypeCostReport:
    lines=[];events=[]
    for line in bom.lines:
        consumed=line.quantity_per_board*boards;result=provider.lookup(line.identity,consumed)
        if not result.offer:
            lines.append(BomLineCost(identity=line.identity,boards=boards,consumed_quantity=consumed,knowledge=CostKnowledge.UNKNOWN,reason=result.error))
            events.append(_event(bom.circuit_fingerprint,EventKind.PRICING_UNKNOWN,f"Pricing unknown: {line.identity.part_id}",{"identity":line.identity.model_dump(mode="json"),"reason":result.error}))
            continue
        offer=result.offer;purchase=max(consumed,offer.moq);purchase=math.ceil(purchase/offer.purchase_increment)*offer.purchase_increment
        applicable=[x for x in offer.price_breaks if x.quantity<=purchase];price=(applicable[-1] if applicable else offer.price_breaks[0]).unit_price
        lines.append(BomLineCost(identity=line.identity,boards=boards,consumed_quantity=consumed,purchase_quantity=purchase,leftovers=purchase-consumed,unit_price=price,consumption_cost=price*consumed,purchase_cost=price*purchase,currency=offer.currency,knowledge=CostKnowledge.KNOWN))
        events.append(_event(bom.circuit_fingerprint,EventKind.SUPPLIER_OFFER_LOADED,f"Supplier offer loaded: {line.identity.part_id}",{"supplier":offer.supplier,"verified_on":offer.verified_on.isoformat(),"provenance":offer.provenance}))
    currencies={x.currency for x in lines if x.currency};
    if len(currencies)>1:raise ValueError("mixed currencies cannot be summed")
    known=[x for x in lines if x.knowledge is CostKnowledge.KNOWN]
    return PrototypeCostReport(boards=boards,lines=lines,pricing_coverage=len(known)/len(lines) if lines else 1,known_consumption_cost=sum((x.consumption_cost for x in known),Decimal(0)),known_purchase_requirement=sum((x.purchase_cost for x in known),Decimal(0)),events=events)

def _event(circuit_hash,kind,summary,payload):
    identity=f"{kind.value}:{summary}:{payload!r}";return EngineeringEvent(event_id=hashlib.sha256(identity.encode()).hexdigest()[:16],kind=kind,summary=summary,circuit_content_hash=circuit_hash,payload=payload)
