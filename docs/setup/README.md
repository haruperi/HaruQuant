 ## Setup

 1. .pre-commit-config.yaml - Main pre-commit configuration with:
    - General file checks: trailing whitespace, end-of-file, large files, private keys
    - Black (v24.10.0): Code formatting
    - isort (v5.13.2): Import sorting with black-compatible profile
    - flake8 (v7.1.1): Linting with additional plugins (docstrings, bugbear, comprehensions, simplify)
    - bandit (v1.8.0): Security vulnerability scanning
    - mypy (v1.13.0): Type checking
  2. pyproject.toml - Centralized configuration for:
    - Black: 88 character line length, Python 3.9+ target
    - isort: Black-compatible profile, same line length
    - mypy: Configured with reasonable strictness, ignores missing imports for MetaTrader5
    - bandit: Excludes test directories, skips assert checks in tests
    - pylint: Same line length, disabled overly strict rules for trading code
    - pytest: Coverage and test discovery settings
  3. .flake8 - Flake8 configuration:
    - 88 character line length (matching black)
    - Ignores conflicts with black (E203, W503, E501)
    - Max complexity of 10
    - Allows unused imports in __init__.py

  Key Features (No Conflicts)

  - Consistent line length: All tools use 88 characters
  - Black-compatible isort: Using --profile black to prevent import conflicts
  - Coordinated ignores: flake8 ignores rules that conflict with black
  - Appropriate for trading: Allows common trading variable names (df, mt5, id)
  - Security-focused: Bandit checks for vulnerabilities, detects private keys
  - Type safety: mypy configured with good strictness balance

  The hooks will now run automatically on every commit. You can also run them manually with:
  - pre-commit run --all-files - Run on all files
  - pre-commit run --files <file> - Run on specific files
