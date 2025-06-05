# SSHplex Packaging and Release Guide

This guide explains how to package, distribute, and release SSHplex.

## 📦 Package Structure

SSHplex is now properly structured as a Python package:

```
sshplex/
├── pyproject.toml          # Modern Python packaging configuration
├── MANIFEST.in             # Additional files to include in distribution
├── sshplex/                # Main package directory
│   ├── __init__.py         # Package initialization and version
│   ├── cli.py              # Main CLI entry point
│   ├── sshplex_connector.py # SSH connection manager
│   ├── config-template.yaml # Default configuration template
│   ├── config-custom.yaml  # Custom configuration example
│   └── lib/                # Core library modules
│       ├── config.py       # Configuration management
│       ├── logger.py       # Logging setup
│       ├── multiplexer/    # Terminal multiplexer integrations
│       ├── sot/            # Source of Truth integrations
│       ├── ssh/            # SSH connection management
│       └── ui/             # User interface components
├── scripts/                # Development and release scripts
│   ├── setup-dev.sh        # Development environment setup
│   └── release.sh          # Release automation script
└── .github/workflows/      # GitHub Actions CI/CD
    ├── ci.yml              # Continuous Integration
    └── release.yml         # Automated releases
```

## 🚀 Installation Methods

### 1. From PyPI (End Users)

Once published to PyPI, users can install with:

```bash
pip install sshplex
```

Then run with:

```bash
sshplex
# or
sshplex --help
# or
sshplex --no-tui  # CLI mode
```

### 2. From Source (Development)

```bash
git clone https://github.com/yourusername/sshplex.git
cd sshplex
./scripts/setup-dev.sh
```

### 3. Editable Install (Development)

```bash
pip install -e .
```

## 🔧 Development Workflow

### Setting Up Development Environment

1. Clone the repository
2. Run the setup script: `./scripts/setup-dev.sh`
3. Activate the virtual environment: `source venv/bin/activate`

### Making Changes

1. Make your changes to the code
2. Run tests: `pytest tests/`
3. Test the CLI: `sshplex --help`
4. Test import: `python -c "from sshplex.cli import main; print('OK')"`

### Testing the Package

```bash
# Test building
python -m build

# Test installation from local build
pip install dist/sshplex-*.whl

# Test the installed package
sshplex --version
```

## 📋 Release Process

### Automated Release (Recommended)

1. **Prepare the release:**
   ```bash
   ./scripts/release.sh 1.0.1
   ```
   This script will:
   - Update version numbers in all relevant files
   - Run tests
   - Build the package
   - Commit changes and create a git tag
   - Push to GitHub

2. **Create GitHub Release:**
   - Go to GitHub repository > Releases
   - Click "Create a new release"
   - Select the tag created by the script (e.g., `v1.0.1`)
   - Add release notes describing changes
   - Publish the release

3. **Automatic PyPI Publishing:**
   - GitHub Actions will automatically detect the new release
   - Run tests across multiple Python versions
   - Build the package
   - Publish to PyPI using the `PYPI_API_TOKEN` secret

### Manual Release

If you prefer manual control:

```bash
# 1. Update version numbers manually
# 2. Build the package
python -m build

# 3. Check the package
twine check dist/*

# 4. Upload to PyPI
twine upload dist/*
```

## 🔑 PyPI Setup

### 1. Create PyPI Account

1. Register at [PyPI](https://pypi.org/account/register/)
2. Enable 2FA for security

### 2. Create API Token

1. Go to Account Settings > API tokens
2. Create a new token with "Entire account" scope
3. Copy the token (starts with `pypi-`)

### 3. Configure GitHub Secret

1. Go to your GitHub repository
2. Settings > Secrets and variables > Actions
3. Create a new secret named `PYPI_API_TOKEN`
4. Paste your PyPI API token as the value

## 🏷️ Version Management

Version numbers are managed in three places:
- `pyproject.toml` (main version)
- `sshplex/__init__.py` (package version)
- `sshplex/cli.py` (CLI version display)

The release script automatically updates all three locations.

### Version Format

Use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., `1.0.0`)
- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes (backward compatible)

## 🔍 GitHub Actions Workflows

### Continuous Integration (`ci.yml`)

Runs on every push and pull request:
- Tests across Python 3.8-3.12
- Linting with flake8
- Type checking with mypy
- Code coverage reporting

### Release Workflow (`release.yml`)

Runs when a GitHub release is published:
- Runs all CI checks
- Builds the package
- Publishes to PyPI automatically

## 📝 Package Metadata

Key information in `pyproject.toml`:
- **Entry point**: `sshplex = "sshplex.cli:main"`
- **Dependencies**: Listed in `dependencies` array
- **Optional dependencies**: Development tools in `[project.optional-dependencies]`
- **Classifiers**: Help users find your package
- **Python versions**: Specify supported versions

## 🚨 Important Notes

### Before First Release

1. **Update URLs**: Replace `yourusername` in `pyproject.toml` with your actual GitHub username
2. **Update author info**: Replace placeholder author and email
3. **Configure PyPI token**: Set up the `PYPI_API_TOKEN` secret in GitHub
4. **Test locally**: Ensure `pip install -e .` works correctly

### Security Considerations

- Never commit API tokens to the repository
- Use GitHub Secrets for sensitive information
- Enable 2FA on PyPI account
- Regularly rotate API tokens

### Testing Releases

Consider using [TestPyPI](https://test.pypi.org/) for testing releases:

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Install from TestPyPI to test
pip install --index-url https://test.pypi.org/simple/ sshplex
```

## 🎉 Success!

Once set up, your workflow will be:

1. Develop features/fixes
2. Run `./scripts/release.sh X.Y.Z`
3. Create GitHub release
4. Package automatically published to PyPI
5. Users can install with `pip install sshplex`

Your SSHplex application is now ready for distribution! 🚀
