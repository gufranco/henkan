<div align="center">

<h1>henkan 変換</h1>

<strong>ゲームのディスクイメージとゲームパッケージを変換、検証、保管する</strong>

<br>
<br>

[English](README.md) | 日本語 | [简体中文](README.zh-Hans.md) | [繁體中文 (香港)](README.zh-HK.md)

<br>

[![CI](https://github.com/gufranco/henkan/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/henkan/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](pyproject.toml)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

henkan はゲームのディスクイメージやゲームパッケージをある形式から別の形式に変換し、結果を元のファイルと照合し、作業中もファイルを安全に保ちます。Linux と macOS で動作します。

## 状況

henkan は開発の初期段階です。現時点ではインストールと自身の環境チェックができ、変換機能はまだありません。形式はそれぞれ個別のリリースで追加され、このページには動作するものだけを記載します。

## インストール

Python 3.14 以降と [uv](https://docs.astral.sh/uv/) が必要です。

```bash
git clone https://github.com/gufranco/henkan.git
cd henkan
uv sync --extra cli
uv run henkan doctor
```

## 使い方

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

`henkan doctor --json` は同じレポートを JSON で出力し、必要なものが欠けている場合は終了コード 1 で終了します。

## henkan に含まれないもの

ゲーム、BIOS ファイル、ファームウェア、鍵、本体の証明書は一切含まず、ダウンロードもしません。ご自身が所有するディスクとパッケージにのみ使用してください。

## ライセンス

[MIT](LICENSE)。henkan が形式を学んだ資料は [NOTICE.md](NOTICE.md) に記載しています。
