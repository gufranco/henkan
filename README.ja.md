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

henkan は開発の初期段階です。現時点では自身の環境チェック、ディスクイメージやゲームフォルダーの判別と変換可能な形式の表示、そして実行を伴わない変換計画の作成ができ、変換機能はまだありません。形式はそれぞれ個別のリリースで追加され、このページには動作するものだけを記載します。

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

`henkan info` は CUE、GDI、TOC、CCD、MDS のシート、ISO と BIN のイメージ、PBP ファイル、3DS ファイル、ゲームフォルダーを読み取り、ファイル名だけではなく内容から判別します。`henkan list` は既定の変換先を `*` で示します。どちらもファイルとフォルダーを受け取り、`--json` で JSON を出力し、ファイルを拒否した場合は理由を標準エラーに出力して終了コード 1 で終了します。

```console
$ henkan info game.cue
game.cue
  kind      cue
  platform  PS1
  disc      CD: a CUE sheet describes a CD
  id        ABCD-12345
  tracks    MODE2/2352, AUDIO
  size      733,824,000 bytes
  files     game.cue, game.bin
$ henkan list game.cue
game.cue  PS1  CD  733,824,000 bytes
  * chd
    pbp
    vcd
    cdi
    cue-ecc
$ henkan convert game.pbp --to cdi --dry-run
game.pbp to cdi
  1. pbp to cue, kept in a temporary folder: 733,824,000 bytes
  2. cue to cdi
  temporary space: 733,824,000 bytes
  expected output: 733,824,000 bytes
```

## henkan に含まれないもの

ゲーム、BIOS ファイル、ファームウェア、鍵、本体の証明書は一切含まず、ダウンロードもしません。ご自身が所有するディスクとパッケージにのみ使用してください。

## ライセンス

[MIT](LICENSE)。henkan が形式を学んだ資料は [NOTICE.md](NOTICE.md) に記載しています。
