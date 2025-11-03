usd-mcp
=======

Model Context Protocol (MCP) server for interacting with Pixar USD (Universal Scene Description) files using clean, single-action tools ideal for LLM orchestration.

What you get in Milestone 1 (Tier 0):
- Install with host `pxr`
- Open/close stages, list stages
- Inspect stages and prims
- Get/set attribute values
- Create new stages from scratch
- Save/export USD files (basic)

Docs and guides
- Docs index: [Docs Index](docs/README.md)
- Installation: [Installation](docs/installation.md)
- Usage and quickstart: [Usage / Quickstart](docs/usage.md)
- Tool contracts (Tier 0): [Tier 0 Tools](docs/tools/tier0.md)
- Architecture decisions: [ADRs](docs/adr/)
- MCP + Griptape setup: [MCP with Griptape](docs/mcp-griptape.md)
- Sample NL prompts for Griptape: [Griptape Prompts](docs/griptape-prompts.md)
  - Includes new composition flow via composeReferencedAssembly and batch reference helpers.
- Test locally with Inspector: [MCP Inspector](docs/inspector.md)

Examples
- See [examples/](examples/) including:
  - [minimal_read.py](examples/minimal_read.py)
  - [create_stage.py](examples/create_stage.py)

License
- Apache-2.0. See `LICENSE`.

Status
- Milestone 1 (Tier 0) in progress. Later tiers include composition (layers/refs), authoring utilities, materials/cameras, and USDZ export + validation.

Quick install
- Create venv, install package, then install USD wheels if available:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .`
  - `pip install "usd-core==25.11"`
  - `python -c "import pxr, usd_mcp; print('ok')"`


