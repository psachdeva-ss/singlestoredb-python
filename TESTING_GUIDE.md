# Testing run_udf_app - Guide for Beginners

This guide explains different approaches to testing the `run_udf_app` function in the SingleStoreDB Python SDK.

## Quick Start

Your sample code looks like this:
```python
from singlestoredb import apps
from singlestoredb.functions import udf

@udf
def hello() -> str:
    return "hello"

await apps.run_udf_app()
```

## Testing Challenges

Testing `run_udf_app` is challenging because it:
1. Starts a real web server (uvicorn)
2. Reads environment variables
3. Makes network calls
4. Manages global state

## Testing Approaches

### 1. Mock Everything (Recommended for Unit Tests)
- **File**: `test_apps.py` 
- **Best for**: Fast, reliable unit tests
- **Mocks**: Server, environment, network calls
- **Pros**: Fast, no external dependencies
- **Cons**: Might miss integration issues

### 2. Test Error Cases First (Easiest to Start)
- **File**: `test_apps_examples.py` (BeginnerTestExample)
- **Best for**: Learning, catching configuration errors
- **Focus**: Missing env vars, missing dependencies
- **Pros**: Simple to write, catches real problems
- **Cons**: Limited coverage

### 3. Pytest Style (Modern Approach)
- **File**: `test_apps_pytest.py`
- **Best for**: Clean, maintainable tests
- **Features**: Fixtures, parameterized tests
- **Pros**: Less boilerplate, better organization
- **Cons**: Need to learn pytest

### 4. Integration Tests (Most Realistic)
- **File**: `test_apps_examples.py` (InteractiveTestingExample)
- **Best for**: End-to-end validation
- **Tests**: Real UDF registration, actual function calls
- **Pros**: Tests real behavior
- **Cons**: Slower, more complex setup

## Running the Tests

```bash
# Run all tests
python -m pytest singlestoredb/tests/test_apps*.py

# Run specific test file
python -m pytest singlestoredb/tests/test_apps.py

# Run with coverage
python -m pytest --cov=singlestoredb.apps singlestoredb/tests/test_apps*.py

# Run specific test
python -m pytest singlestoredb/tests/test_apps.py::TestRunUdfApp::test_run_udf_app_basic_success
```

## Test Structure Explained

### Environment Variables Mock
```python
env_vars = {
    'SINGLESTOREDB_APP_LISTEN_PORT': '8080',
    'SINGLESTOREDB_NOVA_GATEWAY_ENABLED': 'true',
    # ... other required vars
}
```

### Server Mock
```python
mock_server = AsyncMock()
mock_server.serve = AsyncMock()
mock_server.wait_for_startup = AsyncMock()
```

### Application Mock
```python
mock_app = MagicMock()
mock_app.register_functions = MagicMock()
mock_app.get_function_info.return_value = {'hello': {'signature': 'hello() -> str'}}
```

## Common Test Patterns

### Testing Success Cases
```python
async def test_success():
    with patch.dict(os.environ, env_vars, clear=True):
        with patch('...AwaitableUvicornServer', return_value=mock_server):
            result = await run_udf_app()
            assert 'pythonudfs' in result.url
```

### Testing Error Cases
```python
async def test_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing"):
            await run_udf_app()
```

### Testing with Real UDFs
```python
@udf
def test_func() -> str:
    return "test"

async def test_with_udf():
    # ... setup mocks
    result = await run_udf_app()
    assert 'test_func' in result.functions
```

## What to Test

### Essential Tests
1. ✅ **Basic success case** - Function returns correct result
2. ✅ **Missing environment variables** - Raises appropriate errors
3. ✅ **Missing dependencies** - Handles missing uvicorn
4. ✅ **Configuration parsing** - Reads env vars correctly

### Advanced Tests
1. ✅ **Server lifecycle** - Properly shuts down existing servers
2. ✅ **Interactive vs non-interactive** - Different behavior modes
3. ✅ **UDF registration** - Functions are properly registered
4. ✅ **Error handling** - Gateway disabled, port conflicts

### Performance Tests
1. ⏳ **Startup time** - How long does server take to start?
2. ⏳ **Memory usage** - Does it leak memory?
3. ⏳ **Concurrent calls** - Multiple simultaneous calls

## Tips for Beginners

1. **Start with error tests** - They're easier and catch real problems
2. **Use pytest fixtures** - Reduces code duplication
3. **Mock external dependencies** - Keep tests fast and reliable
4. **Test one thing at a time** - Easier to debug when they fail
5. **Use descriptive test names** - Explains what went wrong
6. **Add comments** - Explain complex setup or assertions

## Debugging Failed Tests

### Common Issues
- **Import errors**: Check that all required modules are available
- **Environment variables**: Make sure all required vars are set in tests
- **Async issues**: Use `@pytest.mark.asyncio` for async tests
- **Mock problems**: Verify mock objects have the right methods

### Debugging Commands
```bash
# Run with verbose output
python -m pytest -v singlestoredb/tests/test_apps.py

# Run single test with debug output
python -m pytest -s singlestoredb/tests/test_apps.py::test_name

# See test coverage
python -m pytest --cov-report=html --cov=singlestoredb.apps
```

## Next Steps

1. **Pick an approach**: Start with error tests or basic mocking
2. **Run existing tests**: Make sure your environment works
3. **Write one test**: Start small with a simple case
4. **Expand coverage**: Add more test cases gradually
5. **Add integration tests**: Test with real UDFs when ready

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [unittest.mock documentation](https://docs.python.org/3/library/unittest.mock.html)
- [AsyncMock documentation](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
