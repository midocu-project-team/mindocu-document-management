# Schema-Aufbau der Pipeline

## Task 1: Maschinenlesbare Datei (CaseFileDocument)

```
PDF-Datei (Input)
        │
        ▼
┌─────────────────────────────────────┐
│        CaseFileDocument             │  ← ein Objekt pro PDF
│  document_id, source_path, ...      │
│                                     │
│  pages: [                           │
│    ┌─────────────────────────┐      │
│    │       PageContent       │      │  ← ein Objekt pro Seite
│    │  page_number, raw_text  │      │
│    │  was_ocr_applied, ...   │      │
│    │                         │      │
│    │  blocks: [              │      │
│    │    TextBlock(heading)   │      │  ← Bausteine der Seite
│    │    TextBlock(paragraph) │      │
│    │    TextBlock(footer)    │      │
│    │  ]                      │      │
│    └─────────────────────────┘      │
│    ...weitere Seiten...             │
│  ]                                  │
│                                     │
│  errors: [ExtractedPageError, ...]  │  ← keine stillen Fehler
└─────────────────────────────────────┘
        │
        ▼
```

## Task 2: Segmentierung (SegmentationResult)

```
        │
        ▼
┌─────────────────────────────────────┐
│        SegmentationResult           │  ← ein Objekt pro CaseFileDocument
│  document_id, segmented_at, ...     │
│                                     │
│  segments: [                        │
│    ┌─────────────────────────┐      │
│    │     DocumentSegment     │      │  ← ein Objekt pro erkanntes Segment
│    │  segment_id             │      │
│    │  start_page, end_page   │      │
│    │  raw_text, confidence   │      │
│    │                         │      │
│    │  pages: [               │      │
│    │    PageContent(4)       │      │  ← direkt aus Task 1
│    │    PageContent(5)       │      │
│    │    PageContent(6)       │      │
│    │  ]                      │      │
│    └─────────────────────────┘      │
│    ...weitere Segmente...           │
│  ]                                  │
│                                     │
│  unassigned_pages: [                │
│    PageContent, ...                 │  ← Seiten, die keinem Segment zugeordnet wurden
│  ]                                  │
│                                     │
│  errors: [ExtractedPageError, ...]  │  ← Fehlerhafte Seiten (übernehme von CaseFileDocument)
└─────────────────────────────────────┘
        │
        ▼
```

## Task 3: Klassifizierung (ClassificationResult?)

        │
        ▼

Output (wsl. FastAPI)
