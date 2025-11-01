import os
import tempfile
import pytest


def _has_pxr() -> bool:
    try:
        import pxr  # noqa: F401

        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _has_pxr(), reason="pxr/USD not available")


def test_create_and_save_stage(tmp_path):
    from usd_mcp.tools.tier0 import tool_create_stage, tool_save_stage, tool_get_stage_summary

    out = tmp_path / "new.usda"

    resp = tool_create_stage({"output_path": str(out), "upAxis": "Y", "metersPerUnit": 1.0})
    assert resp["ok"]
    sid = resp["result"]["stage_id"]

    summary = tool_get_stage_summary({"stage_id": sid})
    assert summary["ok"]
    assert "root_prims" in summary["result"]

    saved = tool_save_stage({"stage_id": sid})
    assert saved["ok"], saved
    assert os.path.exists(saved["result"]["output_path"]) or os.path.exists(str(out))


