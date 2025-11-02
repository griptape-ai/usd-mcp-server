ADR 0001: Dependency strategy for USD
=====================================

Status: accepted

Context
- USD (pxr) is large and platform-specific; bundling wheels complicates distribution.

Decision
- Use host-provided USD in Milestone 1. The package does not vendor USD.
- Accept either:
  - PyPI wheels (e.g., `usd-core`) when available for the target Python/platform
  - A system or source-built OpenUSD, exposed via site-packages or PYTHONPATH
- Detect missing USD at runtime and return a clear `missing_usd` error.
- Provide a Docker image with a pinned USD build in a later milestone.

Consequences
- Simpler packaging and CI now; users can use `usd-core` or a local build.
- Later work: build and publish a Docker image for zero-install usage.


Back: [Docs Index](../README.md)

