import io
from datatypes import CaseFileDocument, ExtracedPageError, PageContent

# Korbi

# Ein paar Ansätze, ist aber selbst überlassen: (vlt. auch kein BytesObjekt als Input sondern file name als string direkt, etc.)
def read_document(file: io.BytesIO) -> CaseFileDocument:
  pass

def _extract_page(page) -> PageContent | ExtracedPageError :
  pass