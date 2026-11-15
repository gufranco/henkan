# Security

## Reporting

Report anything you believe is a security problem through [GitHub's private vulnerability reporting](https://github.com/gufranco/henkan/security/advisories/new) on this repository, rather than in a public issue. There is no service behind this project and no user data, so the realistic reports are about the supply chain and about what a malformed image or package can make the code do.

## What is in scope

| Class | Example |
|:--|:--|
| Malformed input | A crafted image, package or archive that makes henkan write outside its output folder, allocate without bound, loop forever, or run anything |
| Wrong acceptance | A result reported as verified that does not match its source |
| Secrets | A key file's contents reaching a process argument, a log, JSON output or the screen |
| Supply chain | A pinned action, the Homebrew formula, or a release artifact that has been tampered with |

## What is not

henkan reads files you already hold and writes files you asked for. It has no network access unless you ask for an optional download. A report that amounts to "this program can write a file" describes what it is for.

## Where this is distributed

This repository's releases page and the formula in the tap `gufranco/homebrew-tap`, and nowhere else. henkan is not published to PyPI; a package of that name anywhere else is not from this project.
