from __future__ import annotations

import json
import socket
import ssl
import urllib.request
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from ..base import BaseTool, ToolExecutionResult


class SSLAuditTool(BaseTool):
    name = "ssl_audit"
    description = "Checks HTTPS availability, certificate validity, and HSTS policy for a URL."
    timeout_seconds = 20
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
        },
        "required": ["url"],
    }

    async def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        url = arguments.get("url")
        if not url:
            return ToolExecutionResult(success=False, error="No URL provided")
        if not str(url).startswith(("http://", "https://")):
            url = f"https://{url}"

        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 443

        findings = []

        # --- SSL Certificate Check ---
        try:
            context = ssl.create_default_context()
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    issuer = dict(x for x in cert.get("issuer", []))
                    issued_by = issuer.get("organizationName", "Unknown")
                    not_before = datetime.strptime(
                        cert["notBefore"], "%b %d %H:%M:%S %Y %Z"
                    ).replace(tzinfo=datetime.UTC)
                    not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(
                        tzinfo=datetime.UTC
                    )

                    now = datetime.now(datetime.UTC)
                    if now < not_before:
                        findings.append(f"Certificate not yet valid, starts {not_before}")
                    if now > not_after:
                        findings.append(f"Certificate expired on {not_after}")

                    findings.append(f"Issued by: {issued_by}")
        except Exception as e:
            return ToolExecutionResult(success=False, error=f"SSL connection failed: {e}")

        # --- HSTS Check ---
        try:
            req = urllib.request.Request(
                url, method="GET", headers={"User-Agent": "QA-SecurityBot/1.0"}
            )
            with urllib.request.urlopen(
                req, timeout=10, context=ssl.create_default_context()
            ) as response:
                hsts_header = response.headers.get("Strict-Transport-Security")
                if hsts_header:
                    findings.append(f"HSTS header present: {hsts_header}")
                else:
                    findings.append("HSTS header missing")
        except Exception as e:
            findings.append(f"HSTS check failed: {e}")

        if not findings:
            findings = ["No issues detected"]

        return ToolExecutionResult(
            success=True,
            output=json.dumps(
                {
                    "url": url,
                    "findings": findings,
                }
            ),
            metadata={"url": url},
        )
