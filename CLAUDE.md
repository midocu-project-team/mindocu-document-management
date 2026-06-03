# CLAUDE.md

Guidance for working in this repository.

## Project

**mindocu** is a case-file document-management pipeline. Input is a (often
scanned) multi-document PDF "Akte" (case file); the system reads it, splits it
into the individual documents it contains, and classifies them. It is a
student project (Professionelles Projektmanagement, WI semester 6).

The pipeline has three stages, each with its own dataclass output (see
[backend/README.md](backend/README.md) for ASCII schema diagrams):

1. **Read** (`reader.py`) — PDF → `CaseFileDocument`: OCR/parse the PDF into
   structured, machine-readable pages and blocks. **Implemented.**
2. **Segment** (`segmentation.py`) — `CaseFileDocument` → `SegmentationResult`:
   detect document boundaries and group pages into `DocumentSegment`s. **Stub.**
3. **Label/Classify** (`labeling.py`) — classify each segment. **Stub.**

## Conventions

- **All code comments and docstrings MUST be written in English**, even though
  the team communicates in German and the README files are German. Commit
  messages are English too. (Historic German comments were already translated.)
- **Commit messages**: Conventional Commits (https://conventionalcommits.org),
  e.g. `feat(reader): ...`, `chore: ...`. Prefer small, frequent commits.
- **Git workflow**: never push to `main` directly; branch per feature
  (`feature/...`, `fix/...`, `docs/...`), PR + one approval, then merge.
- Type hints use modern syntax (`X | None`, `list[...]`), not `Optional`/`List`.

## Environment & commands

- Package/env manager is **uv** (not pip). Python **3.13** (`.python-version`).
- Dependencies live in `pyproject.toml` + `uv.lock` — always commit both together.

```bash
uv sync                              # create .venv + install locked deps
uv add <pkg>            / uv add --dev <pkg>      # add deps (never pip install)
uv run python -m backend.reader      # run a module (run from repo root)
uv run pytest                        # tests
```

Code is imported as a namespace package: `from backend.datatypes import ...`.
There are **no `__init__.py` files** (PEP 420 namespace packages), so always
run from the repo root, otherwise the `backend.` imports won't resolve.

## Code layout (`backend/`)

| File | Role |
| --- | --- |
| `datatypes.py` | All dataclasses (the pipeline's data contract). No logic. |
| `reader.py` | Stage 1: PDF → `CaseFileDocument`. The only substantial code. |
| `segmentation.py` | Stage 2 stub (`segment_document`). |
| `labeling.py` | Stage 3 stub (`label_document`). |
| `tests/explore/explore.py` | Scratch script for trying docling features (kept). |

`reader.py` is organized into three banner-delimited sections that map to the
natural seams of stage 1 (kept in one file on purpose — see "Architecture
notes"): **OCR / PDF conversion**, **Document assembly** (`read_document`, the
entry point), and **DocItem → ContentBlock mapping**.

## docling knowledge (hard-won; read before touching `reader.py`)

The reader is built on **docling**. These points are non-obvious and were
verified empirically against the test PDFs:

- **`document.iterate_items()`** does a depth-first walk of the body tree in
  reading order. With the default `with_groups=False` it yields only `DocItem`s
  (no `GroupItem`s) and **only the `BODY` content layer** — page headers/footers
  (`FURNITURE`), watermarks, etc. are excluded unless you pass
  `included_content_layers`. Picture children are not traversed by default.
- **DocItem hierarchy** drives the mapping dispatch in `item_to_blocks`:
  - `TextItem` (+ `TitleItem`, `SectionHeaderItem`, `ListItem`, `FormulaItem`,
    `CodeItem`, …) has `.text`; check `isinstance(TextItem)` **first** because
    `CodeItem` is also a `FloatingItem`.
  - `FloatingItem` (`TableItem`, `PictureItem`, `KeyValueItem`, `FormItem`) has
    no `.text`: tables → `export_to_markdown(doc)`, pictures → `caption_text(doc)`,
    key-value/form → join `graph.cells[].text`.
  - Bare `DocItem`s (`FieldRegionItem`, `FieldItem`) + anything unknown → generic
    fallback.
- **ProvenanceItem** (`page_no`, `bbox`, `charspan`): a single DocItem can have
  **multiple** provenance items. For `TextItem`s these can even span different
  pages, and `charspan` slices `item.text` per provenance — this is why blocks
  are produced **one per ProvenanceItem** and linked via `ContentBlock.source_ref`.
  `charspan` is only meaningful for `TextItem`s; it is `(0,0)` for tables etc.
  FloatingItems empirically have exactly one provenance (page-spanning is the
  only theoretical exception).
- **Bounding boxes** use `CoordOrigin.BOTTOMLEFT` (y grows upward). A
  top-left-origin frontend must flip y via the page height; bboxes are stored
  raw and converted later. `width_pt`/`height_pt` per page are kept for this.
- **Per-page confidence & OCR signal** come from `conversion_result.confidence`
  (a `ConfidenceReport`): `report.pages[n].mean_score` (`NaN` → `None`) and
  `was_ocr_applied = not isnan(report.pages[n].ocr_score)`. The cell-level
  `TextCell.from_ocr` flag is **not** usable post-conversion (cells are cleared
  during assembling). PDFs are often **mixed** — some pages have an embedded text
  layer (no OCR), others are scans (OCR), so this flag is genuinely per-page.
- **Page numbering** is 1-based and consistent across `document.pages`,
  `confidence.pages`, and `conversion_result.pages` (no off-by-one).
- **docling closes the input `BytesIO`** after reading, so capture
  `file.getbuffer().nbytes` *before* calling the converter.
- Pipeline runs **CPU-only** on purpose: Apple Silicon MPS lacks float64 which
  the RT-DETR layout model needs (it crashes otherwise). Full OCR is slow —
  ~7.5 s/page (the 375-page test scan took ~47 min).

## Architecture notes / decisions

- Stage 1 lives in a single `reader.py` (with section banners) rather than split
  into modules, because the mapping is conceptually *part of* reading. If it
  grows, the intended next step is a `reader/` package (not flat sibling files).
- `CaseFileDocument.document_id` auto-generates a UUID via
  `field(default_factory=..., kw_only=True)` — don't pass it manually.

## Known gaps / WIP

- `labeling.py` imports `Segment` and `LabeledSegment` from `datatypes.py`, but
  those types do **not exist** there yet — stage 3's data contract is unfinished.
- `segmentation.py` / `labeling.py` are bodyless stubs.
- `was_ocr_applied=True` was previously hardcoded; it is now derived, but page
  error handling (`CaseFileDocument.errors`) is still always `[]`.
