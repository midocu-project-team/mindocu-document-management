# CLAUDE.md

Guidance for working in this repository.

## Project

**mindocu** is a case-file document-management pipeline. Input is a (often
scanned) multi-document PDF "Akte" (case file); the system reads it, splits it
into the individual documents it contains, and classifies them. It is a
student project (Professionelles Projektmanagement, WI semester 6).

The pipeline has three stages, each with its own dataclass output (see
[backend/README.md](backend/README.md) for ASCII schema diagrams):

The three stages live in the **`pipeline/` package** (`pipeline/reader/`,
`pipeline/segmentation/`, `pipeline/enrichment/`):

1. **Read** (`pipeline/reader/`) — PDF → `CaseFileDocument`: OCR/parse the PDF
   into structured, machine-readable pages and blocks. **Implemented** as a
   `ReaderStrategy` package; the docling-based reader is the only backend so far.
2. **Segment** (`pipeline/segmentation/`) — `CaseFileDocument` →
   `SegmentationResult`: detect document boundaries and group pages into
   `DocumentSegment`s. **Implemented** — a `SegmentationStrategy` package with
   two interchangeable LLM strategies (pairwise-boundary and full-context).
3. **Enrich** (`pipeline/enrichment/`) — `SegmentationResult` → `EnrichmentResult`:
   enrich each segment with a title, an AI summary and a keyword-based
   relevance flag. **Implemented** as an `EnrichmentStrategy` package; the
   first strategy combines the deterministic keyword relevance decision with
   per-segment LLM title/summary generation (gated on relevance).

## Conventions

- **All code comments and docstrings MUST be written in English**, even though
  the team communicates in German and the README files are German. Commit
  messages are English too. (Historic German comments were already translated.)
- **Commit messages**: Conventional Commits (https://conventionalcommits.org),
  e.g. `feat(reader): ...`, `chore: ...`. Prefer small, frequent commits.
- **Git workflow**: never push to `main` directly; branch per feature
  (`feature/...`, `fix/...`, `docs/...`), PR + one approval, then merge.
- Type hints use modern syntax (`X | None`, `list[...]`), not `Optional`/`List`.
- **Functional decomposition (Clean Code)**: keep functions small and
  single-concern — roughly **≤ 25 lines** of body. When a function grows past
  that or starts doing two things, **extract a named helper** instead of letting
  it sprawl. Push each concern into its own function: payload-building, the LLM
  call, deterministic repair, segment assembly are separate functions, not
  inline blocks. Keep **pure helpers free of instance state** and group them
  below the class (see the `# Pure helpers (no strategy state)` sections in the
  segmentation strategies) so the side-effecting orchestration and the pure,
  testable logic stay visibly separated.

## Environment & commands

- This is a monorepo: `backend/` (Python) and `frontend/` (web app). The Python
  project lives in **`backend/`** — run all `uv`/`pytest` commands from there.
- Package/env manager is **uv** (not pip). Python **3.13** (`.python-version`).
- Dependencies live in `backend/pyproject.toml` + `backend/uv.lock` — always
  commit both together.

```bash
cd backend
uv sync                              # create .venv + install locked deps
uv add <pkg>            / uv add --dev <pkg>      # add deps (never pip install)
uv run python -m evaluation          # run a module (run from backend/)
uv run pytest                        # tests
```

`backend/` is the import root, so modules are imported without a `backend.`
prefix: `from pipeline.datatypes import ...`, `from pipeline import
DoclingReaderStrategy`.
The `pipeline/__init__.py` is the **public interface** of the pipeline: it
re-exports every entry point meant for use from outside (stage entry points,
strategy ABCs and classes, option models). Code outside `pipeline/` imports
from `pipeline` directly — never from the stage subpackages (only unit tests
of private helpers import deep). Always run from `backend/`, otherwise the
imports won't resolve.

## Code layout (`backend/`)

| Path | Role |
| --- | --- |
| `pipeline/datatypes.py` | All dataclasses (the pipeline's data contract). No logic. |
| `pipeline/` | The three pipeline stages; `__init__.py` is the public interface (re-exports all outside-facing entry points). |
| `pipeline/reader/` | Stage 1: PDF → `CaseFileDocument` (strategy package). |
| `pipeline/reader/strategy.py` | `ReaderStrategy` ABC (the `read_document` contract). |
| `pipeline/reader/docling/` | Strategy: docling-based reader (`DoclingReaderStrategy`). |
| `pipeline/reader/docling/options.py` | OCR/pipeline config (`_default_pipeline_options`, `default_pdf_format_options`). |
| `pipeline/reader/docling/reader.py` | Document assembly: `DoclingReaderStrategy`, `ocr_convert_pdf`. |
| `pipeline/reader/docling/mapping.py` | DocItem → `ContentBlock` mapping. |
| `pipeline/segmentation/` | Stage 2: `CaseFileDocument` → `SegmentationResult` (strategy package). |
| `pipeline/segmentation/strategy.py` | `SegmentationStrategy` ABC (the `segment_document` contract). |
| `pipeline/segmentation/pairwise_boundary/` | Strategy: per-adjacent-pair boundary classification (N−1 LLM calls). |
| `pipeline/segmentation/full_context/` | Strategy: whole-document single-pass classification (one LLM call + windowing fallback). |
| `pipeline/segmentation/utils.py` | Shared, strategy-agnostic helpers (`make_segment`). |
| `llm/` | Interchangeable LLM backends behind one `LLMProvider` ABC (injected into stage-2/3 strategies). |
| `llm/provider.py` | `LLMProvider` ABC + backend-agnostic `LLMResponse` (text, token counts, durations in seconds). |
| `llm/ollama_provider.py` | Ollama backend; holds `num_ctx`/`keep_alive`/`think`; native grammar-constrained JSON. |
| `llm/mlx_provider.py` | mlx-lm backend (in-process, Apple Silicon); outlines for constrained JSON. |
| `pipeline/enrichment/` | Stage 3: `SegmentationResult` → `EnrichmentResult` (strategy package). |
| `pipeline/enrichment/strategy.py` | `EnrichmentStrategy` ABC (the `enrich_segments` contract). |
| `pipeline/enrichment/utils.py` | Strategy-agnostic keyword relevance (`RelevanceKeywords`, `decide_relevance`). |
| `pipeline/enrichment/keyword_relevance/` | Strategy: heading-keyword relevance + per-segment LLM title/summary (gated on relevance). |
| `logging_config.py` | `get_logger`; used across all stages. |
| `tests/explore/` | Scratch scripts for trying docling/segmentation features (kept). |

Stage 1 mirrors stages 2/3 as a **strategy package**: a `ReaderStrategy` ABC
(`strategy.py`, one `read_document` method) with one subpackage per backend.
The docling backend (`docling/`) is split along the natural seams of reading:
**options** (`options.py`), **document assembly** (`reader.py`,
`DoclingReaderStrategy` + the raw-conversion escape hatch `ocr_convert_pdf`),
and **DocItem → ContentBlock mapping** (`mapping.py`). Backend configuration
is constructor state: `DoclingReaderStrategy(pdf_format_options=...)` swaps
OCR engine, pipeline class or backend (`None` ⇒ the default options). The
output contract every reader backend must honor — 1-based page numbers,
bboxes in PDF points with a bottom-left origin — is pinned on `BoundingBox`
in `pipeline/datatypes.py`. Mapping helpers are module-private; the package
`__init__` re-exports the public entry points.

Stage 2 is the `pipeline/segmentation/` package built on the **strategy pattern**: a
`SegmentationStrategy` ABC (`strategy.py`) with one `segment_document` method,
and one subpackage per concrete strategy (`pairwise_boundary/`, `full_context/`),
each holding its own `prompt.py` + `segmentation.py`. Strategies take an
`LLMProvider` (from `llm/`) as a **required** constructor argument plus their
own config (the full-context one bundles it in a `FullContextOptions` object)
and are interchangeable. Both reuse `make_segment` from `pipeline/segmentation/utils.py`
rather than cross-importing between sibling strategy packages. The package
`__init__` re-exports the strategies.

Stage 3 mirrors stage 2: an `EnrichmentStrategy` ABC (`strategy.py`, one
`enrich_segments` method) with one subpackage per strategy. The **keyword
relevance decision is strategy-agnostic** and lives in `pipeline/enrichment/utils.py`:
a keyword fires on a case-insensitive substring hit in the text of a `HEADING`
block on any page of the segment; `relevant` matches beat `irrelevant` ones
(fail-safe toward keeping a document visible); no hit ⇒ `default_relevance`
(default `True`, blacklist style — a whitelist is `relevant`-only keywords
plus `default_relevance=False`). `matched_keywords` records only the winning
polarity's hits, so it always explains the decision. The keyword-relevance
strategy takes a **required** `LLMProvider` plus a `KeywordRelevanceOptions`
object and asks the LLM per segment for a title and a 2–4-sentence summary
(German prompt, head-truncated segment text via `max_input_chars`). The
relevance decision runs first and gates the call: irrelevant segments get no
LLM call by default (`enrich_irrelevant=False`). A failed call degrades only
that segment (`title`/`summary` = `None` + segment-scoped `EnrichmentError`);
the deterministic relevance always survives.

## docling knowledge (hard-won; read before touching `pipeline/reader/docling/`)

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
  This is pinned as the stage-1 contract on `BoundingBox` in
  `pipeline/datatypes.py` — any non-docling reader backend must emit it too.
- **Per-page confidence & OCR signal** come from `conversion_result.confidence`
  (a `ConfidenceReport`): `report.pages[n].mean_score` (`NaN` → `None`) and
  `was_ocr_applied = not isnan(report.pages[n].ocr_score)`. The cell-level
  `TextCell.from_ocr` flag is **not** usable post-conversion (cells are cleared
  during assembling). PDFs are often **mixed** — some pages have an embedded text
  layer (no OCR), others are scans (OCR), so this flag is genuinely per-page.
  **Caveat:** `ocr_score` is only populated by engines that report per-cell
  confidence (RapidOCR). The **default Tesseract CLI does not**, so `ocr_score`
  stays `NaN` and `was_ocr_applied` is `False` even on OCR'd pages — the per-page
  OCR signal is unreliable with the current default.
- **Page numbering** is 1-based and consistent across `document.pages`,
  `confidence.pages`, and `conversion_result.pages` (no off-by-one).
- **docling closes the input `BytesIO`** after reading, so capture
  `file.getbuffer().nbytes` *before* calling the converter.
- Pipeline runs **CPU-only** on purpose: Apple Silicon MPS lacks float64 which
  the RT-DETR layout model needs (it crashes otherwise). `AUTO` resolves to MPS
  on a Mac and would re-trigger that crash — keep CPU.
- **OCR engine: Tesseract CLI (`deu`+`eng`) by default** — ~7x faster on scanned
  PDFs than docling's RapidOCR (the 124-page test Akte: ~1 min vs ~8 min) at
  comparable quality. Needs the `tesseract` binary + `deu` language data on the
  host (`brew install tesseract tesseract-lang`). Born-digital pages cost ~0.1 s;
  only true scans are slow. Swappable via the `DoclingReaderStrategy`
  constructor (see below).

## Architecture notes / decisions

- Stage 1 is a **strategy package** like stages 2/3: a `ReaderStrategy` ABC
  plus the `docling/` backend subpackage (`options.py` / `reader.py` /
  `mapping.py`). Add a new reader backend (e.g. OpenDataLoader) as a new
  subpackage implementing `ReaderStrategy` — it must honor the bbox/page-number
  contract pinned in `pipeline/datatypes.py`, never by editing the docling one.
- `DoclingReaderStrategy` takes an optional `pdf_format_options` (a docling
  `PdfFormatOption`) as **constructor state** — the same principle as the LLM
  providers; `default_pdf_format_options()` builds the default (threaded
  pipeline, CPU, Tesseract). Pass a custom one to swap OCR engine, pipeline
  class or backend without touching the reading code.
  `CaseFileDocument.ocr_engine` is derived from the configured options
  (`kind:langs`, e.g. `tesseract:deu+eng`), not hardcoded.
- `CaseFileDocument.document_id` auto-generates a UUID via
  `field(default_factory=..., kw_only=True)` — don't pass it manually.
- Stage 2 is a **strategy package**: add a new approach as a subpackage under
  `pipeline/segmentation/` implementing `SegmentationStrategy`, not by editing an
  existing strategy. Each stage owns its error contract — stage 2 uses
  `SegmentationError` (`error_type` + `message` + optional `start_page`/`end_page`
  scope; both `None` ⇒ whole document), **not** the reader's `PageExtractionError`.
  `SegmentationResult.errors` holds only stage-2 errors; stage-1 read errors stay
  on the `CaseFileDocument` (linked via `document_id`), they are not copied over.
- **LLM access goes through `llm/`** (dependency injection): strategies depend
  only on the `LLMProvider` ABC (`generate(prompt, *, system, schema,
  temperature, max_tokens) -> LLMResponse`); concrete backends are injected.
  Endpoint properties (model name, Ollama's `num_ctx`/`keep_alive`/`think`,
  MLX's `default_max_tokens`) are provider-constructor state, NOT `generate`
  parameters. `schema` is a Pydantic *class* (Ollama derives the dict via
  `model_json_schema()`; outlines needs the class as `output_type`); callers
  still parse `response.text` themselves. Add a new backend (e.g. a future
  `LiteLLMProvider` for remote APIs) as a new `LLMProvider` subclass — never by
  editing `pipeline/segmentation/`.
- **MLX specifics**: mlx-lm has no constrained decoding — `MLXProvider` uses
  **outlines** (`outlines.from_mlxlm`) for schema-enforced JSON. outlines drops
  mlx-lm's per-call metrics, so token counts are re-derived via the tokenizer
  and only wall-clock generation time is reported. The model loads once per
  model id (`lru_cache`) and stays in unified memory (no `keep_alive` concept);
  there is no `num_ctx` equivalent (full prompt is always prefilled — do NOT
  use `max_kv_size`, a rotating cache would silently drop early pages).
  mlx/outlines imports are function-level so `llm` stays importable off-Mac.
- The **full-context** strategy sends one compact *fingerprint* per page (not
  the full text); when running it on Ollama the provider **must** be built with
  `num_ctx` (e.g. 131072) — Ollama's default (~2–4K) silently truncates the
  prompt. The model's segment list is never trusted directly: a deterministic
  repair step guarantees gap-/overlap-free coverage of every page regardless of
  model output.

## Known gaps / WIP

- Stage 3's LLM-generated titles/summaries are **unbenchmarked** (like the
  stage-2 strategies); irrelevant segments get `title`/`summary` = `None` by
  default (`enrich_irrelevant=False`). Build segments via
  `EnrichedSegment.from_segment` to preserve the `segment_id`.
- Stage 2 strategies are LLM-based and **unbenchmarked against ground truth** —
  the marked test PDF (`tests/assets/LR_32 F 245_24_markiert.pdf`) is the
  intended ground truth; boundary precision/recall per strategy is still TODO.
- `was_ocr_applied` is derived from the confidence report's `ocr_score`, but the
  default Tesseract CLI leaves that `NaN`, so the flag is currently unreliable
  (always `False`); a RapidOCR engine would restore it. Stage-1 page error
  handling (`CaseFileDocument.errors`) is still always `[]`.
