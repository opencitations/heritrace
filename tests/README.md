# Testing Heritrace

This directory contains tests for the Heritrace application.

## Test Structure

The test suite is organized into two main categories:

### Unit Tests (`unit/`)
Tests that verify individual components in isolation, without requiring external services:
- `test_app.py`: Tests for basic application initialization and configuration
- `test_extensions.py`: Tests for Flask extensions and utilities
- `test_routes.py`: Tests for route handlers using mocked dependencies
- `test_api.py`: Tests for API endpoints using mocked services
- And other component-specific tests that don't require external services

### Integration Tests (`integration/`)
Tests that verify interactions between components using real external services:
- `test_editor_integration.py`: Tests for the editor module with real database connections
- `test_entity_integration.py`: Tests for entity operations using actual databases
- `test_sparql_utils_integration.py`: Tests for SPARQL utilities with real triplestore
- And other tests that require external services like databases

### Common Files
- `conftest.py`: Contains pytest fixtures and configuration
- `test_config.py`: Contains test-specific configuration settings

## Test Database Setup

The integration tests require dedicated test databases. These are separate database instances running on different ports than the main application:

- Test Dataset database on port 9999
- Test Provenance database on port 9998
- Test Redis instance on port 6380 (database 1)

### Starting Test Databases

Use the provided scripts to start the test databases (required for integration tests):

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