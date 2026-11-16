<div align="center">

<h1>henkan 変換</h1>

<strong>轉換、校驗及保存遊戲光碟映像檔和遊戲套件</strong>

<br>
<br>

[English](README.md) | [日本語](README.ja.md) | [简体中文](README.zh-Hans.md) | 繁體中文 (香港)

<br>

[![CI](https://github.com/gufranco/henkan/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/henkan/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](pyproject.toml)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

henkan 把遊戲光碟映像檔或遊戲套件由一種格式轉換成另一種格式，將結果與原檔案作比對，並在處理期間保障你的檔案安全。它可在 Linux 及 macOS 上運行。

## 狀況

henkan 正處於早期開發階段。目前它可以檢查自身環境，判斷光碟映像檔或遊戲資料夾是甚麼、可以轉換成哪些格式，並在不執行的情況下規劃一次轉換，暫未提供任何轉換功能。每種格式會在各自的版本中加入，本頁只列出已經可用的功能。

## 安裝

需要 Python 3.14 或以上版本及 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/gufranco/henkan.git
cd henkan
uv sync --extra cli
uv run henkan doctor
```

## 用法

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

`henkan doctor --json` 以 JSON 格式輸出同一份報告，缺少必需組件時會以狀態碼 1 結束。

`henkan info` 讀取 CUE、GDI、TOC、CCD 及 MDS 描述檔、ISO 及 BIN 映像檔、PBP 檔案、3DS 檔案以及遊戲資料夾，並根據內容而非單憑檔案名稱作判斷。`henkan list` 以 `*` 標示預設目標格式。兩者均接受檔案及資料夾，使用 `--json` 輸出 JSON，拒絕某個檔案時會把原因寫到標準錯誤並以狀態碼 1 結束。

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

## henkan 不包含的內容

不包含任何遊戲、BIOS 檔案、韌體、密鑰或主機證書，亦從不下載這些內容。請只用於你擁有的光碟及遊戲套件。

## 授權

[MIT](LICENSE)。henkan 學習格式時參考的資料列於 [NOTICE.md](NOTICE.md)。
