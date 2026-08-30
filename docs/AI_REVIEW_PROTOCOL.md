# Independent AI development review protocol

Review the repository, not the implementer's summary. Read the approved scope,
task acceptance criteria, Git diff and changed files, architecture and decision
records, tests, verification record, and relevant product documentation.

Inspect correctness, missed requirements, regressions, edge cases, trust-boundary
violations, security/privacy, state/concurrency, failure behavior, tests that only
mirror implementation, accidental verification weakening, unnecessary complexity,
dead code, and documentation drift. Run appropriate gates where possible.

Record every review in `.ai/reviews.yaml`. Review status is `PENDING`, `PASSED`,
`FINDINGS_OPEN`, or `UNAVAILABLE`; self-review must set `independent: false` and
must not claim independent approval. Findings have stable IDs, scope, severity
(`BLOCKER`, `HIGH`, `MEDIUM`, `LOW`), status (`OPEN`, `FIXED`,
`INVALID_WITH_EVIDENCE`, `ACCEPTED_RISK`), description, affected files, found-at
commit, resolution commit/explanation, and verification evidence.

Never delete resolved findings. `INVALID_WITH_EVIDENCE` requires concrete
counter-evidence. Open `BLOCKER` or `HIGH` findings prevent completion. Medium/low
findings may remain only as explicitly recorded accepted risk. For a product
milestone, reviewer `UNAVAILABLE` permits `VERIFIED` but not `COMPLETE`; a human or
independent reviewer must close that gate.

