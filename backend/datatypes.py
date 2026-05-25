from dataclasses import dataclass
from typing import List

@dataclass
class Page:
  page_number: int
  type: str
  content: str

@dataclass
class File:
  pages: List[Page]

@dataclass
class Segment:
  type: str
  pages: List[Page]

class LabeledSegment:
  ...
