from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from hypothesis import settings
from hypothesis import strategies as st

from henkan.errors import FormatError, HenkanError
from henkan.source import Source

EXAMPLES = 10_000
LIMIT = 4 * 1024 * 1024
READS_MAX = 100_000
HOSTILE = (b"\0", b"\xff", b"\x7f", b"\x80", b"\xff\xff", b"\xff\xff\xff\xff", b"\0\0\0\x80")
FUZZ = settings(max_examples=EXAMPLES, deadline=None, derandomize=True, database=None)
QUICK = settings(FUZZ, max_examples=EXAMPLES // 5)

type Mutations = list[tuple[int, int, bytes]]

MUTATIONS = st.lists(
    st.tuples(
        st.integers(0, 2**31),
        st.integers(-8, 8),
        st.sampled_from(HOSTILE) | st.binary(min_size=1, max_size=4),
    ),
    max_size=6,
)
CUTS = st.none() | st.integers(0, 2**31)


@dataclass(frozen=True, slots=True)
class Outcome:
    refused: bool
    reads: int
    largest: int

    @property
    def bounded(self) -> bool:
        return self.reads <= READS_MAX and self.largest <= LIMIT


class _Counting(io.BytesIO):
    def __init__(self, data: bytes) -> None:
        super().__init__(data)
        self.sizes: list[int] = []

    @override
    def read(self, size: int | None = -1) -> bytes:
        data = super().read(size)
        self.sizes.append(len(data))
        return data


def structure(base: bytes) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(base) if value)


def corrupted(base: bytes, hot: tuple[int, ...], mutations: Mutations, cut: int | None) -> bytes:
    image = bytearray(base)
    for pick, shift, value in mutations:
        at = max(0, hot[pick % len(hot)] + shift)
        image[at : at + len(value)] = value
    return bytes(image if cut is None else image[: cut % (len(image) + 1)])


def attempt(
    action: Callable[[Source], object],
    data: bytes,
    refusal: type[HenkanError] = FormatError,
) -> Outcome:
    handle = _Counting(data)
    try:
        action(Source(handle, len(data), LIMIT, "fuzzed"))
    except refusal:
        return Outcome(True, len(handle.sizes), max(handle.sizes, default=0))
    return Outcome(False, len(handle.sizes), max(handle.sizes, default=0))
