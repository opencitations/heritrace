# Testing Heritrace

This directory contains tests for the Heritrace application.

## Test Structure

- `conftest.py`: Contains pytest fixtures and configuration
- `unit/`: Contains unit tests for individual components
  - `test_app.py`: Tests for application initialization
  - `test_extensions.py`: Tests for the extensions module
  - `test_routes.py`: Tests for the routes
  - `test_editor.py`: Tests for the editor module

## Running Tests

To run all tests:

```bash
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