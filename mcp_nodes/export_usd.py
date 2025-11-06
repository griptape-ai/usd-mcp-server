from __future__ import annotations

import os
from griptape_nodes.exe_types.core_types import Parameter, ParameterMode
from griptape_nodes.exe_types.node_types import SuccessFailureNode

from usd_mcp import core


class ExportUsdNode(SuccessFailureNode):
    """Export/flatten USD or USDZ to a USD/USDA file.

    Deterministic: calls usd_mcp.core.export_usd_file.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.add_parameter(Parameter(name="path", input_types=["str"], type="str", default_value=None))
        self.add_parameter(Parameter(name="output_path", input_types=["str"], type="str", default_value=None))
        self.add_parameter(Parameter(name="flatten", input_types=["bool"], type="bool", default_value=True))
        self.add_parameter(Parameter(name="skipIfExists", input_types=["bool"], type="bool", default_value=True))

        self.out_output_path = Parameter(
            name="result_output_path",
            input_types=["str"],
            type="str",
            default_value="",
            allowed_modes={ParameterMode.OUTPUT},
        )
        self.add_parameter(self.out_output_path)

        self.out_skipped = Parameter(
            name="skipped",
            input_types=["bool"],
            type="bool",
            default_value=False,
            allowed_modes={ParameterMode.OUTPUT},
        )
        self.add_parameter(self.out_skipped)

        # Status panel (required by SuccessFailureNode lifecycle)
        self._create_status_parameters(
            result_details_tooltip="Details about export results",
            result_details_placeholder="Results will appear when the node executes",
            parameter_group_initially_collapsed=False,
        )

    def process(self) -> None:
        path = self.get_parameter_value("path")
        output_path = self.get_parameter_value("output_path")
        flatten = bool(self.get_parameter_value("flatten"))
        skip = bool(self.get_parameter_value("skipIfExists"))

        # Route packaging requests to USDZ API if the output is .usdz
        if isinstance(output_path, str) and output_path.lower().endswith(".usdz"):
            # If input is already a .usdz and skipIfExists, short-circuit
            if skip and os.path.exists(output_path):
                self.publish_update_to_parameter("result_output_path", output_path)
                self.publish_update_to_parameter("skipped", True)
                return
            result = core.export_usdz_file(path=path, output_path=output_path)
            self.publish_update_to_parameter("result_output_path", result.get("output_path", ""))
            self.publish_update_to_parameter("skipped", False)
            return

        # Otherwise, export to USD/USDA (flatten supported)
        result = core.export_usd_file(path=path, output_path=output_path, flatten=flatten, skipIfExists=skip)
        self.publish_update_to_parameter("result_output_path", result.get("output_path", ""))
        self.publish_update_to_parameter("skipped", bool(result.get("skipped", False)))


