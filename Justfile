set shell := ["bash", "-cu"]

# Python in local venv (lowercase variable names - just identifiers are lowercase)
py := ".venv/bin/python"
ruff := ".venv/bin/ruff"  # use venv ruff to satisfy project constraint

default:
  @just --list

# Create a local virtualenv
venv:
  python3 -m venv .venv
  .venv/bin/python -m pip install -U pip

# Install deps with pip (editable) — pass extra args via `args:=...` if needed
# Example: just deps-pip args="-e 'packages/django_lenskit_audit[test]'"
deps-pip args="":
  .venv/bin/python -m pip install -e 'packages/django_lenskit_audit[test]' -e 'packages/django_lenskit_fixtures[test]' {{args}}

# Install deps with uv — pass extra args via `args:=...` if needed
# Example: just deps-uv args="-e 'packages/django_lenskit_audit[test]'"
deps-uv args="":
  uv pip install -e 'packages/django_lenskit_audit[test]' -e 'packages/django_lenskit_fixtures[test]' {{args}}

# Lint with ruff (from venv)
# Example: just lint args="packages/django_lenskit_audit -q"
lint args=".":
  .venv/bin/ruff check {{args}}

# Format with ruff (from venv)
fmt:
  # Checks
  #   I: Import order
  #   F401: Unused imports
  .venv/bin/ruff check --select I,F401 --fix .
  .venv/bin/ruff format .

# Run audit tests — pass through extra pytest flags via `args:=...`
# Examples:
#  - just test-audit
#  - just test-audit args="-q -k rule"
test-audit args="-q --cov=django_lenskit_audit --cov-report=term-missing":
  .venv/bin/python -m pytest {{args}} packages/django_lenskit_audit

# Run fixtures tests — pass through extra pytest flags via `args:=...`
# Examples:
#  - just test-fixtures
#  - just test-fixtures args="-q -k export"
test-fixtures args="-q --cov=django_lenskit_fixtures --cov-report=term-missing":
  .venv/bin/python -m pytest {{args}} --ds=django_lenskit_fixtures.tests.settings packages/django_lenskit_fixtures

# Run both test suites (add extra pytest flags via `args:=...`)
test-all args="-q":
  just test-audit args="{{args}}"
  just test-fixtures args="{{args}}"

# Sample project: run audit command in the demo admin project
# Pass through manage.py args via `args:=...`
# Examples:
#  - just audit-admin
#  - just audit-admin args="--first-party-only --html=admin_audit.html"
audit-admin args="":
  .venv/bin/python packages/django_lenskit_admin/manage.py audit_admin {{args}}

# Clean typical bytecode and cache folders
clean:
  rm -rf .pytest_cache **/__pycache__ .ruff_cache
