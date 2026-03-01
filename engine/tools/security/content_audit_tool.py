from __future__ import annotations

import json
from typing import Any

from ..base import BaseTool, ToolExecutionResult
from ..playwright import PlaywrightComputerTool


class SecurityContentAuditTool(BaseTool):
    """
    Checks the current page for security-relevant issues like:
    - Insecure form actions (HTTP)
    - Mixed content (HTTP resources on HTTPS page)
    - High number of inline scripts (potential XSS risk)
    """

    name = "security_content_audit"
    description = "Audit a page for security-relevant content issues (HTTP forms, mixed content, inline scripts)."
    timeout_seconds = 30
    input_schema = {
        "type": "object",
        "properties": {
            "include_screenshot": {"type": "boolean"},
        },
        "required": [],
    }

    def __init__(self, computer_tool: PlaywrightComputerTool):
        self._computer = computer_tool

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        include_screenshot = bool(arguments.get("include_screenshot", False))

        # Ensure the browser page is ready
        await self._computer.ensure_ready()
        snapshot = await self._computer.collect_page_snapshot()

        findings: list[str] = []

        # Security-related checks only
        if snapshot.get("insecure_form_actions", 0) > 0:
            findings.append("Form action posting over HTTP detected.")
        if snapshot.get("mixed_content_references", 0) > 0:
            findings.append("Mixed content (HTTP resources on HTTPS page) detected.")
        if snapshot.get("inline_script_blocks", 0) > 10:
            findings.append(
                f"High number of inline scripts ({snapshot['inline_script_blocks']}); potential XSS risk."
            )

        if not findings:
            findings = ["No security issues detected."]

        result = ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": self._computer.current_url,
                    "snapshot": snapshot,
                    "findings": findings,
                }
            ),
            metadata={"url": self._computer.current_url},
        )

        # Optionally include a screenshot
        if include_screenshot:
            shot = await self._computer.execute({"action": "screenshot"})
            result.screenshot_base64 = shot.screenshot_base64

        return result
