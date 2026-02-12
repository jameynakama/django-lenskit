# Personal Claude directives

## Testing

- Read the Justfile to learn how to run commands like tests
- In particular, use `just test-all` to run all tests, but there are other more specific commands

## Code style

### Python

- I use strict ruff/mypy mode
  - Use modern type hints: `dict | None`, not `Optional[Dict]`
  - Use full typing (with annotations): `dict[str, Any]`, not `dict`
- Test methods need `-> None` return type
- Start test docstrings with "Should..."
