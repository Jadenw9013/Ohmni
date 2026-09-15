# Ohmni public release — DEPLOY-T01

The user explicitly authorized pushing and deploying the verified release.
The existing hosts are retained:

- Website: https://ohmni-yvnd.vercel.app
- Backend: https://ohmni-demo.fly.dev
- GitHub: https://github.com/Jadenw9013/Ohmni

Runtime release: `a619cbaf08f4eab1255f99d0d3028675a3ebe33b`, pushed to `main`
and `codex/personal-sensor-projects`. Later ledger/documentation commits do not
change the deployed application bytes.

Vercel deployment: `dpl_AWs7LPpsgmF1nDaSJ9UEr8Fq5zps`.
Fly image: `registry.fly.io/ohmni-demo:deployment-01M2HPQN6RAGYAWQ7PJSBGTS71`.
The existing single machine and persistent volume are reused.

## Packaging and deployment

Both deployment ignore files now exclude local credentials, private reference
inputs, agent configuration and nested development dependencies. The release
was uploaded from a clean Git archive, not the shared working directory.
Both Vercel configs explicitly skip dependency installation/build because the
static application and pinned vendor runtime are already committed. The
project root is `apps/web`; its output is `.`. The root configuration remains
usable with repository-root output `apps/web`.

Create archives with newline conversion disabled:

```powershell
git -c core.autocrlf=false archive --format=zip --output build/release.zip HEAD
```

Validate extracted paths stay within the release directory, private inputs are
absent, all 29 public assets match Git blob bytes, and
`scripts/docker-entrypoint.sh` contains no carriage returns before uploading.
The entrypoint is now pinned to LF in `.gitattributes` as well.

The first archive inherited Windows CRLF conversion. That broke the Linux
entrypoint at startup. The previous known-good backend image was restored and
its health checked before deploying the corrected archive. The initial failed
release was not accepted as a successful deployment. The locally installed
Vercel CLI 44.7.3 was also rejected by the service; CLI 59.17.0 was installed
under ignored `build/deployment-tools` and used through its documented
`dist/vc.js` entrypoint. No global CLI update was needed.

The corrected backend was deployed with:

```powershell
flyctl deploy --app ohmni-demo --remote-only --ha=false --update-only --yes
```

Vercel was linked to existing project `ohmni-yvnd`, staged with
`deploy --prod --skip-domain`, checked through authenticated `vercel curl`,
then promoted after the backend fingerprint matched. The existing API rewrite
continues to proxy `/api/*` to Fly. The UI protocol adopts the backend's
identity; live byte comparison separately establishes that both hosts serve
the intended frontend release.

Expected UI fingerprint:
`37bf50306208df88bf1a4209564e9bd6213ee138f2c786f3e667795ccfdcf946`.

## Verification and limits

The deployed homepage passed the real-browser regression at 1500, 849 and
390 px, including repeated keyboard entry, focus return and both board
viewers. Public screenshots are under
`out/deployment/public-browser/screenshots/`. The durable verification record
is `.ai/verification/DEPLOY-T01.yaml`; local detailed results are under
`out/deployment/`.

Independent live checks matched all 29 assets on both hosts (58 comparisons),
validated health and project-options contracts, and confirmed six private-path
requests returned 404. Both GitHub verification runs for the release succeeded.

Deployed job `18ea227ac5a6` generated the 29-component sensor/controller from
the confirmed example brief. Its canonical circuit hash matches the saved
showcase: `96245a408b92518aeb6f11d968c7bc4ba1000e735a0b99da1130fd8fc9afb80e`.
It completed semantic checks, ERC with retained warnings, physical checks,
72 required routed connections, DRC with zero violations/unrouted connections,
and the synthetic manufacturing review. Its downloadable ZIP passed integrity
checking and contained the PCB fingerprint reported by that job. The clearly
labeled release-check project remains in the deployed workspace.

This publishes the verified product version. It does not resolve the separate
124-body scene's unknown electrical identities, add firmware or bench evidence,
or make the demo an enterprise-hardened service. Its illustrative label and the
actual board's recorded limits remain visible.
