# Working in this repository

[README.md](README.md) is the document written for a person, and it is the source of truth for everything public. The Japanese, Simplified Chinese and Hong Kong Traditional Chinese READMEs are the same document translated. Change the English one first, then each translation, then anything derived from them: the package description, the formula `desc`, the citation abstract and the GitHub About text. `tests/repository/test_public_text.py` fails when a copy drifts.

## What this project is

One library and one command line over the same code, for game disc images and game packages: detect, convert, verify, hash and store. The command line decides nothing: every command parses its arguments, calls the library function of the same capability, and prints what came back. Typer is the `cli` extra.

## Legal and shareable, a hard rule

This project is for preservation and interoperability, and it must stay safe to share in public. A change that breaks one of these points is wrong even when everything else passes.

- No game, BIOS, firmware, key, console certificate, disc image or game package is ever committed, as a fixture or in any other guise. Test images are synthesized by the tests. Real images used for the optional local checks are supplied by the developer, held legally, declared in [artifacts.manifest.json](artifacts.manifest.json) and kept in the gitignored `external/` folder.
- No link or pointer to where to obtain a game, a key or firmware is committed.
- No vocabulary that frames the work as unlawful copying or as defeating a protection appears in any tracked file. [tests/repository/test_legal_hygiene.py](tests/repository/test_legal_hygiene.py) scans every tracked file and also fails if a disc image, package or key file is tracked.
- henkan never downloads anything on its own. An optional download runs only on request, from an allowlisted host, checked against a fixed SHA-256.

## Clean room, a hard rule

henkan is MIT, and every format is learned without copying. The projects [NOTICE.md](NOTICE.md) lists are studied, never copied, whatever their license.

- Whoever has read the source code of a project NOTICE.md lists writes behavior specs for that area, never henkan code. Specs hold inputs, outputs, byte layouts and decisions in the writer's own words, with no code, identifier, message or test from the source, and a second reader checks each one before it is used.
- Whoever writes henkan code works only from those specs, public format documents, and what reference programs produce when run as separate programs.
- A new source gets its NOTICE.md row, with its license and how it was used, in the same change. [tests/repository/test_notice.py](tests/repository/test_notice.py) fails on a row without one.

## Rules that are invisible in the code

- Never publish to PyPI. Distribution is this repository's releases and the formula in the shared tap `gufranco/homebrew-tap`.
- Linux and macOS only. Both run the whole suite in CI.
- The library's runtime imports are the standard library plus the packages `pyproject.toml` names; a new one needs the owner's approval.

## The gates

Every change passes all of these. A gate that was not run is a gate that failed.

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov
pnpm run format:check
```

Coverage is 100% of statements and branches. Tests carry only the `# Arrange`, `# Act` and `# Assert` markers: three blocks, one call to the thing under test, and a name that states the behavior.

## Where things live

| Path | Holds |
|:--|:--|
| `src/henkan/` | The library; each module's tests sit beside it as `<module>_test.py` |
| `src/henkan/formats/` | One module per container or file-system format |
| `src/henkan/platforms/` | One module per console family: what identifies its discs, files and folders |
| `src/henkan/*_test_support.py` | Builders of synthetic images and the corrupted-input harness the tests share |
| `src/henkan/cli/` | The Typer command line |
| `src/henkan/entry.py` | The console script, which says how to get the `cli` extra when Typer is absent |
| `tests/` | Tests of the repository itself, of `python -m henkan` and of the scripts |
| `.github/scripts/` | Release and commit-message scripts, run by CI, semantic-release and the commit-msg hook |
