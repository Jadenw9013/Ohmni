"""The child half of bounded PDF observation: parse under a self-applied cap.

Run as ``python -m ohmni.datasheet.observation_worker <request.json> <outdir>``.
It is never imported by the parent, which is the point: the parse happens in a
process whose death is survivable.

Order matters here and is the whole design. The address-space cap is applied
*before* the parser library is imported and before a single byte of the document
is read, so there is no window in which this process can allocate without a
bound. If the cap cannot be applied, the worker exits with
:data:`EXIT_UNBOUNDED` and reads nothing at all.

Exit codes are the protocol. They are distinct so the parent can tell a refusal
the document earned (:data:`EXIT_REJECTED` -- an ingest status or an observation
bound) from a failure of the worker itself, and neither can arrive as an empty
success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

#: The parse ran and the bundle was written.
EXIT_OK = 0
#: The worker itself failed in a way the parent should treat as unavailable.
EXIT_FAILED = 1
#: The document was refused: a PDF ingest status or an observation bound.
EXIT_REJECTED = 3
#: No address-space cap could be applied, so nothing was parsed.
EXIT_UNBOUNDED = 4

#: A cap below this cannot host a running interpreter, so asking for one is a
#: configuration error rather than a tight bound. Refusing it explicitly keeps
#: the fail-closed path identical on every platform: Windows rejects such a
#: limit outright, while POSIX accepts it and the process then dies of memory
#: starvation somewhere unpredictable, which is a different code path.
MINIMUM_ADDRESS_SPACE_BYTES = 64 * 1024 * 1024


def _write(directory: Path, name: str, payload: dict) -> None:
    (directory / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        print("usage: observation_worker <request.json> <output-directory>", file=sys.stderr)
        return EXIT_FAILED
    request_path, output_directory = Path(arguments[0]), Path(arguments[1])
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"unreadable worker request: {exc}", file=sys.stderr)
        return EXIT_FAILED
    output_directory.mkdir(parents=True, exist_ok=True)

    # 1. Bound this process before anything expensive can be imported or read.
    from ..adapters.resource_limits import (
        ResourceLimitUnavailable,
        apply_address_space_limit,
        read_applied_limit,
    )

    try:
        requested = request["address_space_bytes"]
        if not isinstance(requested, int) or requested < MINIMUM_ADDRESS_SPACE_BYTES:
            raise ResourceLimitUnavailable(
                f"an address-space cap of {requested} bytes is below the "
                f"{MINIMUM_ADDRESS_SPACE_BYTES} byte floor a running parse needs"
            )
        mechanism = apply_address_space_limit(requested)
        # Read the cap back out of the kernel rather than echoing the request.
        # A reported bound that is only the number we asked for cannot witness a
        # mechanism that applied something else, or nothing at all.
        applied = read_applied_limit()
    except (ResourceLimitUnavailable, TypeError, ValueError, KeyError) as exc:
        _write(output_directory, "error.json", {
            "kind": "unbounded",
            "detail": f"no address-space cap could be applied: {exc}",
        })
        return EXIT_UNBOUNDED

    # 2. Only now does the parser library exist in this process.
    from .observations import ObservationLimitError
    from .pdf import BoundedObservationExtractor, PdfIngestError

    try:
        extractor = BoundedObservationExtractor(
            max_bytes=request["max_bytes"],
            render_dpi=request["render_dpi"],
        )
        bundle, images = extractor.observe(
            Path(request["path"]), request["pages"], render=request["render"]
        )
    except PdfIngestError as exc:
        _write(output_directory, "error.json", {
            "kind": "ingest", "status": str(exc.status), "detail": str(exc),
        })
        return EXIT_REJECTED
    except ObservationLimitError as exc:
        _write(output_directory, "error.json", {"kind": "limit", "detail": str(exc)})
        return EXIT_REJECTED
    except MemoryError as exc:
        # The cap did its job. This is a refusal, not a crash to hide.
        _write(output_directory, "error.json", {
            "kind": "limit",
            "detail": f"the parse exceeded its {mechanism} address-space cap: {exc}",
        })
        return EXIT_REJECTED
    except Exception as exc:  # noqa: BLE001 - an unexpected parser failure is a rejection
        _write(output_directory, "error.json", {
            "kind": "parser", "detail": f"{type(exc).__name__}: {exc}",
        })
        return EXIT_REJECTED

    for number, png in images.items():
        (output_directory / f"page{number}.png").write_bytes(png)
    _write(output_directory, "bundle.json", {
        "memory_mechanism": mechanism,
        "address_space_bytes": applied,
        "requested_address_space_bytes": request["address_space_bytes"],
        "rendered_pages": sorted(images),
        "bundle": bundle.model_dump(mode="json"),
    })
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover - exercised as a child process
    sys.exit(main())
