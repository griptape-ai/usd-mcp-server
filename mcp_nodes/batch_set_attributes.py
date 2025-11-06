from __future__ import annotations

import json
from typing import Any, List, Dict

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode

from usd_mcp import core


class BatchSetAttributesNode(SuccessFailureNode):
    """Batch set attribute values in one save.

    Deterministic: calls usd_mcp.core.batch_set_attribute_values_in_file.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.add_parameter(Parameter(name="path", input_types=["str"], type="str", default_value=None))
        self.add_parameter(
            Parameter(
                name="items",
                input_types=["str", "list"],
                type="str",
                default_value="[]",
                tooltip="JSON array of {prim_path, attr, value, time?}",
                ui_options={"multiline": True},
            )
        )

        self.out_output_path = Parameter(
            name="output_path",
            input_types=["str"],
            type="str",
            default_value="",
            allowed_modes={ParameterMode.OUTPUT},
        )
        self.add_parameter(self.out_output_path)

        # Status panel (required by SuccessFailureNode lifecycle)
        self._create_status_parameters(
            result_details_tooltip="Details about batch set results",
            result_details_placeholder="Results will appear when the node executes",
            parameter_group_initially_collapsed=False,
        )

    def process(self) -> None:
        path = self.get_parameter_value("path")
        items_param = self.get_parameter_value("items")
        if isinstance(items_param, str):
            items: List[Dict[str, Any]] = json.loads(items_param or "[]")
        else:
            items = list(items_param or [])
        result = core.batch_set_attribute_values_in_file(path=path, items=items)
        self.publish_update_to_parameter("output_path", result.get("output_path", ""))


