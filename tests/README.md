# IHACPA Tests Directory

This directory contains all test files for the IHACPA Python Package Review Automation system.

## Directory Structure

```
tests/
├── analysis/           # Analysis and investigation scripts
├── debug/             # Debug scripts for troubleshooting specific issues
├── integration/       # Integration tests for various components
├── unit/             # Unit tests (to be added)
├── utilities/        # Utility scripts for testing and data extraction
└── verification/     # Verification and validation scripts
```

## Running Tests

### Integration Tests
```bash
# Run all integration tests
python -m pytest tests/integration/

# Run specific integration test
python tests/integration/test_vulnerability_scanner.py
```

### Debug Scripts
```bash
# Run debug script for specific issue
python tests/debug/debug_scanner.py
```

### Analysis Scripts
```bash
# Run analysis script
python tests/analysis/analyze_manual_review.py
```

### Verification Scripts
```bash
# Run verification script
python tests/verification/full_verification.py
```

## Test Categories

### Integration Tests (`tests/integration/`)
- Full system integration tests
- API integration tests
- Database scanner tests
- Excel processing tests

### Debug Scripts (`tests/debug/`)
- Issue-specific debugging scripts
- Scanner debugging tools
- API troubleshooting scripts

### Analysis Scripts (`tests/analysis/`)
- Data analysis tools
- Excel formatting analysis
- Color and style investigations

### Verification Scripts (`tests/verification/`)
- System verification tools
- Fix validation scripts
- Regression testing tools

### Utilities (`tests/utilities/`)
- Helper scripts for data extraction
- Package information tools
- Summary generation scripts

## Adding New Tests

1. Place test files in the appropriate subdirectory
2. Follow naming conventions:
   - `test_*.py` for pytest-compatible tests
   - `debug_*.py` for debug scripts
   - `verify_*.py` for verification scripts
3. Update imports to use relative paths from the tests directory
4. Add appropriate documentation

## Dependencies

Tests require the main project dependencies plus:
- pytest
- pytest-asyncio
- pytest-cov

See `requirements.txt` in the project root for full dependencies.