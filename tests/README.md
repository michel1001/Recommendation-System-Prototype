# Tests

## Purpose
This directory contains unit tests, integration tests, and test utilities.

## Structure
- **test_data.py**: Tests for data processing module
- **test_ml_model.py**: Tests for the supervised ML model
- **test_api.py**: Tests for API endpoints
- **conftest.py**: Pytest configuration and fixtures

## Running Tests
```bash
pytest tests/
pytest tests/ -v  # Verbose output
pytest tests/ --cov  # With coverage report
```
