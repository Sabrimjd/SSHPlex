#!/bin/bash
# Release script for SSHplex

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if version is provided
if [ $# -eq 0 ]; then
    print_error "Please provide a version number (e.g., ./release.sh 1.0.1)"
    exit 1
fi

VERSION=$1

print_info "Preparing release for version $VERSION"

# Validate version format
if ! [[ $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    print_error "Version must be in format X.Y.Z (e.g., 1.0.1)"
    exit 1
fi

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    print_warning "You're not on the main branch. Current branch: $CURRENT_BRANCH"
    read -p "Do you want to continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    print_error "Working directory is not clean. Please commit or stash your changes."
    exit 1
fi

# Update version in pyproject.toml
print_info "Updating version in pyproject.toml"
sed -i '' "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Update version in __init__.py
print_info "Updating version in sshplex/__init__.py"
sed -i '' "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" sshplex/__init__.py

# Update version in cli.py
print_info "Updating version in CLI help"
sed -i '' "s/version='SSHplex .*'/version='SSHplex $VERSION'/" sshplex/cli.py

# Run tests
print_info "Running tests..."
if command -v pytest &> /dev/null; then
    python -m pytest tests/ -v
else
    print_warning "pytest not found, skipping tests"
fi

# Build the package
print_info "Building package..."
python -m pip install --upgrade build twine
python -m build

# Check the package
print_info "Checking package..."
twine check dist/*

# Commit changes
print_info "Committing version bump..."
git add pyproject.toml sshplex/__init__.py sshplex/cli.py
git commit -m "Bump version to $VERSION"

# Create and push tag
print_info "Creating and pushing tag v$VERSION..."
git tag "v$VERSION"
git push origin main
git push origin "v$VERSION"

print_info "Release preparation complete!"
print_info "The GitHub Actions workflow will automatically:"
print_info "  1. Run tests across multiple Python versions"
print_info "  2. Build the package"
print_info "  3. Publish to PyPI when you create a release on GitHub"
print_info ""
print_info "Next steps:"
print_info "  1. Go to https://github.com/yourusername/sshplex/releases"
print_info "  2. Create a new release using tag v$VERSION"
print_info "  3. Add release notes"
print_info "  4. Publish the release"
print_info ""
print_info "The package will be automatically published to PyPI!"
