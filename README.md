<div align="center">

<h1>henkan 変換</h1>

<strong>Convert, verify and store game disc images and game packages</strong>

<br>
<br>

English | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | [繁體中文 (香港)](README.zh-HK.md)

<br>

[![CI](https://github.com/gufranco/henkan/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/henkan/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](pyproject.toml)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

henkan turns a game disc image or game package from one format into another, checks the result against the original, and keeps your files safe while it works. It runs on Linux and macOS.

## Status

henkan is in early development. Today it installs and checks its own environment; no conversion ships yet. Each format arrives in its own release, and this page lists only what works.

## Install

henkan needs Python 3.14 or newer and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/gufranco/henkan.git
cd henkan
uv sync --extra cli
uv run henkan doctor
```

## Usage

```console
$ henkan --version
henkan 0.0.0
$ henkan doctor
henkan             0.0.0
python             3.14.10
platform           Darwin arm64
zlib               available
bz2                available
lzma               available
compression.zstd   available
```

`henkan doctor --json` prints the same report as JSON, and exits 1 when something henkan needs is missing.

## What henkan never contains

No games, no BIOS files, no firmware, no keys and no console certificates, and it never downloads any. Use it only with discs and packages you own.

## License

[MIT](LICENSE). The sources henkan's formats were learned from are listed in [NOTICE.md](NOTICE.md).
