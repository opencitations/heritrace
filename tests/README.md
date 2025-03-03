# Testing Heritrace

This directory contains tests for the Heritrace application.

## Test Structure

- `conftest.py`: Contains pytest fixtures and configuration
- `test_config.py`: Contains test-specific configuration settings
- `unit/`: Contains unit tests for individual components
  - `test_app.py`: Tests for application initialization
  - `test_extensions.py`: Tests for the extensions module
  - `test_routes.py`: Tests for the routes
  - `test_editor.py`: Tests for the editor module
  - `test_api.py`: Tests for the API routes

## Test Database Setup

Before running tests, you need to set up the test databases. The tests use separate database instances running on different ports than the main application:

- Test Dataset database on port 9999
- Test Provenance database on port 9998
- Test Redis instance on port 6380 (database 1)

### Starting Test Databases

Use the provided scripts to start the test databases:

For Unix/Linux/MacOS:
```bash
# Make the script executable if needed
chmod +x ./tests/start-test-databases.sh

# Start the test databases
./tests/start-test-databases.sh
```

For Windows (PowerShell):
```powershell
# Start the test databases
.\tests\Start-TestDatabases.ps1
```

### Stopping Test Databases

After running tests, stop the test databases:

For Unix/Linux/MacOS:
```bash
# Make the script executable if needed
chmod +x ./tests/stop-test-databases.sh

# Stop the test databases
./tests/stop-test-databases.sh
```

For Windows (PowerShell):
```powershell
# Stop the test databases
.\tests\Stop-TestDatabases.ps1
```

## Running Tests

To run all tests:

```bash
# Make sure test databases are running first
pytest
```

To run a specific test file:

```bash
pytest tests/unit/test_app.py
```

To run a specific test function:

```bash
pytest tests/unit/test_app.py::test_app_creation
```

To run tests with verbose output:

```bash
pytest -v
```

To run tests with coverage report:

```bash
pytest --cov=heritrace
```

## Writing Tests

When writing tests, follow these guidelines:

1. Each test function should test a single functionality
2. Use descriptive test function names that explain what is being tested
3. Use fixtures for common setup and teardown
4. Mock external dependencies to isolate the code being tested
5. Use assertions to verify the expected behavior

## Example Test

```python
def test_some_function():
    # Arrange: Set up the test
    input_data = "test input"
    expected_output = "expected result"
    
    # Act: Call the function being tested
    actual_output = some_function(input_data)
    
    # Assert: Verify the result
    assert actual_output == expected_output
``` 