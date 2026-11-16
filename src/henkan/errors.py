from __future__ import annotations


class HenkanError(Exception):
    pass


class FormatError(HenkanError):
    pass


class RefusalError(HenkanError):
    pass
