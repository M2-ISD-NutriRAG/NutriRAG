# How to Write Tests in Python with pytest

A simple guide to writing tests using pytest with markers.

---

## Basic Test Structure

Write a simple test:

```python
def test_addition():
    result = 2 + 2
    assert result == 4
```

Follow the **Arrange-Act-Assert** pattern:

```python
def test_list_operations():
    # Arrange - Set up test data
    my_list = [1, 2, 3]

    # Act - Perform the action
    my_list.append(4)

    # Assert - Check the result
    assert len(my_list) == 4
    assert my_list[-1] == 4
```

---

## Using Markers

Markers categorize your tests. Our project uses these markers (see `pytest.ini`):

- `@pytest.mark.unit` - Fast, isolated tests
- `@pytest.mark.integration` - Tests with external dependencies
- `@pytest.mark.contract` - API contract tests

---

## Marker Examples

### Single Marker

```python
import pytest

@pytest.mark.unit
def test_simple_function():
    assert 2 + 2 == 4
```

### Multiple Markers

```python
@pytest.mark.integration
@pytest.mark.slow
def test_full_workflow():
    # This is both an integration test and slow
    pass
```

### Skip Tests

```python
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

@pytest.mark.skipif(sys.version_info < (3, 8), reason="Requires Python 3.8+")
def test_modern_feature():
    pass
```

### Parametrized Tests

```python
@pytest.mark.unit
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

---

## Running Tests

| Command                           | Description                |
| --------------------------------- | -------------------------- |
| `pytest`                          | Run all tests              |
| `pytest -v`                       | Verbose output             |
| `pytest -m unit`                  | Run only unit tests        |
| `pytest -m integration`           | Run only integration tests |
| `pytest -m contract`              | Run only contract tests    |
| `pytest -m "unit or integration"` | Run multiple types         |
| `pytest -m "not slow"`            | Exclude slow tests         |
| `pytest tests/unit/`              | Run specific directory     |

---

## Using Fixtures

Fixtures provide reusable setup:

```python
import pytest

@pytest.fixture
def sample_data():
    return {"name": "Test", "value": 42}

@pytest.mark.unit
def test_with_fixture(sample_data):
    assert sample_data["name"] == "Test"
    assert sample_data["value"] == 42
```

---

## Project Structure

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Tests with external dependencies
├── contract/       # API contract tests
└── fixtures/       # Shared test fixtures
```

---

## Common Assertions

```python
# Equality
assert value == expected

# Truthiness
assert is_valid

# Exceptions
with pytest.raises(ValueError):
    raise ValueError("error")

# Approximate (for floats)
assert 3.14159 == pytest.approx(3.14, rel=0.01)

# Membership
assert "item" in my_list

# Type checking
assert isinstance(obj, MyClass)
```

---

## Quick Tips

✓ **One test, one thing** - Test one behavior per test function  
✓ **Clear names** - Use descriptive test names like `test_user_cannot_login_with_invalid_password`  
✓ **Use markers** - Always mark tests as `unit`, `integration`, or `contract`  
✓ **Fast feedback** - Run `pytest -m unit` frequently during development  
✓ **Organize** - Keep test types in separate directories
