from __future__ import annotations

import os
import time
import urllib.parse
from typing import Any

from griptape_nodes.exe_types.core_types import (
    NodeMessageResult,
    Parameter,
    ParameterMessage,
    ParameterMode,
)
from griptape_nodes.exe_types.node_types import DataNode
from griptape_nodes.traits.button import (
    Button,
    ButtonDetailsMessagePayload,
    ModalContentPayload,
    OnClickMessageResultPayload,
)


class USDZViewerLauncher(DataNode):
    """Launch a web-based USDZ viewer via a Button parameter.

    Inputs:
        - usdz_url (str): URL to a .usdz asset
        - title (str): Optional title displayed by the viewer
        - mirror_to_static (bool): Optionally mirror the USDZ into same-origin static storage to avoid CORS

    Controls:
        - open_viewer (Button): Saves a self-contained viewer page to static storage and links to it

    Outputs:
        - viewer_url (str): URL to the static viewer with query params
        - viewer_message (ParameterMessage): UI message with a button to open the viewer
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.category = "usd"
        self.description = "Open a self-contained USDZ viewer in the browser"

        # Inputs
        self.add_parameter(
            Parameter(
                name="usdz_url",
                input_types=["str"],
                type="str",
                tooltip="HTTP(s) URL to a .usdz file",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="title",
                input_types=["str"],
                type="str",
                default_value="USDZ Viewer",
                tooltip="Optional viewer title",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )
        self.add_parameter(
            Parameter(
                name="mirror_to_static",
                input_types=["bool"],
                type="bool",
                default_value=False,
                tooltip="Download the USDZ to same-origin static storage to avoid CORS",
                allowed_modes={ParameterMode.INPUT, ParameterMode.PROPERTY},
            )
        )

        # Button control
        self.add_parameter(
            Parameter(
                name="open_viewer",
                type="str",
                tooltip="Open the USDZ viewer",
                allowed_modes={ParameterMode.PROPERTY},
                traits={
                    Button(
                        icon="external-link",
                        size="sm",
                        variant="default",
                        on_click=self._on_open_viewer,
                    )
                },
            )
        )

        # Outputs
        self.add_parameter(
            Parameter(
                name="viewer_url",
                output_type="str",
                tooltip="URL to the launched viewer",
                allowed_modes={ParameterMode.OUTPUT},
            )
        )

        self.viewer_message = ParameterMessage(
            name="viewer_message",
            title="USDZ Viewer",
            value="Click to open the viewer in a new tab.",
            variant="info",
            button_link="",
            button_text="Open Viewer",
            button_icon="external-link",
        )
        self.add_node_element(self.viewer_message)

    def process(self) -> None:
        # Non-interactive run: attempt to generate viewer URL once
        self._generate_and_publish()

    def _on_open_viewer(self, button: Button, button_details: ButtonDetailsMessagePayload) -> NodeMessageResult | None:  # noqa: ARG002
        self._generate_and_publish()
        return NodeMessageResult(
            success=True,
            details="Viewer URL prepared",
            response=OnClickMessageResultPayload(
                button_details=button_details,
                modal_content=ModalContentPayload(
                    render_url=self.parameter_output_values.get("viewer_url", ""),
                    title=(self.get_parameter_value("title") or "USDZ Viewer").strip(),
                ),
            ),
            altered_workflow_state=False,
        )

    def _generate_and_publish(self) -> None:
        usdz_url = (self.get_parameter_value("usdz_url") or "").strip()
        if not (usdz_url.startswith("http://") or usdz_url.startswith("https://")):
            raise ValueError("usdz_url must be an http(s) URL to a .usdz asset")

        title = (self.get_parameter_value("title") or "USDZ Viewer").strip()
        viewer_url = self._ensure_viewer_and_compose_url(usdz_url, title)

        self.parameter_output_values["viewer_url"] = viewer_url
        # Update message with link
        self.viewer_message.button_link = viewer_url
        self.viewer_message.value = f"Viewer prepared for: {usdz_url}"
        self.show_message_by_name(self.viewer_message.name)

    def _ensure_viewer_and_compose_url(self, src_url: str, title: str) -> str:
        # Build final HTML by inlining viewer.js into index.html
        base_dir = os.path.dirname(__file__)
        index_path = os.path.join(base_dir, "usdz_viewer_app", "index.html")
        js_path = os.path.join(base_dir, "usdz_viewer_app", "viewer.js")

        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()
        with open(js_path, "r", encoding="utf-8") as f:
            viewer_js = f.read()

        # Replace placeholder with inline JS to create a self-contained static file
        inlined = index_html.replace("/*__INLINE_VIEWER_JS__*/", viewer_js)
        data = inlined.encode("utf-8")

        # Save to static files
        try:
            from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes
        except Exception:
            from griptape_nodes.retained_mode.retained_mode import GriptapeNodes

        filename = f"usdz_viewer_{int(time.time() * 1000)}.html"
        static_url = GriptapeNodes.StaticFilesManager().save_static_file(data, filename)

        # Optional mirror to same-origin static storage to avoid CORS
        try:
            mirror = bool(self.get_parameter_value("mirror_to_static"))
        except Exception:
            mirror = False
        if mirror and (src_url.startswith("http://") or src_url.startswith("https://")):
            try:
                import requests  # lazy import

                r = requests.get(src_url, timeout=30)
                r.raise_for_status()
                # derive a friendly filename
                base_name = os.path.basename(src_url.split("?", 1)[0]) or "model.usdz"
                if not base_name.lower().endswith(".usdz"):
                    base_name += ".usdz"
                mirrored_name = f"{int(time.time())}_{base_name}"
                mirrored_url = GriptapeNodes.StaticFilesManager().save_static_file(r.content, mirrored_name)
                # Add cache-busting token
                src_url = f"{mirrored_url}?t={int(time.time())}"
            except Exception:
                # If mirroring fails, fall back to original URL
                pass

        # Compose query params
        q = {
            "src": src_url,
            "title": title,
        }
        sep = "&" if "?" in static_url else "?"
        return f"{static_url}{sep}{urllib.parse.urlencode(q)}"


