# Security and Safety

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
