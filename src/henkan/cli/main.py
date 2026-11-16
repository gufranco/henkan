from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Annotated

import typer

from henkan import commands, doctor
from henkan.cli import report as texts
from henkan.errors import UsageError
from henkan.version import VERSION

NAME_WIDTH = 18
DOCTOR_HELP = "Check the installation: version, Python, platform and the codecs henkan needs."
INFO_HELP = "Show what each file or folder is: platform, disc class, game ID, tracks and files."
LIST_HELP = "Show the formats each file or folder can become, with the default marked."
CONVERT_HELP = "Plan a conversion with --dry-run: each step and the space it needs."
PLAN_ONLY = "this version of henkan plans conversions and does not run them: add --dry-run"

Files = Annotated[list[Path], typer.Argument(help="files and folders to read", show_default=False)]
JsonFlag = Annotated[bool, typer.Option("--json", help="print the result as JSON")]

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Convert, verify and store game disc images and game packages.",
)


def doctor_lines(report: doctor.DoctorReport) -> list[str]:
    return [
        f"{check.name:<{NAME_WIDTH}} {check.detail}"
        + ("" if check.status is doctor.CheckStatus.OK else f" [{check.status}]")
        for check in report.checks
    ]


def doctor_json(report: doctor.DoctorReport) -> str:
    checks = [
        {"name": check.name, "status": str(check.status), "detail": check.detail}
        for check in report.checks
    ]
    return json.dumps({"healthy": report.healthy, "checks": checks}, indent=2)


def exit_code(report: doctor.DoctorReport) -> int:
    return 0 if report.healthy else 1


def _version(value: bool) -> None:
    if value:
        typer.echo(f"henkan {VERSION}")
        raise typer.Exit(code=0)


@app.callback()
def main(
    *,
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="print the version"),
    ] = False,
) -> None:
    del version


@app.command("doctor", help=DOCTOR_HELP)
def doctor_command(
    *,
    json_output: Annotated[bool, typer.Option("--json", help="print the report as JSON")] = False,
) -> None:
    report = doctor.diagnose()
    typer.echo(doctor_json(report) if json_output else "\n".join(doctor_lines(report)))
    raise typer.Exit(code=exit_code(report))


def _emit[Entry](
    found: commands.Report[Entry],
    key: str,
    lines: Callable[[Entry], list[str]],
    data: Callable[[Entry], texts.Json],
    json_output: bool,
) -> None:
    refused = [{"path": str(entry.path), "reason": entry.reason} for entry in found.refused]
    whole = {key: [data(entry) for entry in found.entries], "refused": refused}
    text = "\n".join(line for entry in found.entries for line in lines(entry))
    body = json.dumps({**whole, "notes": list(found.notes)}, indent=2) if json_output else text
    if body:
        typer.echo(body)
    for note in found.notes:
        typer.echo(f"note: {note}", err=True)
    for entry in found.refused:
        typer.echo(f"refused: {entry.reason}", err=True)
    raise typer.Exit(code=1 if found.refused else 0)


@app.command("info", help=INFO_HELP)
def info_command(files: Files, *, json_output: JsonFlag = False) -> None:
    _emit(commands.info(files), "items", texts.info_lines, texts.item_json, json_output)


@app.command("list", help=LIST_HELP)
def list_command(files: Files, *, json_output: JsonFlag = False) -> None:
    _emit(commands.offers(files), "items", texts.offer_lines, texts.offer_json, json_output)


@app.command("convert", help=CONVERT_HELP)
def convert_command(
    files: Files,
    *,
    to: Annotated[str | None, typer.Option("--to", help="the format to convert to")] = None,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="plan without converting")] = False,
    json_output: JsonFlag = False,
) -> None:
    if not dry_run:
        typer.echo(PLAN_ONLY, err=True)
        raise typer.Exit(code=1)
    try:
        found = commands.plans(files, to)
    except UsageError as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=2) from error
    _emit(found, "plans", texts.plan_lines, texts.plan_json, json_output)
