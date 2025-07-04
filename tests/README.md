# Discarr Testing Framework

This directory contains the comprehensive testing suite for the Discarr Discord bot.

## Test Structure

```
tests/
├── unit/                   # Unit tests for individual components
│   ├── test_settings.py    # Settings configuration tests
│   ├── test_time_utils.py  # Time utility function tests
│   └── test_base_client.py # Base client functionality tests
├── integration/            # Integration tests
│   └── test_api_clients.py # API client integration tests
└── README.md              # This file
```

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run only unit tests
python run_tests.py tests/unit/

# Run only integration tests
python run_tests.py tests/integration/

# Run specific test file
python run_tests.py tests/unit/test_settings.py

# Run with coverage
python run_tests.py tests/unit/ --cov=src --cov-report=html
```

### Using pytest directly

```bash
# Install dependencies first
pip install -r requirements.txt

# Run tests with pytest
pytest tests/

# Run with coverage
pytest tests/ --cov=src --cov-report=html --cov-report=term-missing
```

## Test Categories

### Unit Tests

Unit tests focus on testing individual components in isolation:

- **Settings Tests** (`test_settings.py`): Test configuration loading, validation, and environment variable handling
- **Time Utils Tests** (`test_time_utils.py`): Test time formatting, parsing, and Discord timestamp functions
- **Base Client Tests** (`test_base_client.py`): Test the base media client functionality, HTTP requests, and error handling
- **Discord Bot Import Tests** (`test_discord_bot_imports.py`): Test critical Discord.py library imports and verify no naming conflicts (essential for Docker deployment)

### Integration Tests

Integration tests verify that components work together correctly:

- **API Client Tests** (`test_api_clients.py`): Test Radarr and Sonarr client integration, API request formatting, and response handling

## Environment Variables for Testing

### Required for Unit Tests
No special environment variables are required for unit tests as they use mocking.

### Optional for Integration Tests
Set these environment variables to run integration tests against real services:

```bash
# Enable integration tests
export RUN_INTEGRATION_TESTS=true

# Test API endpoints (optional, defaults to localhost)
export TEST_RADARR_URL=http://your-radarr-instance:7878
export TEST_RADARR_API_KEY=your_radarr_api_key
export TEST_SONARR_URL=http://your-sonarr-instance:8989
export TEST_SONARR_API_KEY=your_sonarr_api_key
```

## CI/CD Integration

The testing framework is integrated with GitHub Actions for continuous integration:

- **Multiple Python Versions**: Tests run on Python 3.8, 3.9, 3.10, and 3.11
- **Code Coverage**: Coverage reports are generated and uploaded to Codecov
- **Security Scanning**: Safety and Bandit security checks
- **Docker Testing**: Docker image build and basic functionality tests

## Test Configuration

### pytest.ini
The `pytest.ini` file in the root directory configures pytest behavior:
- Test discovery patterns
- Output formatting
- Coverage settings
- Custom markers for test categorization

### Markers
Tests can be marked with custom markers:
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests

## Writing New Tests

### Unit Test Example

```python
import unittest
from unittest.mock import patch, Mock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.instance = YourClass()
    
    def test_your_method(self):
        """Test your method functionality."""
        result = self.instance.your_method("test_input")
        self.assertEqual(result, "expected_output")
    
    @patch('your_module.external_dependency')
    def test_with_mock(self, mock_dependency):
        """Test with mocked external dependency."""
        mock_dependency.return_value = "mocked_result"
        result = self.instance.method_using_dependency()
        self.assertEqual(result, "expected_result")
```

### Integration Test Example

```python
import unittest
import os

class TestIntegration(unittest.TestCase):
    @unittest.skipUnless(
        os.getenv('RUN_INTEGRATION_TESTS') == 'true',
        "Integration tests disabled"
    )
    def test_real_integration(self):
        """Test real integration with external services."""
        # Your integration test code here
        pass
```

## Best Practices

1. **Isolation**: Unit tests should not depend on external services
2. **Mocking**: Use mocks for external dependencies in unit tests
3. **Descriptive Names**: Test method names should clearly describe what is being tested
4. **Setup/Teardown**: Use setUp() and tearDown() methods for test fixtures
5. **Assertions**: Use specific assertions (assertEqual, assertIn, etc.) rather than assertTrue
6. **Coverage**: Aim for high test coverage but focus on meaningful tests
7. **Documentation**: Include docstrings explaining what each test verifies

## Troubleshooting

### Import Errors
If you encounter import errors, ensure:
1. The `src` directory is in your Python path
2. All `__init__.py` files are present
3. You're running tests from the project root directory

### Mock Issues
When mocking:
1. Mock at the point of use, not the point of definition
2. Use `patch` as a decorator or context manager
3. Verify mock calls with `assert_called_with()`

### Coverage Issues
For accurate coverage:
1. Run tests with `--cov=src` to include the source directory
2. Use `--cov-report=term-missing` to see uncovered lines
3. Exclude test files from coverage with `.coveragerc`

## Dependencies

Testing dependencies are included in `requirements.txt`:
- `pytest`: Test framework
- `pytest-cov`: Coverage plugin
- `pytest-mock`: Enhanced mocking capabilities

## Future Enhancements

Planned testing improvements:
- Performance tests for API clients
- End-to-end Discord bot tests
- Database integration tests (if applicable)
- Load testing for high-volume scenarios
- Automated test data generation
