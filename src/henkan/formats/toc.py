from __future__ import annotations

import re

from henkan.errors import FormatError
from henkan.formats.sheet import Sheet

FILE = re.compile(r'^(?:FILE|DATAFILE)\s+"([^"]+)"', re.IGNORECASE)


def parse(text: str) -> Sheet:
    matches = (FILE.match(line.strip()) for line in text.splitlines())
    files = tuple(dict.fromkeys(match[1] for match in matches if match))
    if not files:
        raise FormatError("not a TOC sheet: it names no file")
    return Sheet(files, ())
