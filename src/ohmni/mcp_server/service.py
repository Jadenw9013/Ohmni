"""Direct Python service calls; no engineering verdict logic or EDA orchestration."""

import hashlib
import json
from pathlib import Path

import pydantic

from ..catalog.loader import JsonPartCatalog
from ..domain.circuit import CircuitIR
from ..domain.requirements import RequirementsSpec
from ..domain.verification import RuleOutcome
from ..verifier.engine import verify
from ..verifier.registry import all_rules
from .schemas import (
    MAX_ARGUMENT_BYTES,
    MAX_COMPONENTS,
    MAX_CONNECTIONS,
    MAX_NETS,
    MAX_STRING_LENGTH,
    Capabilities,
    GetPartRequest,
    InputModel,
    ListPartsRequest,
    PartDetail,
    PartPage,
    PartSummary,
    VerificationResult,
    VerifyRequest,
)

TOOLS = ("get_capabilities", "list_parts", "get_part", "verify_circuit")
LIMITATIONS = [
    "Semantic verification only. No ERC, DRC, PCB, routing, SPICE or fabrication was run.",
    ("The bundled catalog retains its source labels; catalog-reported facts are not "
     "machine-verified datasheet evidence or live supplier facts."),
    "Circuit intent, external sources and requirements are caller proposals, not measurements.",
    "No blockers is not full verification: inspect coverage, undecided rules and subsystem status.",
    "Parent hashes are untrusted history hints; this stateless server attests no revision lineage.",
]


def content_hash(value) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False,
    ).encode("utf-8")).hexdigest()


def verifier_fingerprint() -> str:
    """Identify installed semantic implementation, independently of the old report_id."""
    root = Path(__file__).resolve().parents[1]
    sources = {}
    for package in ("domain", "verifier"):
        for path in sorted((root / package).rglob("*.py")):
            sources[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return content_hash({"sources": sources, "pydantic": pydantic.__version__})


class SemanticService:
    def __init__(self):
        # Private startup snapshot. Clients can discover it but cannot replace it.
        self.catalog = JsonPartCatalog()
        self.catalog_hash = content_hash([
            part.model_dump(mode="json") for part in self.catalog.all_parts()
        ])
        self.verifier_hash = verifier_fingerprint()

    def get_capabilities(self, request: InputModel) -> Capabilities:
        return Capabilities(
            tools=list(TOOLS), catalog_hash=self.catalog_hash, verifier_hash=self.verifier_hash,
            rule_ids=[rule.rule_id for rule in all_rules()],
            limits={"max_components": MAX_COMPONENTS, "max_nets": MAX_NETS,
                    "max_connections": MAX_CONNECTIONS, "max_string_length": MAX_STRING_LENGTH,
                    "max_argument_bytes": MAX_ARGUMENT_BYTES},
            limitations=LIMITATIONS,
        )

    def list_parts(self, request: ListPartsRequest) -> PartPage:
        parts = self.catalog.all_parts()
        end = request.offset + request.limit
        return PartPage(
            catalog_hash=self.catalog_hash, total=len(parts), offset=request.offset,
            parts=[PartSummary(part_id=p.part_id, manufacturer=p.manufacturer, mpn=p.mpn,
                               category=p.category.value) for p in parts[request.offset:end]],
            next_offset=end if end < len(parts) else None,
        )

    def get_part(self, request: GetPartRequest) -> PartDetail:
        part = self.catalog.get(request.part_id)
        if part is None:
            raise KeyError("PART_NOT_FOUND")
        return PartDetail(catalog_hash=self.catalog_hash, part=part.model_copy(deep=True))

    def verify_circuit(self, request: VerifyRequest) -> VerificationResult:
        data = request.model_dump(mode="json")
        circuit = CircuitIR.model_validate(data["circuit"])
        requirements = (RequirementsSpec.model_validate(data["requirements"])
                        if data["requirements"] is not None else None)
        report = verify(circuit, self.catalog, requirements)
        scope_supported = requirements.is_supported_scope if requirements is not None else None
        limitations = list(LIMITATIONS)
        if scope_supported is False:
            limitations.append("Declared requirements are outside Ohmni's supported scope; "
                               "no validated-design claim is permitted.")
        elif scope_supported is None:
            limitations.append("No requirements were supplied; supported scope is unspecified.")
        # Rule failures retain ERROR and missing verdicts; internal tracebacks are not public data.
        for result in report.results:
            if result.outcome is RuleOutcome.ERROR:
                result.error_text = "Rule execution failed; verdict unavailable."
                result.limitations = ["This rule did not complete; its verdict is unavailable."]
        return VerificationResult(
            input_hash=content_hash({"schema_version": "1", "request": data,
                                     "catalog_hash": self.catalog_hash,
                                     "verifier_hash": self.verifier_hash}),
            catalog_hash=self.catalog_hash, verifier_hash=self.verifier_hash,
            requirements_supported=scope_supported, report=report,
            undecided_rule_ids=[rule.rule_id for rule in report.undecided_rules],
            limitations=limitations,
        )
