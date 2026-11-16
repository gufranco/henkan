from __future__ import annotations

from henkan.source import Source

MAGICS = (
    (0, b"WBFS", "a WBFS image"),
    (0, b"WUX0\x2e\xd0\x99\x10", "a WUX image"),
    (0, b"CISO", "a CSO or CISO image"),
    (0, b"ZISO", "a ZSO image"),
    (0, b"\x01\xc0\x0b\xb1", "a GCZ image"),
    (0, b"WIA\x01", "a WIA image"),
    (0, b"RVZ\x01", "an RVZ image"),
    (0, b"MComprHD", "a CHD"),
    (0, b"ECM\x00", "an ECM file"),
    (0, b"\x7fPKG", "a PS3 package"),
    (0, b"PFS0", "an NSP"),
    (0, b"NUP\x01", "a NUP"),
    (0, b"Z3DS", "a compressed 3DS file"),
    (0x100, b"HEAD", "an XCI"),
)
ARCHIVE = "an archive"
EXTENSIONS = {
    ".nrg": "a Nero image",
    ".cdi": "a DiscJuggler image",
    ".vcd": "a POPStarter VCD",
    ".ecm": "an ECM file",
    ".chd": "a CHD",
    ".cso": "a CSO or CISO image",
    ".ciso": "a CSO or CISO image",
    ".zso": "a ZSO image",
    ".dax": "a DAX image",
    ".jso": "a JSO image",
    ".gcz": "a GCZ image",
    ".rvz": "an RVZ image",
    ".wia": "a WIA image",
    ".wbfs": "a WBFS image",
    ".wux": "a WUX image",
    ".zar": "a ZAR archive",
    ".pkg": "a PS3 package",
    ".nsp": "an NSP",
    ".xci": "an XCI",
    ".nup": "a NUP",
    ".nsz": "an NSZ",
    ".xcz": "an XCZ",
    ".cia": "a CIA",
    ".zcci": "a compressed 3DS file",
    ".zcxi": "a compressed 3DS file",
    ".z3dsx": "a compressed 3DS file",
    ".m3u": "a playlist",
    ".zip": ARCHIVE,
    ".7z": ARCHIVE,
    ".rar": ARCHIVE,
    ".tar": ARCHIVE,
    ".gz": ARCHIVE,
    ".tgz": ARCHIVE,
    ".bz2": ARCHIVE,
    ".xz": ARCHIVE,
}


def label(source: Source, extension: str) -> str | None:
    by_content = (name for at, magic, name in MAGICS if source.peek(at, len(magic)) == magic)
    return next(by_content, EXTENSIONS.get(extension))
