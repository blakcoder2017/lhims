# LHIMS Test Suite

This directory contains tests for the Local Health Information Management System.

## Test Structure

- `conftest.py`: Pytest configuration and shared fixtures
- `test_charge_automation.py`: Tests for automated charge aggregation
- `test_validation.py`: Tests for validation utilities

## Running Tests

### Install Dependencies

```bash
pip install pytest pytest-asyncio
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_validation.py
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

### Run Only Unit Tests

```bash
pytest -m unit
```

### Run Only Integration Tests

```bash
pytest -m integration
```

## Test Categories

- **Unit Tests**: Test individual functions and components in isolation
- **Integration Tests**: Test interactions between components
- **Slow Tests**: Tests that take longer to run (marked with `@pytest.mark.slow`)

## Writing New Tests

1. Create a new test file following the naming convention: `test_*.py`
2. Use pytest fixtures from `conftest.py` for database sessions and test clients
3. Mark tests with appropriate markers (`@pytest.mark.unit`, `@pytest.mark.integration`)
4. Follow the Arrange-Act-Assert pattern

## Example Test

```python
import pytest

@pytest.mark.unit
def test_example_function():
    """Test description."""
    # Arrange
    input_value = "test"
    
    # Act
    result = example_function(input_value)
    
    # Assert
    assert result == "expected"
```

