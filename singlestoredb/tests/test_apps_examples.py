#!/usr/bin/env python
"""
Example tests for run_udf_app - Different approaches for beginners.

This file demonstrates various testing strategies you can use when testing
the run_udf_app function. Pick the approaches that work best for your needs.
"""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from singlestoredb.apps import run_udf_app
from singlestoredb.functions import udf


class BeginnerTestExample(unittest.TestCase):
    """Simple examples to get you started with testing run_udf_app."""

    def test_approach_1_mock_everything(self):
        """
        Approach 1: Mock all external dependencies.
        
        This is the safest approach for unit testing - you control everything
        and don't depend on external services or network calls.
        """
        
        # Define a simple UDF for testing
        @udf
        def simple_hello() -> str:
            return "Hello World"
        
        # Mock environment variables
        env_vars = {
            'SINGLESTOREDB_APP_LISTEN_PORT': '8080',
            'SINGLESTOREDB_APP_BASE_URL': 'http://localhost:8080',
            'SINGLESTOREDB_APP_BASE_PATH': '/api',
            'SINGLESTOREDB_NOTEBOOK_SERVER_ID': 'test-123',
            'SINGLESTOREDB_APP_TOKEN': 'fake-token',
            'SINGLESTOREDB_USER_TOKEN': 'fake-user-token',
            'SINGLESTOREDB_RUNNING_INTERACTIVELY': 'true',
            'SINGLESTOREDB_NOVA_GATEWAY_ENABLED': 'true',
            'SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT': 'http://fake-gateway.com',
        }
        
        async def run_test():
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer') as mock_server_class:
                    with patch('singlestoredb.apps._python_udfs.kill_process_by_port') as mock_kill:
                        with patch('singlestoredb.apps._python_udfs.Application') as mock_app_class:
                            
                            # Set up mocks
                            mock_server = AsyncMock()
                            mock_server.serve = AsyncMock()
                            mock_server.wait_for_startup = AsyncMock()
                            mock_server_class.return_value = mock_server
                            
                            mock_app = MagicMock()
                            mock_app.register_functions = MagicMock()
                            mock_app.get_function_info.return_value = {
                                'simple_hello': {'return_type': 'str'}
                            }
                            mock_app_class.return_value = mock_app
                            
                            # Call the function
                            result = await run_udf_app()
                            
                            # Assert what we expect
                            self.assertIn('pythonudfs', result.url)
                            self.assertIn('simple_hello', result.functions)
                            mock_kill.assert_called_once_with(8080)
        
        # Run the async test
        asyncio.run(run_test())

    def test_approach_2_focus_on_error_cases(self):
        """
        Approach 2: Test error handling.
        
        Testing error cases is often easier than testing success cases
        because you don't need to mock as much.
        """
        
        async def test_missing_env_vars():
            # Test with completely empty environment
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(RuntimeError) as context:
                    await run_udf_app()
                
                self.assertIn('Missing', str(context.exception))
        
        async def test_missing_uvicorn():
            # Test when uvicorn is not available
            with patch('singlestoredb.apps._python_udfs.uvicorn', None):
                with self.assertRaises(ImportError) as context:
                    await run_udf_app()
                
                self.assertIn('uvicorn is required', str(context.exception))
        
        # Run both error tests
        asyncio.run(test_missing_env_vars())
        asyncio.run(test_missing_uvicorn())

    def test_approach_3_test_configuration_parsing(self):
        """
        Approach 3: Test that configuration is parsed correctly.
        
        This tests the integration between run_udf_app and AppConfig
        without needing to actually start a server.
        """
        
        # Set up specific environment configuration
        env_vars = {
            'SINGLESTOREDB_APP_LISTEN_PORT': '9999',  # Custom port
            'SINGLESTOREDB_APP_BASE_URL': 'http://custom-host:9999',
            'SINGLESTOREDB_APP_BASE_PATH': '/custom-api',
            'SINGLESTOREDB_NOTEBOOK_SERVER_ID': 'custom-server-456',
            'SINGLESTOREDB_APP_TOKEN': 'custom-app-token',
            'SINGLESTOREDB_USER_TOKEN': 'custom-user-token',
            'SINGLESTOREDB_RUNNING_INTERACTIVELY': 'false',  # Non-interactive
            'SINGLESTOREDB_NOVA_GATEWAY_ENABLED': 'true',
            'SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT': 'http://custom-gateway.com',
        }
        
        async def run_test():
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer') as mock_server_class:
                    with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                        with patch('singlestoredb.apps._python_udfs.Application') as mock_app_class:
                            
                            # Set up minimal mocks
                            mock_server = AsyncMock()
                            mock_server.serve = AsyncMock()
                            mock_server.wait_for_startup = AsyncMock()
                            mock_server_class.return_value = mock_server
                            
                            mock_app = MagicMock()
                            mock_app.get_function_info.return_value = {}
                            mock_app_class.return_value = mock_app
                            
                            # Call the function
                            await run_udf_app()
                            
                            # Check that the app was created with correct parameters
                            mock_app_class.assert_called_once()
                            call_args = mock_app_class.call_args
                            
                            # Verify the base URL was constructed correctly
                            self.assertIn('custom-gateway.com', call_args.kwargs['url'])
                            self.assertIn('custom-server-456', call_args.kwargs['url'])
                            
                            # In non-interactive mode, register_functions should not be called
                            mock_app.register_functions.assert_not_called()
        
        asyncio.run(run_test())


class InteractiveTestingExample(unittest.TestCase):
    """
    Examples for testing with actual UDF registration.
    
    These tests actually register UDFs and test the integration,
    but still mock the server to avoid network calls.
    """

    def test_udf_registration_in_interactive_mode(self):
        """Test that UDFs are actually registered in interactive mode."""
        
        # Define test UDFs
        @udf
        def add_numbers(a: int, b: int) -> int:
            return a + b
        
        @udf  
        def greet(name: str) -> str:
            return f"Hello, {name}!"
        
        env_vars = {
            'SINGLESTOREDB_APP_LISTEN_PORT': '8080',
            'SINGLESTOREDB_APP_BASE_URL': 'http://localhost:8080',
            'SINGLESTOREDB_APP_BASE_PATH': '/api',
            'SINGLESTOREDB_NOTEBOOK_SERVER_ID': 'test-123',
            'SINGLESTOREDB_APP_TOKEN': 'fake-token',
            'SINGLESTOREDB_USER_TOKEN': 'fake-user-token',
            'SINGLESTOREDB_RUNNING_INTERACTIVELY': 'true',
            'SINGLESTOREDB_NOVA_GATEWAY_ENABLED': 'true',
            'SINGLESTOREDB_NOVA_GATEWAY_ENDPOINT': 'http://fake-gateway.com',
        }
        
        async def run_test():
            with patch.dict(os.environ, env_vars, clear=True):
                with patch('singlestoredb.apps._python_udfs.AwaitableUvicornServer') as mock_server_class:
                    with patch('singlestoredb.apps._python_udfs.kill_process_by_port'):
                        
                        # Don't mock the Application - let it work with real UDFs
                        mock_server = AsyncMock()
                        mock_server.serve = AsyncMock()
                        mock_server.wait_for_startup = AsyncMock()
                        mock_server_class.return_value = mock_server
                        
                        # Call the function
                        result = await run_udf_app()
                        
                        # Check that our UDFs are in the result
                        self.assertIn('add_numbers', result.functions)
                        self.assertIn('greet', result.functions)
                        
                        # Check function signatures
                        add_func = result.functions['add_numbers']
                        greet_func = result.functions['greet']
                        
                        # These will contain the actual function metadata
                        self.assertIn('signature', add_func)
                        self.assertIn('signature', greet_func)
        
        asyncio.run(run_test())


if __name__ == '__main__':
    # Run specific test classes or all tests
    unittest.main()
