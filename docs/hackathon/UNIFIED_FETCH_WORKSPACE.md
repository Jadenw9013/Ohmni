# Fetch projects in the main Ohmni workspace

Fetch `OPEN` now returns a one-use, 30-minute connection link to the main Ohmni
site. The link joins the existing project to the browser's private workspace;
it does not copy the board or regenerate it. The same main UI provides the
project shelf, revision settings, board view, component tutor, board chat,
checks and downloads. A persistent HttpOnly cookie remembers access for 180 days.
There is no account/password login in this implementation. To open a Fetch
project in another browser, request a fresh `OPEN` link in its Fetch conversation.
Never share a connection link: it grants access to view and edit that project.

Projects created in the hosted main UI are private to that browser workspace too.
The former public demo server's project list is not imported: it has no ownership
records that would justify assigning someone else's demo projects to a browser.
The saved example remains available as an example. Clearing browser access means
reconnecting Fetch projects through Fetch; it does not delete their saved records.

## Saved conversations and edits

Board and per-component conversations are stored with the project revision in
SQLite, rather than with a temporary viewer link. They survive page refresh,
new connection links and service restarts. Older messages have pagination. The
AI receives bounded recent context, while older history remains available to read.
Existing viewer conversations are migrated once when their project is linked.
Saved planning requests are retained; unavailable historical assistant replies
are not reconstructed. New Fetch exchanges are also recorded in board history.

The main UI's detailed settings and board assistant create immutable revisions.
AI changes require review and an explicit save. Generation runs against that
saved revision; previous boards and checks remain attached to previous revisions.
Direct saves reject stale base revisions. Old chat proposals remain readable but
cannot be applied after expiry or restart. Fetch checks the latest UI-saved
revision before answering or proposing a further change.

Editing means the supported board families and configuration fields already
available in Ohmni. It is not arbitrary PCB trace editing. Teaching, illustrative
3D bodies, behavioral-model limits, firmware and physical-test limits remain
separate from the deterministic engineering results.

## Runtime boundary

Vercel rewrites `/connected/*` to the Fetch host. The gateway authenticates an
HttpOnly session, checks project/job/plan ownership, rejects cross-origin mutation
requests and forwards only explicitly classified routes to a loopback instance
of the existing main application handlers. The application shares the bridge's
JobStore, ProjectStore, planner, assistant and request budget. It does not claim a
second filesystem lock or recover active jobs a second time. No unguarded demo
project API is published on the Fetch host.

Connection credentials are removed from the fragment before the application and
telemetry load. The service stores their hashes, enforces atomic single-use
claims and permits retry only by the claiming session. Legacy viewer tokens
retain their old read/teach permissions and cannot claim editing access.

`OHMNI_MAIN_UI_URL` defaults to `https://ohmni-yvnd.vercel.app`. A local proxy can
set it to its own origin for testing. The main static assets are served by Vercel;
the Fly image contains the same assets for application identity and legacy links.
No API keys or session credentials enter committed artifacts.
