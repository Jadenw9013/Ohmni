# Security and Safety

## Model proposal boundary

Model output is untrusted data validated against strict schemas. It cannot create
evidence, verification status, tool results, rule waivers, requirement changes, or EDA
file edits. Datasheet snippets are not placed into instruction text; planning uses
bounded structured facts with status and source identifiers. Repair operations target
only semantic circuit objects and are fingerprint-bound.

## Threat model

### Untrusted datasheets

Treat all document contents as data.

Do not allow datasheet text to override system instructions.

Never execute:
- embedded scripts
- document actions
- shell commands found in text
- URLs automatically

### File handling

- restrict file types
- cap file size
- parse PDFs in isolated process where practical
- sanitize filenames
- never trust user-supplied project paths

### Command execution

EDA tools should be invoked through fixed command templates.

Never interpolate arbitrary user text into shell commands.

Use argument arrays, not shell strings.

### Secrets

- API keys in environment variables
- never store secrets in generated KiCad project
- never place secrets in logs
- redact third-party responses when needed
- async demo failures expose a fixed public error, never exception-derived text
- demo diagnostics never serialize or log exception objects, values, tracebacks, or local paths
- demo jobs use exact owned envelopes; malformed state becomes a fixed terminal failure before status evaluation
- the local demo rejects non-finite JSON and emits neither access logs nor request-thread exception diagnostics
- the local demo maps one fixed fixture identifier (plus its exact legacy request) to a server-owned canonical request
- Windows demo servers claim their endpoint exclusively; bind failures emit only a fixed actionable startup message
- demo APIs, artifacts, and static UI assets are served with `Cache-Control: no-store`
- every demo-server process owns a distinct random instance identity and an isolated in-memory job store; job polling is generation-bound and a restarted server cannot adopt an old job identifier
- the four executable UI assets are read once into an immutable startup snapshot whose SHA-256 version is carried through health, job creation, polling, and response headers
- current clients bind job creation to the exact API, server instance, and UI snapshot; exact fixed-fixture and canonical-request payloads remain narrowly supported for pre-versioned local clients
- local API errors and job failures expose only allowlisted fixed codes; stderr diagnostics are flushed structured events containing no request bodies, exception strings, tracebacks, or filesystem paths
- demo initialization, endpoint binding, worker launch, pipeline execution, and server runtime failures remain distinct fixed diagnostic boundaries

## Electrical safety policy for MVP

Block automatic validated-design claims for:

- mains
- lithium battery charging/protection
- life support
- medical
- automotive safety
- explosive/pyrotechnic control
- high-current motor systems
- RF power amplifiers
- high-voltage supplies

## Bench automation

Future instrument control must enforce hard deterministic bounds:

- max voltage
- max current
- output-off default
- timeouts
- emergency stop
- user confirmation before energizing hardware

The LLM must never directly choose values outside the allowed envelope.
