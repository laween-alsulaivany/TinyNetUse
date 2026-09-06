# Code signing policy

TinyNetUse official Windows releases are currently unsigned.

## Official builds

Official TinyNetUse releases are built from the public source repository using
GitHub Actions and published through GitHub Releases.

Official release artifacts include:

- `TinyNetUse.exe`
- `TinyNetUse-Setup-<version>.exe`
- Portable release packages

SHA-256 checksums are published alongside release artifacts.

## Code signing

TinyNetUse does not currently use a code-signing provider.

If code signing is added in the future, only artifacts produced by the official
release workflow will be eligible for signing. This policy will be updated before
signed releases are distributed.

## Official distribution

Official TinyNetUse releases are distributed through:

https://github.com/laween-alsulaivany/TinyNetUse/releases
