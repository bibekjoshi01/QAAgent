import pytest

from engine.tools.security import SSLAuditTool


@pytest.mark.asyncio
async def test_ssl_valid_site():
    tool = SSLAuditTool()
    result = await tool.execute({"url": "https://example.com"})

    assert result.success is True
    assert result.error is None
    assert result.output is not None
    assert "Issued by" in result.output


@pytest.mark.asyncio
async def test_ssl_invalid_domain():
    tool = SSLAuditTool()
    result = await tool.execute({"url": "https://nonexistent-domain-xyz-123.com"})

    assert result.success is False
    assert result.error is not None
