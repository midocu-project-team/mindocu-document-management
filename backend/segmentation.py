from datatypes import (
    CaseFileDocument,
    DocumentSegment,
    SegmentationResult,
    PageContent,
    SimilarityResult,
)
import json
import ollama
from statistics import mean

SIMILARITY_MODEL = "llama3.2:latest"

# System prompt for the page-similarity / document-boundary decision.
# A case file ("Akte") is a single PDF concatenating several distinct documents;
# the model decides whether the next page continues the current document or
# starts a new one.
SIMILARITY_SYSTEM_PROMPT = """\
You are a document-boundary detector for a German case file ("Akte"). A case \
file is a single PDF in which several distinct documents (e.g. letters, forms, \
invoices, court rulings, medical reports) are concatenated one after another.

You receive two inputs as JSON:
- "current_pages": the pages already grouped into the current document segment, \
in reading order. This list may be empty.
- "contestant_page": the next page, which either CONTINUES the current document \
or BEGINS a new one.

Decide whether the contestant page belongs to the SAME document as the current \
pages. Weigh signals such as: continuity of topic and wording, layout and \
formatting, sender/recipient, dates and reference/file numbers, explicit page \
numbering (e.g. "Seite 2 von 5"), salutations and closings (a fresh letterhead, \
greeting or signature block usually marks a new document), and abrupt changes \
in language or document type.

Output rules:
- are_similar: true if the contestant page continues the current document, \
false if it starts a new document.
- confidence: a float in [0.0, 1.0] expressing how certain you are.
- reasoning: one or two concise sentences justifying the decision.

Return ONLY a JSON object matching the provided schema. Emit no text outside \
the JSON."""


def segment_document(doc: CaseFileDocument) -> SegmentationResult:
    segments: list[DocumentSegment] = []
    current_pages: list[PageContent] = []
    similarity_confidences: list[float] = []

    def flush_segment() -> None:
        """Turn the pages collected so far into a DocumentSegment and reset."""
        if not current_pages:
            return
        page_numbers = [p.page_number for p in current_pages]
        segments.append(
            DocumentSegment(
                start_page=min(page_numbers),
                end_page=max(page_numbers),
                raw_text="\n\n\n".join(p.raw_text for p in current_pages),
                # Copy: the model keeps the list, but we clear our buffer below.
                pages=list(current_pages),
                confidence=mean(similarity_confidences),
            )
        )
        current_pages.clear()
        similarity_confidences.clear()

    for page in doc.pages:
        similarity_result = decide_page_similarity(current_pages, contestant_page=page)

        # A dissimilar page is a document boundary: close the running segment so
        # that this page becomes the first page of the next one (instead of being
        # dropped).
        if not similarity_result.are_similar:
            flush_segment()

        current_pages.append(page)

        # A boundary page opens a fresh segment and has no "continuation" score,
        # so it counts as full confidence -- same as the very first page, which
        # decide_page_similarity short-circuits to are_similar=True / 1.0.
        similarity_confidences.append(
            similarity_result.confidence if similarity_result.are_similar else 1.0
        )

    # Emit the last segment, which is still buffered when the loop ends.
    flush_segment()

    return SegmentationResult(
        document_id=doc.document_id,
        segments=segments,
        segmentation_method="llm",
        errors=doc.errors,
    )


def decide_page_similarity(
    current_pages: list[PageContent], contestant_page: PageContent
) -> SimilarityResult:
    """Asks the LLM whether contestant_page continues the current segment.

    The current pages and the contestant page are passed to the model as JSON;
    the reply is constrained to the SimilarityResult schema and parsed back into
    a SimilarityResult.
    """
    # An empty segment always accepts its first page; no LLM call needed.
    if not current_pages:
        return SimilarityResult(
            are_similar=True,
            confidence=1.0,
            reasoning="No current segment yet; the contestant page starts the first segment.",
        )

    user_content = json.dumps(
        {
            "current_pages": [p.model_dump(mode="json") for p in current_pages],
            "contestant_page": contestant_page.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )

    response = ollama.chat(
        model=SIMILARITY_MODEL,
        messages=[
            {"role": "system", "content": SIMILARITY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        format=SimilarityResult.model_json_schema(),
    )

    return SimilarityResult.model_validate_json(response.message.content)
