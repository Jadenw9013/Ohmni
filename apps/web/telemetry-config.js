// Public browser telemetry configuration. Served as a static snapshot asset.
//
// Disabled by default: the facade never loads the SDK bundle unless `enabled`
// is exactly true and every field below validates. Enabling it is an
// owner-approved public-config deployment (see docs/hackathon/SENTRY_CORE_RESULTS.md).
// Only public values belong here: a frontend DSN is public by design; the backend
// DSN, auth tokens and source-map upload credentials never do.
export const TELEMETRY_CONFIG = Object.freeze({
    enabled: false,
    dsn: "",
    environment: "local",
    release: "",
    // Exact API origin that may receive a trace header, for a cross-origin API.
    // Empty means the page's own origin (the Vercel /api rewrite or the local server).
    apiOrigin: "",
    traceSampleRate: 0,
});
