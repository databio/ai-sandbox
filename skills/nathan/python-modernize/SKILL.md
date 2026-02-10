# Python Package Modernization

Modernize a legacy Python package to current standards. This is a complete overhaul — delete old packaging artifacts, don't preserve backwards compatibility.

## Trigger

Use when asked to "modernize" a Python package, or when a package uses `setup.py`, old-style docstrings, or lacks type hints.

## Input

The user provides a path to a Python package repo to modernize. The package should have a `setup.py` or `setup.cfg` based build.

## Python Version Target

**Supported range: Python 3.10 through 3.13.**

This affects three places — keep them consistent:
- `pyproject.toml` `requires-python`: `">=3.10"`
- `pyproject.toml` classifiers: list every minor version (3.10, 3.11, 3.12, 3.13)
- CI/CD test matrix: test only the **floor and ceiling** — `["3.10", "3.13"]`

## Process

Work through these phases in order. Commit after each phase.

### Phase 1: Packaging — Migrate to `pyproject.toml`

**Delete these files entirely:**
- `setup.py`
- `setup.cfg`
- `MANIFEST.in`
- `requirements/` directory (all files inside)

**Create `pyproject.toml`** with this structure (adapt values from the old `setup.py`):

```toml
[project]
name = "PACKAGE_NAME"
version = "X.Y.Z"
description = "..."
readme = "README.md"
license = "BSD-2-Clause"
requires-python = ">=3.10"
authors = [
    { name = "Author Name" },
]
keywords = ["..."]
classifiers = [
    "Development Status :: 4 - Beta",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]
dependencies = [
    # Move from setup.py install_requires or requirements.txt
]

[project.urls]
Homepage = "https://..."

[project.scripts]
# Move console_scripts entry_points here
# command-name = "package.module:function"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.optional-dependencies]
test = [
    "pytest",
]

[tool.pytest.ini_options]
addopts = "-rfE"
testpaths = ["tests"]

[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I"]
ignore = ["F403", "F405", "E501"]

[tool.ruff.lint.isort]
known-first-party = ["PACKAGE_NAME"]
```

**Delete `_version.py`** entirely. The single source of truth for version is `pyproject.toml`.

- Remove any `from ._version import __version__` lines from `__init__.py` and other modules.
- Where a version string is needed at runtime (e.g. a debug log or CLI `--version`), use `importlib.metadata` inline:
  ```python
  from importlib.metadata import version
  _LOGGER.debug(f"Using package version {version('PACKAGE_NAME')}")
  ```
- Do NOT wrap in try/except — if the package isn't installed, the import itself fails first.

### Phase 2: Pre-commit — Switch to Ruff

**Replace `.pre-commit-config.yaml`** contents with:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: check-yaml
      - id: end-of-file-fixer
      - id: check-ast

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

Remove any Black, isort, or flake8 references from pre-commit config.

### Phase 3: CI/CD — Update GitHub Actions

**Lint workflow** (`.github/workflows/black.yml` or similar — keep the filename):

```yaml
name: Lint

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .
```

**Test workflow** (`.github/workflows/run-pytest.yml` or similar):

```yaml
name: Run pytests

on:
  push:
    branches: [master, dev]
  pull_request:
    branches: [master]

jobs:
  pytest:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        python-version: ["3.10", "3.13"]
        os: [ubuntu-latest, macos-latest]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install package with test dependencies
      run: python -m pip install ".[test]"

    - name: Run pytest tests
      run: pytest tests
```

Key changes in test workflows:
- Remove any `pip install -r requirements/requirements-*.txt` lines
- Replace with `pip install ".[test]"` (dependencies come from pyproject.toml now)
- Update Python version matrix to `["3.10", "3.13"]`
- Update actions to `checkout@v4`, `setup-python@v5`

**Publish workflow** (`.github/workflows/python-publish.yml`):

```yaml
name: Upload Python Package

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    name: upload release to PyPI
    permissions:
      contents: read
      id-token: write

    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.x'
    - name: Install build dependencies
      run: python -m pip install --upgrade pip build
    - name: Build package
      run: python -m build
    - name: Publish package distributions to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
```

Key changes:
- Use `python -m build` instead of `python setup.py sdist bdist_wheel`
- Use trusted PyPI publishing (`id-token: write` + `pypa/gh-action-pypi-publish`) instead of username/password/token
- Remove `twine` and `setuptools wheel` installs

**Build/install workflow** (if it exists):
- Update Python matrix to `["3.10", "3.13"]`
- Replace `pip install -r requirements/...` with `pip install .`
- Update action versions

### Phase 4: Python Code — Add Type Hints

**Do NOT add `from __future__ import annotations`.** With `requires-python = ">=3.10"`, all modern type syntax works natively at runtime:
- `str | None` union syntax (PEP 604) — native since Python 3.10
- `list[str]`, `dict[str, int]` lowercase generics (PEP 585) — native since Python 3.9
- The `__future__` import was planned to become default in 3.10 but was postponed indefinitely. It's unnecessary with a 3.10 floor and can cause issues with runtime annotation introspection (Pydantic, FastAPI, dataclasses).

For **every `.py` file** in the package (not tests):

1. Add type hints to all function/method signatures:
   - Parameters: `def func(name: str, count: int = 0, items: list[str] | None = None)`
   - Return types: `def func() -> str:`, `def func() -> None:`
   - Use modern syntax: `str | None` not `Optional[str]`, `list[str]` not `List[str]`, `dict[str, int]` not `Dict[str, int]`

2. Add type hints to module-level constants:
   ```python
   PKG_NAME: str = "mypackage"
   DEFAULT_PORT: int = 80
   ALL_VERSIONS: dict[str, str] = {"v1": "/api/v1"}
   SUPPORTED_TYPES: list[str] = ["fasta", "fastq"]
   ```

3. Replace deprecated imports:
   - `pkg_resources` -> `importlib.metadata`
   - Remove `from typing import Optional, List, Dict, Tuple` (use builtins)
   - Remove `from __future__ import annotations` if present
   - Keep `from typing import Any` if needed

### Phase 5: Docstrings — Convert to Google Style

Convert all docstrings from Sphinx/reST style to Google style.

**Module/class docstrings** — collapse short ones to single line with trailing period:
```python
# Before
"""
Package constants
"""

# After
"""Package constants."""
```

**Function/method docstrings** — use Google `Args:`/`Returns:`/`Raises:` format:
```python
# Before
def func(name, count=0):
    """
    Create the thing with a name.

    :param str name: the name to use
    :param int count: how many to create
    :return str: the created thing's ID
    :raise ValueError: if name is empty
    """

# After
def func(name: str, count: int = 0) -> str:
    """Create the thing with a name.

    Args:
        name: The name to use.
        count: How many to create.

    Returns:
        The created thing's ID.

    Raises:
        ValueError: If name is empty.
    """
```

Rules:
- Opening `"""` on same line as first sentence (no blank line after `"""`)
- Trailing period on all descriptions
- Don't repeat type info in docstring Args (it's in the signature now)
- `Args:` not `Arguments:` or `:param:`
- `Returns:` not `:return:` or `:returns:`
- `Raises:` not `:raise:` or `:raises:`
- One blank line before `Args:`, `Returns:`, `Raises:` sections
- Indent continuation lines under each arg by 4 spaces

### Phase 6: Cleanup

- Remove any `veracitools` references
- Remove ALL `__future__` imports (`annotations`, `print_function`, `division`, etc.)
- Remove Python 2 compatibility code
- Remove `# -*- coding: utf-8 -*-` lines
- Run `ruff check --fix .` and `ruff format .` on the entire codebase

## Commit Strategy

Make one commit per phase:
1. `modernize packaging to pyproject.toml`
2. `update pre-commit to ruff`
3. `update CI/CD for modern Python`
4. `add type hints`
5. `convert docstrings to Google style`
6. `cleanup`

Or consolidate into fewer commits if the package is small:
1. `modernize packaging to pyproject.toml`
2. `restyle docstrings`
3. `update CI/CD, modernize`
