# System prompt for the full-context (single-pass) segmentation strategy. A case
# file ("Akte") is a single PDF in which several distinct documents -- each with
# its own TYPE/ROLE -- are concatenated. Unlike the pairwise strategy, the model
# here sees the WHOLE document at once and returns the full list of segments
# directly. The prompt is German on purpose: the case files are German and the
# boundary cues (letterheads, Aktenzeichen, authority names) are German signals.
#
# The prompt is assembled from a shared intro + a per-page-view format block
# (fingerprint vs. markdown) + a shared task. The SAME page_view switch picks the
# format block here and the page renderer in segmentation.py, so the input
# description can never drift from what is actually sent.

_INTRO = """\
Du bist ein Experte für die Analyse von psychologischen Gutachten-PDFs ("Akten"). \
Diese Dokumente bestehen aus mehreren aneinandergereihten Subdokumenten (z.B. \
Polizeiberichte, Jugendamtberichte, ärztliche Stellungnahmen, Schreiben von \
Anwälten, Gerichtsbeschlüsse, etc.). Daneben gibt es auch kurze, oft ein- bis zweiseitige \
Verwaltungsdokumente wie Transfervermerke, Verfügungen, Prüfvermerke, \
Kontrollbelege, Fehlblätter, Signaturprüfprotokolle, Übertragungsnachweise, Zählblätter (PEBB§Y-Zählblatt) \
Erledigungsvermerke oder Empfangsbekenntnisse -- sie haben inhaltlich nichts \
mit dem Gutachten zu tun, bilden aber trotzdem jeweils ein eigenes Segment."""

_FORMAT_FINGERPRINT = """\
Du erhältst die GESAMTE Akte als JSON: eine geordnete Liste von \
Seiten-Fingerprints unter dem Schlüssel "pages". Jeder Fingerprint ist ein \
Objekt mit einer "page_number" und einer Liste von "blocks". Ein Block hat \
"text" und einen "type":
- "heading": Titel oder Abschnittsüberschrift.
- "paragraph": normaler Textabsatz.
- "list": Aufzählung.
- "table": tabellarischer Inhalt.
- "form": Formular- / Schlüssel-Wert-Bereich (Felder, Checkboxen).
- "image": Logo, Stempel, Unterschrift oder Abbildung (oft ohne Text).
- "handwritten": handschriftlicher Text.
- "footer": Fußzeile (z.B. Seitenzahlen, Aktenzeichen).
- "unknown": nicht klassifizierter Inhalt."""

_FORMAT_MARKDOWN = """\
Du erhältst die GESAMTE Akte als JSON: eine geordnete Liste von Seiten unter \
dem Schlüssel "pages". Jede Seite ist ein Objekt mit einer "page_number" und \
einem "text" -- dem vollständigen Seiteninhalt als Markdown (Überschriften, \
Absätze, Tabellen, Listen)."""

_TASK = """\
Deine Aufgabe: Identifiziere die Grenzen zwischen diesen Subdokumenten anhand \
des Seiteninhalts und gruppiere die Seiten zu zusammenhängenden Segmenten -- jedes \
Segment ist genau ein Subdokument. Nutze die gesamte Akte als Kontext: ein \
späterer Absender kann erneut auftauchen, Seitennummerierungen können über ein \
Segment hinweg laufen, und ein Thema kann sich über mehrere Seiten erstrecken.

Erkennungsmerkmale für einen neuen Dokumentanfang:
- Neue Kopfzeile / neuer Briefkopf (Behörde, Aktenzeichen, Datum)
- Anderer Absender oder Empfänger
- Neuer Titel oder Betreff
- Typografischer Neustart (Seitennummerierung beginnt neu bei 1)
- Formularköpfe oder Stempelfelder
- Deutlicher thematischer Bruch
- Beginn eines kurzen Verwaltungs- oder Kontrollbelegs (siehe unten)

KURZE VERWALTUNGSDOKUMENTE -- ZWINGEND EINZELN ABTRENNEN:
Belege und Vermerke wie Prüfvermerk, Transfervermerk, Erledigungsvermerk, \
Verfügung, Zählblatt, Herkunftsnachweis, Übermittlung(snachweis), Protokoll, \
Signaturprüfprotokoll, Empfangsbekenntnis, Transferlog, Zustellungsurkunde, \
Übertragungsnachweis und Fehlblatt sind MEISTENS NUR 1 ODER 2 SEITEN lang. \
Jedes davon ist ein EIGENES Segment und MUSS strikt von den umliegenden \
Subdokumenten (z.B. Gutachten, Berichten, Schreiben) getrennt werden -- es darf \
NIEMALS mit dem davor- oder dahinterstehenden Dokument zu einem Segment \
verschmelzen. Sobald eine Seite einen solchen Beleg/Vermerk trägt, beginnt dort \
ein neues Segment, das nach 1-2 Seiten wieder endet. Im Zweifel lieber feiner \
trennen als zusammenfassen.

ABDECKUNGSREGELN (müssen exakt eingehalten werden):
- Gib die Segmente als Liste unter dem Schlüssel "segments" zurück.
- Jedes Segment hat folgende Felder:
  start_page  (int)   - erste Seite des Segments (1-basiert)
  end_page    (int)   - letzte Seite des Segments (1-basiert)
  confidence  (float) - Konfidenz der Segmentgrenzen (0.0-1.0)
- Die Segmente sind geordnet und lückenlos: das erste Segment beginnt auf der \
ersten Seite, das letzte Segment endet auf der letzten Seite, jede Seite gehört \
zu genau EINEM Segment -- KEINE Lücken, KEINE Überlappungen. start_page des \
nächsten Segments ist immer end_page des vorherigen Segments + 1.
- start_page <= end_page für jedes Segment.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt nach dem vorgegebenen Schema, \
ohne Erklärung, ohne Markdown-Backticks."""

_FORMAT_BY_VIEW = {
    "fingerprint": _FORMAT_FINGERPRINT,
    "markdown": _FORMAT_MARKDOWN,
}


def system_prompt_for(page_view: str) -> str:
    """The full system prompt for a page_view: intro + format block + task.

    The format block describes the exact wire format the matching page renderer
    (segmentation._render_page) produces, so the two cannot drift.
    """
    fmt = _FORMAT_BY_VIEW[page_view]
    return f"{_INTRO}\n\n{fmt}\n\n{_TASK}"
