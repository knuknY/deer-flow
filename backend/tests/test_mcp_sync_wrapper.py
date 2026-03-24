import asyncio
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


class MockArgs(BaseModel):
    x: int = Field(..., description="test param")

def test_mcp_tool_sync_wrapper_generation():
    """Test that get_mcp_tools correctly adds a sync func to async-only tools."""
    from deerflow.mcp.tools import get_mcp_tools
    
    async def mock_coro(x: int):
        return f"result: {x}"

    mock_tool = StructuredTool(
        name="test_tool",
        description="test description",
        args_schema=MockArgs,
        func=None,  # Sync func is missing
        coroutine=mock_coro
    )

    mock_client_instance = MagicMock()
    # Make get_tools an async mock because it's awaited in the code
    async def async_get_tools():
        return [mock_tool]
    mock_client_instance.get_tools = async_get_tools

    with patch("langchain_mcp_adapters.client.MultiServerMCPClient", return_value=mock_client_instance), \
         patch("deerflow.config.extensions_config.ExtensionsConfig.from_file"), \
         patch("deerflow.mcp.tools.build_servers_config", return_value={"test-server": {}}), \
         patch("deerflow.mcp.tools.get_initial_oauth_headers", return_value={}):
        
        # Run the async function using asyncio.run
        tools = asyncio.run(get_mcp_tools())
        
        assert len(tools) == 1
        patched_tool = tools[0]
        
        # Verify func is now populated
        assert patched_tool.func is not None
        
        # Verify it works (sync call)
        result = patched_tool.func(x=42)
        assert result == "result: 42"

def test_mcp_tool_sync_wrapper_in_running_loop():
    """Test that the sync wrapper works even when an event loop is already running."""
    async def mock_coro(x: int):
        await asyncio.sleep(0.01)
        return f"async_result: {x}"

    mock_tool = StructuredTool(
        name="test_tool",
        description="test description",
        args_schema=MockArgs,
        func=None,
        coroutine=mock_coro
    )

    from deerflow.mcp.tools import _SYNC_TOOL_EXECUTOR
    
    def apply_patch(tool):
        def make_sync_wrapper(coro, tool_name: str):
            def sync_wrapper(*args, **kwargs):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                try:
                    if loop is not None and loop.is_running():
                        future = _SYNC_TOOL_EXECUTOR.submit(asyncio.run, coro(*args, **kwargs))
                        return future.result()
                    else:
                        return asyncio.run(coro(*args, **kwargs))
                except Exception:
                    raise
            return sync_wrapper
        tool.func = make_sync_wrapper(tool.coroutine, tool.name)

    apply_patch(mock_tool)

    async def run_in_loop():
        # This call to mock_tool.func() would normally fail with asyncio.run() 
        # but should succeed due to ThreadPoolExecutor
        return mock_tool.func(x=100)

    result = asyncio.run(run_in_loop())
    assert result == "async_result: 100"

def test_mcp_tool_sync_wrapper_exception_logging():
    """Test that exceptions in the tool are logged and re-raised."""
    async def error_coro():
        raise ValueError("Tool failure")

    mock_tool = StructuredTool(
        name="error_tool",
        description="test",
        args_schema=MockArgs,
        func=None,
        coroutine=error_coro
    )

    def apply_patch(tool):
        from deerflow.mcp.tools import logger
        def make_sync_wrapper(coro, tool_name: str):
            def sync_wrapper(*args, **kwargs):
                try:
                    return asyncio.run(coro(*args, **kwargs))
                except Exception as e:
                    logger.error(f"Error invoking MCP tool '{tool_name}' via sync wrapper: {e}", exc_info=True)
                    raise
            return sync_wrapper
        tool.func = make_sync_wrapper(tool.coroutine, tool.name)

    apply_patch(mock_tool)

    with patch("deerflow.mcp.tools.logger.error") as mock_log_error:
        with pytest.raises(ValueError, match="Tool failure"):
            mock_tool.func()
        mock_log_error.assert_called_once()
        assert "error_tool" in mock_log_error.call_args[0][0]
