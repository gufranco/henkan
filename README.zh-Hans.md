<div align="center">

<h1>henkan 変換</h1>

<strong>转换、校验并保存游戏光盘镜像和游戏包</strong>

<br>
<br>

[English](README.md) | [日本語](README.ja.md) | 简体中文 | [繁體中文 (香港)](README.zh-HK.md)

<br>

[![CI](https://github.com/gufranco/henkan/actions/workflows/ci.yml/badge.svg)](https://github.com/gufranco/henkan/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)](pyproject.toml)
[![Types](https://img.shields.io/badge/mypy-strict-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

</div>

---

henkan 将游戏光盘镜像或游戏包从一种格式转换为另一种格式，把结果与原文件进行比对，并在处理过程中保护你的文件。它运行在 Linux 和 macOS 上。

## 状态

henkan 处于早期开发阶段。目前它可以检查自身环境，判断光盘镜像或游戏文件夹是什么、可以转换成哪些格式，并在不执行的情况下规划一次转换，尚未提供任何转换功能。每种格式会在各自的版本中加入，本页只列出已经可用的功能。

## 安装

需要 Python 3.14 或更高版本以及 [uv](https://docs.astral.sh/uv/)。

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

`henkan doctor --json` 以 JSON 格式输出同一份报告，缺少必需组件时以状态码 1 退出。

`henkan info` 读取 CUE、GDI、TOC、CCD 和 MDS 描述文件、ISO 和 BIN 镜像、PBP 文件、3DS 文件以及游戏文件夹，并根据内容而不是仅凭文件名来判断。`henkan list` 用 `*` 标出默认目标格式。两者都接受文件和文件夹，使用 `--json` 输出 JSON，拒绝某个文件时把原因写到标准错误并以状态码 1 退出。

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

## henkan 不包含的内容

不包含任何游戏、BIOS 文件、固件、密钥或主机证书，也从不下载这些内容。请只用于你拥有的光盘和游戏包。

## 许可证

[MIT](LICENSE)。henkan 学习格式时参考的资料列在 [NOTICE.md](NOTICE.md) 中。
