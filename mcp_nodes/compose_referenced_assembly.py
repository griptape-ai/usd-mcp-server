from __future__ import annotations

import json
from typing import Any, List, Dict

from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode

from usd_mcp import core


class ComposeReferencedAssemblyNode(SuccessFailureNode):
    """Compose an assembly stage by referencing a list of assets.

    Deterministic: calls usd_mcp.core.compose_referenced_assembly directly.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.add_parameter(
            Parameter(
                name="output_path",
                input_types=["str"],
                type="str",
                default_value=None,
                tooltip="Assembly stage path (.usd/.usda)",
            )
        )
        self.add_parameter(
            Parameter(
                name="assets",
                input_types=["str", "list"],
                type="str",
                default_value="[]",
                tooltip="JSON array of {asset_path,name?,internal_path?}",
                ui_options={"multiline": True},
            )
        )
        self.add_parameter(
            Parameter(name="container_root", input_types=["str"], type="str", default_value="/Assets")
        )
        self.add_parameter(Parameter(name="flatten", input_types=["bool"], type="bool", default_value=True))
        self.add_parameter(Parameter(name="upAxis", input_types=["str"], type="str", default_value="Z"))
        self.add_parameter(Parameter(name="setDefaultPrim", input_types=["bool"], type="bool", default_value=True))
        self.add_parameter(Parameter(name="skipIfExists", input_types=["bool"], type="bool", default_value=True))
        self.add_parameter(Parameter(name="clearExisting", input_types=["bool"], type="bool", default_value=False))

        self.output_combined_path = Parameter(
            name="combined_path",
            input_types=["str"],
            type="str",
            default_value="",
            allowed_modes={ParameterMode.OUTPUT},
        )
        self.add_parameter(self.output_combined_path)

        self.output_referenced = Parameter(
            name="referenced",
            input_types=["int"],
            type="int",
            default_value=0,
            allowed_modes={ParameterMode.OUTPUT},
        )
        self.add_parameter(self.output_referenced)

        # Status panel (required by SuccessFailureNode lifecycle)
        self._create_status_parameters(
            result_details_tooltip="Details about composition results",
            result_details_placeholder="Results will appear when the node executes",
            parameter_group_initially_collapsed=False,
        )

    def process(self) -> None:
        try:
            output_path: str = self.get_parameter_value("output_path")
            assets_param = self.get_parameter_value("assets")
            if isinstance(assets_param, str):
                assets: List[Dict[str, Any]] = json.loads(assets_param or "[]")
            else:
                assets = list(assets_param or [])
            container_root: str = self.get_parameter_value("container_root")
            flatten: bool = bool(self.get_parameter_value("flatten"))
            upAxis: str = self.get_parameter_value("upAxis")
            setDefaultPrim: bool = bool(self.get_parameter_value("setDefaultPrim"))
            skipIfExists: bool = bool(self.get_parameter_value("skipIfExists"))
            clearExisting: bool = bool(self.get_parameter_value("clearExisting"))

            result = core.compose_referenced_assembly(
                output_path=output_path,
                assets=assets,
                container_root=container_root,
                flatten=flatten,
                upAxis=upAxis,
                setDefaultPrim=setDefaultPrim,
                skipIfExists=skipIfExists,
                clearExisting=clearExisting,
            )
            self.publish_update_to_parameter("combined_path", result.get("combined_path", ""))
            self.publish_update_to_parameter("referenced", int(result.get("referenced", 0)))
        except Exception as e:
            # Mark failure
            self.publish_update_to_parameter("combined_path", "")
            self.publish_update_to_parameter("referenced", 0)
            raise e


