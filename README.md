usd-mcp
=======

Model Context Protocol (MCP) server for interacting with Pixar USD (Universal Scene Description) files using clean, single-action tools ideal for LLM orchestration.

Features
- Stage management: open/close, list, summarize (stateful) and stateless file helpers.
- File inspection: summarizeFile, listPrimsFile, primInfoFile, getAttrFile.
- Attribute writes: setAttrFile and batch set via setAttrsFile (aliases displayColor→primvars:displayColor, coerces [r,g,b]→[[r,g,b]]).
- Prim authoring: createPrimFile, deletePrimFile.
- Transforms: getXformFile, setXformFile (CommonAPI ops; strips TypeTransform; smart parent/child scaling; gprim size handling).
- Composition: composeReferencedAssembly (one‑shot), addReferencesBatchInFile, setDefaultPrimFile.
- Variants: listVariantsFile, setVariantFile.
- Materials: listMaterialsFile, bindMaterialFile, unbindMaterialFile, getMaterialBindingFile.
- Cameras: listCamerasFile, getCameraFile, setCameraFile.
- Bounds: getBoundsFile (world AABB with fallbacks).
- Export: exportUsdFile (flatten, skipIfExists), exportUsdzFile.
- Ergonomics: camelCase tool aliases; argument normalization (flat JSON, tolerant keys); createStage is open‑or‑create, default upAxis Z.

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
- Active development. See Features above for what’s available now.

Quick install
- Create venv, install package, then install USD wheels if available:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .`
  - `pip install "usd-core==25.11"`
  - `python -c "import pxr, usd_mcp; print('ok')"`


