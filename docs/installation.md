Installation (USD/pxr via venv)
===============================

Prereqs
- Python 3.10+

1) Create and activate a venv (macOS/Linux)
- `python3 -m venv .venv`
- `source .venv/bin/activate`

2) Install usd-mcp (editable for development)
- `pip install -e .`

3) Provide USD (pxr) to this Python

Option A — PyPI wheel (recommended if available)
- `pip install "usd-core==25.11"`
- Verify: `python -c "import pxr; print(pxr.__file__)"`

Option B — System USD already present on PYTHONPATH
- If your environment already exposes `pxr`, skip A.
- Verify: `python -c "import pxr; print('ok')"`

Option C — Build OpenUSD and point your venv at it
- Install deps: `brew install cmake boost tbb` (macOS)
- Build: `git clone https://github.com/PixarAnimationStudios/OpenUSD.git && cd OpenUSD`
- `python build_scripts/build_usd.py $HOME/usd --build-variant release --python --no-usdview --no-tests --no-docs`
- Add to venv via .pth: `echo "$HOME/usd/lib/python" > .venv/lib/python3.X/site-packages/openusd.pth` (match X to your minor)

4) Verify usd-mcp + pxr
- `python -c "import pxr, usd_mcp; print('ok')"`
- `usd-mcp --help`

Notes
- We do not vendor USD; we rely on either the `usd-core` wheel or a host build.
- Wheels may be platform/py-version specific (cp3XY). If you switch Python, reinstall the matching wheel.


Next steps
- Continue to [Usage / Quickstart](usage.md)

Back: [Docs Index](README.md)

