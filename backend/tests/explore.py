from pipeline import ocr_convert_pdf, read_document
from pathlib import Path
import io
import IPython
from rich import print


PDF_NAME = "LR_32 F 245_24_markiert.pdf"
PDF_PATH = Path(__file__).parent / "assets" / PDF_NAME

with open(PDF_PATH, "rb") as f:
    pdf_bytes = io.BytesIO(f.read())

# Our reading format
doc = read_document(pdf_bytes, str(PDF_NAME))
print(doc)

# Docling reading format
# result = ocr_convert_pdf(pdf_bytes, str(PDF_NAME))
# print(result)

IPython.embed()
