# Code signing policy

TinyNetUse uses automated builds from its public GitHub repository for official Windows releases.

## Windows code signing

Free code signing provided by SignPath.io, certificate by SignPath Foundation.

### What is signed

Official Windows release artifacts published through GitHub Releases may be signed, including:

* `TinyNetUse.exe`
* `TinyNetUse-Setup-<version>.exe`
* Other TinyNetUse binaries produced by the official release workflow

Only artifacts built from the TinyNetUse source repository are submitted for signing.

### Build and signing process

Official release artifacts are built from the public TinyNetUse source repository using GitHub Actions.

Only artifacts produced by the project's official build workflow are eligible for signing. Each signing request requires approval by the project maintainer.

### Team roles

TinyNetUse is currently a single-maintainer project.

* **Authors / Committers:** [laween-alsulaivany](https://github.com/laween-alsulaivany)
* **Reviewers:** [laween-alsulaivany](https://github.com/laween-alsulaivany)
* **Approvers:** [laween-alsulaivany](https://github.com/laween-alsulaivany)

Changes submitted by external contributors are reviewed by the maintainer before being merged.

### Privacy

TinyNetUse does not send telemetry or collect usage data.

The application reads network byte counters provided locally by Windows to calculate current upload and download speeds. It does not inspect packet contents.

TinyNetUse will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it. For example, project and release links open GitHub in the user's default browser only when the user chooses to open them.

For additional details, see the Privacy and network behavior section of the project README.

## Official distribution

Official TinyNetUse releases are distributed through:

https://github.com/laween-alsulaivany/TinyNetUse/releases
