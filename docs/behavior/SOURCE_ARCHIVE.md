# The source archive and how to reproduce it

Every value in the behavior records traces to a document: a manufacturer datasheet, a
specification or a catalogue. The fetch ledger, `out/component-behavior/run/FETCH_LEDGER.jsonl`,
records for each cited URL the sha256 and byte count of the document that was checked, when, with
which tool, or the named person who saved it from a browser. The audit (AUD-SOURCE-001) needs the
bytes themselves under `out/component-behavior/run/fetched-sources/<sha256>.bin` and re-hashes
them on every run.

## Why the bytes are not in the repository

The documents are copyrighted by their manufacturers. This repository is public, so it publishes
the ledger (what was checked, and its hash) but never the documents. That is the same boundary a
paper applies: it cites the datasheet, it does not reprint it.

## Rebuilding the archive from a clean checkout

```
python -m tools.behavior_audit rebuild-sources
```

re-downloads every successful ledger URL and stores a document only if its bytes hash to the
ledgered value. `SOURCE_REBUILD.json` in the run directory reports each URL as `rebuilt`, `present`,
`changed` (the host now serves different bytes; nothing is stored under the old hash), `unavailable`
(the host refused or failed) or `manual`. A `changed` or `unavailable` document is a real finding:
the ledger still proves what was checked, not that it can be fetched today, and the gap belongs in
`docs/behavior/SOURCE_BINDINGS.json` as a supersession (a replacement document, with what it
supports) or a manufacturer withdrawal (nothing primary exists any more, and no bound fact depends
on it).

`manual` rows are documents a named person saved from a browser because the host blocks scripted
downloads. They cannot be rebuilt automatically; the ledger names who saved them and when, and the
owner keeps the private archive bundle (see below) for them.

Run the command from a machine with ordinary network access. The cloud sandbox used for parts of
this work reaches only an allowlist of hosts and reports most manufacturers as `unavailable`.

## The owner's private bundle

The complete archive (383 documents, 413 MB) is kept by the repository owner outside the
repository as `fetched-sources.tar.gz`, with its sha256 beside it. Unpacking it into
`out/component-behavior/run/` restores every document, including the manual ones, so the source
audit passes on a fresh clone without any download. Reviewers who need the exact bytes ask the
owner for the bundle; it is not redistributed.

## What the audit accepts

- A cited URL with a successful ledger row whose archived bytes hash to the recorded value.
- A dead URL with an approved supersession in `SOURCE_BINDINGS.json` whose replacement document
  has its own successful archived fetch; partial support must explain the gap.
- A dead URL recorded as withdrawn by the manufacturer, only when a named person checked the
  manufacturer's own locations on a stated date and no gapfill fact or runtime recipe cites it.
  The spec's values stay as written and are flagged by that record; nothing simulable rests on them.
