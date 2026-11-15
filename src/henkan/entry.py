from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Sequence
from types import ModuleType

CLI_MODULE = "henkan.cli.main"
CLI_DEPENDENCY = "typer"
PROGRAM = "henkan"
MISSING_CLI = (
    "the henkan command needs its cli extra: install it with Homebrew, "
    "or with pip install 'henkan[cli] @ git+https://github.com/gufranco/henkan'"
)

Importer = Callable[[str], ModuleType]


def main(
    argv: Sequence[str] | None = None, *, importer: Importer = importlib.import_module
) -> None:
    try:
        module = importer(CLI_MODULE)
    except ModuleNotFoundError as error:
        if error.name != CLI_DEPENDENCY:
            raise
        sys.stderr.write(MISSING_CLI + "\n")
        raise SystemExit(1) from error
    args = list(argv) if argv is not None else sys.argv[1:]
    module.app(args=args, prog_name=PROGRAM)
