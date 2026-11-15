## What this changes

One paragraph: what a reader of the diff would not work out on their own.

## How it was established

For a format change, the specification or spec it was written from, and the reference program its output was checked against.

## Checklist

- [ ] `uv run ruff format --check .` and `uv run ruff check .` pass
- [ ] `uv run mypy` passes
- [ ] `uv run pytest --cov` passes at 100% on a clean checkout
- [ ] A new capability works both as a library call and as a command
- [ ] A new source has its NOTICE.md row, and whoever wrote the code has not read that source's code
