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

henkan 处于早期开发阶段。目前它可以安装并检查自身环境，尚未提供任何转换功能。每种格式会在各自的版本中加入，本页只列出已经可用的功能。

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

## henkan 不包含的内容

不包含任何游戏、BIOS 文件、固件、密钥或主机证书，也从不下载这些内容。请只用于你拥有的光盘和游戏包。

## 许可证

[MIT](LICENSE)。henkan 学习格式时参考的资料列在 [NOTICE.md](NOTICE.md) 中。
