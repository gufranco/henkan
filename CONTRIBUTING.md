# Contributing

## Getting it running

```bash
git clone https://github.com/gufranco/henkan.git
cd henkan
uv sync
pnpm install
git config core.hooksPath .githooks
uv run pytest --cov
```

The suite passes on a clean checkout with no network. Every image a test needs is synthesized by the test.

## The gates

| Gate | Command |
|:--|:--|
| Format | `uv run ruff format --check .` |
| Lint | `uv run ruff check .` |
| Types | `uv run mypy` |
| Tests and coverage | `uv run pytest --cov` |
| JSON and YAML format | `pnpm run format:check` |

## Clean room

If you have read the source code of a project listed in [NOTICE.md](NOTICE.md), you can help by writing a behavior spec for that area, but not by writing henkan code for it. [AGENTS.md](AGENTS.md) explains the rule.

## Commits

Conventional commits, a subject of 50 characters at most, lowercase after the type, no full stop. The `commit-msg` hook and CI check every subject.
