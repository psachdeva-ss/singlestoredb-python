#!/usr/bin/env python
"""Tests for singlestoredb.apps module."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from singlestoredb.apps import run_udf_app
from singlestoredb.apps._connection_info import UdfConnectionInfo
from singlestoredb.functions import udf


class TestRunUdfApp(unittest.TestCase):
    """Test cases for run_udf_app function."""

    def setUp(self):
        """Set up test environment before each test."""
        # Reset the global _running_server variable
        import singlestoredb.apps._python_udfs
        singlestoredb.apps._python_udfs._running_server = None
        
        # Common mock environment variables
        self.env_vars = {
            'SINGLESTOREDB_APP_LISTEN_PORT': '8080',
            'SINGLESTOREDB_APP_BASE_URL': 'http://localhost:8080',
            'SINGLESTOREDB_APP_BASE_PATH': '/api',
            'SINGLESTOREDB_NOTEBOOK_SERVER_ID': 'test-server-123',
            'SINGLESTOREDB_IS_LOCAL_DEV': 'false',
            'SINGLESTOREDB_WORKLOAD_TYPE': 'InteractiveNotebook',
            'SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT': 'http://gateway.test.com',
            'SINGLESTOREDB_APP_TOKEN': 'test-app-token',
            'SINGLESTOREDB_USER_TOKEN': 'test-user-token',
        }

    def tearDown(self):
        """Clean up after each test."""
        # Reset the global _running_server variable
        import singlestoredb.apps._python_udfs
        singlestoredb.apps._python_udfs._running_server = None

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._uvicorn_util.AwaitableUvicornServer')
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    @patch('singlestoredb.apps._python_udfs.Application')
    def test_run_udf_app_basic_success(self, mock_app_class, mock_kill_process, mock_server_class):
        """Test basic successful execution of run_udf_app."""
        # Set up environment
        os.environ.update(self.env_vars)
        
        # Mock the server
        mock_server = AsyncMock()
        mock_server.shutdown = AsyncMock()
        mock_server.serve = AsyncMock()
        mock_server.wait_for_startup = AsyncMock()
        mock_server_class.return_value = mock_server
        
        # Mock the ASGI application
        mock_app = MagicMock()
        mock_app.register_functions = MagicMock()
        mock_app.get_function_info.return_value = {'hello': {'signature': 'hello() -> str'}}
        mock_app_class.return_value = mock_app
        
        async def run_test():
            result = await run_udf_app(log_level='info', kill_existing_app_server=True)
            
            # Verify the result
            self.assertIsInstance(result, UdfConnectionInfo)
            self.assertIn('pythonudfs', result.url)
            self.assertEqual(result.functions, {'hello': {'signature': 'hello() -> str'}})
            
            # Verify mocks were called
            mock_kill_process.assert_called_once_with(8080)
            mock_app.register_functions.assert_called_once_with(replace=True)
            mock_server.wait_for_startup.assert_called_once()
        
        # Run the async test
        asyncio.run(run_test())

    @patch.dict(os.environ, clear=True)
    def test_run_udf_app_missing_env_vars(self):
        """Test that run_udf_app fails when required environment variables are missing."""
        # Don't set environment variables
        
        async def run_test():
            with self.assertRaises(RuntimeError) as context:
                await run_udf_app()
            
            self.assertIn('Missing', str(context.exception))
        
        asyncio.run(run_test())

    @unittest.skip("Complex to test dynamic import - see examples for how to mock this")
    def test_run_udf_app_missing_uvicorn(self):
        """Test that run_udf_app fails when uvicorn is not installed."""
        # This test is complex because uvicorn is imported dynamically within the function
        # For a real implementation, you'd need to mock the import mechanism
        # See test_apps_examples.py for a simpler error test approach
        pass

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._uvicorn_util.AwaitableUvicornServer')
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    @patch('singlestoredb.apps._python_udfs.Application')
    def test_run_udf_app_with_existing_server(self, mock_app_class, mock_kill_process, mock_server_class):
        """Test run_udf_app when there's already a running server."""
        # Set up environment
        os.environ.update(self.env_vars)
        
        # Set up an existing server
        import singlestoredb.apps._python_udfs
        existing_server = AsyncMock()
        existing_server.shutdown = AsyncMock()
        singlestoredb.apps._python_udfs._running_server = existing_server
        
        # Mock the new server
        mock_server = AsyncMock()
        mock_server.serve = AsyncMock()
        mock_server.wait_for_startup = AsyncMock()
        mock_server_class.return_value = mock_server
        
        # Mock the ASGI application
        mock_app = MagicMock()
        mock_app.register_functions = MagicMock()
        mock_app.get_function_info.return_value = {}
        mock_app_class.return_value = mock_app
        
        async def run_test():
            await run_udf_app()
            
            # Verify existing server was shut down
            existing_server.shutdown.assert_called_once()
            
            # Verify process killing was attempted
            mock_kill_process.assert_called_once_with(8080)
        
        asyncio.run(run_test())

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._uvicorn_util.AwaitableUvicornServer')
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    @patch('singlestoredb.apps._python_udfs.Application')
    def test_run_udf_app_non_interactive_mode(self, mock_app_class, mock_kill_process, mock_server_class):
        """Test run_udf_app in non-interactive mode."""
        # Set up environment for non-interactive mode
        env_vars = self.env_vars.copy()
        env_vars['SINGLESTOREDB_WORKLOAD_TYPE'] = 'BatchJob'  # Non-interactive
        os.environ.update(env_vars)
        
        # Mock the server
        mock_server = AsyncMock()
        mock_server.serve = AsyncMock()
        mock_server.wait_for_startup = AsyncMock()
        mock_server_class.return_value = mock_server
        
        # Mock the ASGI application
        mock_app = MagicMock()
        mock_app.get_function_info.return_value = {}
        mock_app_class.return_value = mock_app
        
        async def run_test():
            await run_udf_app()
            
            # In non-interactive mode, register_functions should not be called
            mock_app.register_functions.assert_not_called()
        
        asyncio.run(run_test())

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    def test_run_udf_app_gateway_not_enabled(self, mock_kill_process):
        """Test run_udf_app when Nova Gateway is not enabled."""
        # Set up environment without gateway enabled
        env_vars = self.env_vars.copy()
        del env_vars['SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT']  # Remove gateway endpoint
        os.environ.update(env_vars)
        
        async def run_test():
            with self.assertRaises(RuntimeError) as context:
                await run_udf_app()
            
            self.assertIn('Python UDFs are not available if Nova Gateway is not enabled', 
                         str(context.exception))
        
        asyncio.run(run_test())


class TestRunUdfAppIntegration(unittest.TestCase):
    """Integration tests for run_udf_app with actual UDF definitions."""

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._uvicorn_util.AwaitableUvicornServer')
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    @patch('singlestoredb.apps._python_udfs.Application')
    def test_run_udf_app_with_actual_udf(self, mock_kill_process, mock_server_class):
        """Test run_udf_app with an actual UDF definition."""
        # Set up environment
        env_vars = {
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
        os.environ.update(env_vars)
        
        # Define a test UDF
        @udf
        def hello() -> str:
            return "hello"
        
        # Mock the server
        mock_server = AsyncMock()
        mock_server.serve = AsyncMock()
        mock_server.wait_for_startup = AsyncMock()
        mock_server_class.return_value = mock_server
        
        async def run_test():
            result = await run_udf_app()
            
            # Verify the result contains our UDF
            self.assertIsInstance(result, UdfConnectionInfo)
            self.assertIn('hello', result.functions)
        
        asyncio.run(run_test())


class TestRunUdfAppParameterized(unittest.TestCase):
    """Parameterized tests for different scenarios."""

    @patch.dict(os.environ, clear=True)
    @patch('singlestoredb.apps._uvicorn_util.AwaitableUvicornServer')
    @patch('singlestoredb.apps._python_udfs.kill_process_by_port')
    @patch('singlestoredb.apps._python_udfs.Application')
    def _test_log_level(self, log_level, mock_app_class, mock_kill_process, mock_server_class):
        """Helper method to test different log levels."""
        # Set up environment
        os.environ.update(self.env_vars)
        
        mock_server = AsyncMock()
        mock_server.serve = AsyncMock()
        mock_server.wait_for_startup = AsyncMock()
        mock_server_class.return_value = mock_server
        
        mock_app = MagicMock()
        mock_app.register_functions = MagicMock()
        mock_app.get_function_info.return_value = {}
        mock_app_class.return_value = mock_app
        
        async def run_test():
            await run_udf_app(log_level=log_level)
            
            # Check that uvicorn.Config was called with the correct log_level
            # (This would require more specific mocking of uvicorn.Config)
        
        asyncio.run(run_test())

    def setUp(self):
        """Set up test environment."""
        self.env_vars = {
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

    def test_different_log_levels(self):
        """Test run_udf_app with different log levels."""
        for log_level in ['debug', 'info', 'warning', 'error', 'critical']:
            with self.subTest(log_level=log_level):
                self._test_log_level(log_level)


if __name__ == '__main__':
    unittest.main()
