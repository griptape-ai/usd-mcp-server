#!/usr/bin/env python3

import json


def main() -> int:
    # Demonstrate an example request to the server: open, summary, close
    # This prints example request JSON; pipe into `usd-mcp serve` to execute.
    reqs = [
        {"method": "open_stage", "params": {"path": "/path/to/your/file.usda"}},
        {"method": "get_stage_summary", "params": {"stage_id": "<FILL_AFTER_OPEN>"}},
        {"method": "close_stage", "params": {"stage_id": "<FILL_AFTER_OPEN>"}},
    ]
    print("\n".join(json.dumps(r) for r in reqs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


