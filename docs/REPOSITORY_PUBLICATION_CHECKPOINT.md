# Repository publication checkpoint

Date: 2026-10-02. Scope: `REPO-READY-1`; task: `REPO-T01`.

The user authorized preparing, committing and pushing the existing local work to
`main`. This includes the previously uncommitted component-synthesis source,
audit remediation, reference documentation and development ledger, alongside the
already committed component library, disposable placement sandbox and UI redesign.
Approval is recorded in `.ai/approvals/REPO-READY-1.yaml`.

## Published source and local checks

Source commit: `7efe78b94577103303df231bc84a30a2eede5be6`. Published to `origin/main` by non-force
fast-forward. The final ledger/evidence commit follows this source snapshot.

- Full committed-tree suite: **1847 passed, 2 skipped** in 235.74 s.
- Corpus: **108 passed**, 1741 deselected.
- Frontend: **203 passed**, no failures or skips.
- Workflow: **11 passed**. Ruff and all **14** product fixtures passed.
- KiCad component proof: **36** asset checks passed; native symbol/footprint
  renders and connected ERC/DRC completed.

## Fixes during publication preparation

- The real demo's earlier `pipeline_failed` was reproduced as a KiCad ERC timeout
  under filesystem sandbox restrictions. The same scripted `DemoPipeline` completed
  with normal local permissions and produced routing and fabrication artifacts.
  No engineering check was weakened to accommodate the sandbox.
- The Chromium smoke helper expected the project form at `/`. It now follows the
  landing page's visible **Build** link before checking and submitting the form.
  The actual browser regression passed after this correction.
- The slow routing/fabrication test changed the manufacturing profile version to
  `2.0`, which was already its value. It now derives a different version from the
  current value and asserts that the fingerprint changes before testing stale
  package rejection. The production fingerprint check was already correct.
- The workflow test now recognizes the explicit repository-publication approval.
- `.codex/` is ignored because its configuration contains a machine-specific
  executable path. Generated outputs, PDFs, databases and environment files remain
  local. Reference illustrations and their inventory are included as source inputs;
  their package hashes and sizes were checked.

## Verification and reproduction

Exact final commands, counts, commit identity and limitations are recorded in
`.ai/verification/REPO-T01.yaml`. Use the project virtual environment. Run pytest
tiers sequentially because the canonical runner shares a temporary directory.

```text
python scripts/ai_state.py validate
python scripts/verify.py full
python scripts/verify.py corpus
python scripts/verify.py workflow
node --test apps/web/tests/*.test.mjs
python -m ruff check .
python -m ohmni verify-all
python scripts/record_component_extraction.py --check
python scripts/component_cad_proof.py --out build/release-prep-component
```

The corpus gate requires the exact manufacturer PDF from
`python scripts/acquire_corpus.py`; absence must fail that gate. Actual KiCad tests
require local access to the installed CLI and its configuration. A skipped test
is not a passed check.

Local diagnostic artifacts (ignored by Git):

- `build/release-prep-full.txt`: initial failures and their tracebacks.
- `build/release-prep-browser.txt`: corrected Chromium navigation regression.
- `build/release-prep-node.txt`: standalone frontend suite.
- `build/release-prep-demo-diagnostic.txt`: sandbox timeout reproduction.
- `build/release-prep-demo-native/`: successful scripted engineering artifacts.
- `build/release-prep-component/CS-T04_evidence.json`: source receipts, 36 asset
  checks, hashes, native tool results and reconstructed-proposal provenance.
- `build/release-prep-component/renders/`: KiCad symbol and footprint SVGs.

## Handoff boundaries

Publication is not completion of the component-synthesis milestone. CS-T01 through
CS-T04 remain **VERIFIED**, pending the recorded independent-review and live
extraction-evaluation requirements. CS-T05 and CAB-T05 remain unstarted and held
by their incomplete dependencies. No imported component has been activated.

The replay fixture is **reconstructed**, not a witnessed live-model response.
No live provider evaluation was run for publication. Geometry and KiCad acceptance
do not establish IPC compliance, validated SPICE behavior or working hardware.

The isolated PDF worker is opt-in; the existing `ohmni ingest-datasheet` CLI still
parses in-process. The worker bounds resources but is not a security sandbox.
Independent accessibility and newcomer usability evaluation remain outstanding.
The Windows run does not prove POSIX behavior. Remote CI results must be observed
separately from local results. No direct deployment command or infrastructure
provisioning was performed. The existing Vercel Git integration reported success
for the pushed source commit; this task did not configure or invoke that integration.

For the next session: read `AGENTS.md`, this checkpoint, `.ai/state.yaml`,
`.ai/tasks.yaml`, the CS remediation records and the UX checkpoints. Validate
the ledger and inspect Git status. Do not start later product work merely because
the repository has been published.
