"""
Pytest-style tests for run_udf_app.

This file shows how to write tests using pytest instead of unittest.
pytest is often preferred for its simpler syntax and better fixtures.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from singlestoredb.apps import run_udf_app
from singlestoredb.functions import udf


# Pytest fixtures for common test data
@pytest.fixture
def mock_env_vars():
    """Fixture providing mock environment variables."""
    return {
        'SINGLESTOREDB_APP_LISTEN_PORT': '8080',
        'SINGLESTOREDB_APP_BASE_URL': 'http://localhost:8080',
        'SINGLESTOREDB_APP_BASE_PATH': '/api',
        'SINGLESTOREDB_NOTEBOOK_SERVER_ID': 'test-server-123',
        'SINGLESTOREDB_APP_TOKEN': 'test-app-token',
        'SINGLESTOREDB_USER_TOKEN': 'test-user-token',
        'SINGLESTOREDB_RUNNING_INTERACTIVELY': 'true',
        'SINGLESTOREDB_NOVA_GATEWAY_ENABLED': 'true',
        'SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT': 'http://gateway.test.com',
    }


@pytest.fixture
def mock_server():
    """Fixture providing a mock uvicorn server."""
    server = AsyncMock()
    server.serve = AsyncMock()
    server.wait_for_startup = AsyncMock()
    server.shutdown = AsyncMock()
    return server


@pytest.fixture
def mock_app():
    """Fixture providing a mock ASGI application."""
    app = MagicMock()
    app.register_functions = MagicMock()
    app.get_function_info.return_value = {'test_func': {'signature': 'test() -> str'}}
    return app


# Simple pytest tests
async def test_run_udf_app_success(mock_env_vars, mock_server, mock_app):
    """Test successful execution of run_udf_app."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.Application', return_value=mock_app):
                with patch('singlestoredb.apps._python_udfs.kill_process_by_port') as mock_kill:
                    
                    result = await run_udf_app()
                    
                    # Assertions
                    assert 'pythonudfs' in result.url
                    assert 'test_func' in result.functions
                    mock_kill.assert_called_once_with(8080)
                    mock_app.register_functions.assert_called_once_with(replace=True)


async def test_run_udf_app_missing_env_vars():
    """Test run_udf_app with missing environment variables."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing"):
            await run_udf_app()


async def test_run_udf_app_missing_uvicorn():
    """Test run_udf_app when uvicorn is not installed."""
    with patch('singlestoredb.apps._python_udfs.uvicorn', None):
        with pytest.raises(ImportError, match="package uvicorn is required"):
            await run_udf_app()


async def test_run_udf_app_with_existing_server(mock_env_vars, mock_server, mock_app):
    """Test run_udf_app when there's already a running server."""
    # Set up an existing server
    existing_server = AsyncMock()
    existing_server.shutdown = AsyncMock()
    
    with patch.dict(os.environ, mock_env_vars, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.Application', return_value=mock_app):
                with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                    # Simulate existing server
                    import singlestoredb.apps._python_udfs
                    singlestoredb.apps._python_udfs._running_server = existing_server
                    
                    try:
                        await run_udf_app()
                        
                        # Verify existing server was shut down
                        existing_server.shutdown.assert_called_once()
                    finally:
                        # Clean up
                        singlestoredb.apps._python_udfs._running_server = None


async def test_run_udf_app_non_interactive_mode(mock_env_vars, mock_server, mock_app):
    """Test run_udf_app in non-interactive mode."""
    # Modify env vars for non-interactive mode
    non_interactive_env = mock_env_vars.copy()
    non_interactive_env['SINGLESTOREDB_RUNNING_INTERACTIVELY'] = 'false'
    
    with patch.dict(os.environ, non_interactive_env, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.Application', return_value=mock_app):
                with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                    
                    await run_udf_app()
                    
                    # In non-interactive mode, register_functions should not be called
                    mock_app.register_functions.assert_not_called()


async def test_run_udf_app_gateway_not_enabled(mock_env_vars):
    """Test run_udf_app when Nova Gateway is not enabled."""
    # Modify env vars to disable gateway
    disabled_gateway_env = mock_env_vars.copy()
    disabled_gateway_env['SINGLESTOREDB_NOVA_GATEWAY_ENABLED'] = 'false'
    
    with patch.dict(os.environ, disabled_gateway_env, clear=True):
        with pytest.raises(RuntimeError, match="Python UDFs are not available if Nova Gateway is not enabled"):
            await run_udf_app()


# Parameterized tests
@pytest.mark.parametrize("log_level", ["debug", "info", "warning", "error", "critical"])
async def test_run_udf_app_different_log_levels(mock_env_vars, mock_server, mock_app, log_level):
    """Test run_udf_app with different log levels."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.Application', return_value=mock_app):
                with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                    with patch('singlestoredb.apps._python_udfs.uvicorn.Config') as mock_config:
                        
                        await run_udf_app(log_level=log_level)
                        
                        # Verify that uvicorn.Config was called with the correct log_level
                        mock_config.assert_called_once()
                        assert mock_config.call_args.kwargs['log_level'] == log_level


@pytest.mark.parametrize("kill_existing", [True, False])
async def test_run_udf_app_kill_existing_parameter(mock_env_vars, mock_server, mock_app, kill_existing):
    """Test run_udf_app with different kill_existing_app_server values."""
    with patch.dict(os.environ, mock_env_vars, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.Application', return_value=mock_app):
                with patch('singlestoredb.apps._python_udfs.kill_process_by_port') as mock_kill:
                    
                    await run_udf_app(kill_existing_app_server=kill_existing)
                    
                    if kill_existing:
                        mock_kill.assert_called_once_with(8080)
                    else:
                        mock_kill.assert_not_called()


# Integration test with actual UDF
async def test_run_udf_app_with_real_udf(mock_env_vars, mock_server):
    """Test run_udf_app with an actual UDF definition."""
    
    # Define a test UDF
    @udf
    def hello_pytest() -> str:
        return "Hello from pytest!"
    
    with patch.dict(os.environ, mock_env_vars, clear=True):
        with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer', return_value=mock_server):
            with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                
                result = await run_udf_app()
                
                # Verify the UDF is in the result
                assert 'hello_pytest' in result.functions
                assert result.functions['hello_pytest'] is not None


# Smoke tests for quick validation
class TestSmokeTests:
    """Quick smoke tests that can run without much setup."""
    
    def test_import_works(self):
        """Test that we can import run_udf_app without errors."""
        from singlestoredb.apps import run_udf_app
        assert callable(run_udf_app)
    
    def test_udf_decorator_works(self):
        """Test that the UDF decorator works."""
        @udf
        def smoke_test() -> str:
            return "smoke"
        
        assert callable(smoke_test)
        assert smoke_test() == "smoke"
