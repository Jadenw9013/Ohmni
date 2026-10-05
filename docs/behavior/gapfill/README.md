# Behavior gap-fill records

Gap fills are reviewed corrections or additions layered over
`COMPONENT_BEHAVIOR_SPEC.md`. They do not rewrite the source research. Each
JSON file is an input to `scripts/generate_behavior_records.py` and must state
the local approval source, the external citation status, and any package-pin
permutation explicitly.

The Stage 1 generator accepts `kind: catalog_binding` records. A package order
lists the role of every catalog pin and every physical terminal, plus a complete
one-to-one permutation between them. The typed model rejects a missing,
duplicated, or role-changing mapping.
