#!/usr/bin/env python3

import json


def main() -> int:
    # Create a new stage and save it
    reqs = [
        {
            "method": "create_stage",
            "params": {"output_path": "/tmp/new.usda", "upAxis": "Y", "metersPerUnit": 0.01},
        },
        {"method": "get_stage_summary", "params": {"stage_id": "<FILL_AFTER_CREATE>"}},
        {"method": "save_stage", "params": {"stage_id": "<FILL_AFTER_CREATE>"}},
    ]
    print("\n".join(json.dumps(r) for r in reqs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


