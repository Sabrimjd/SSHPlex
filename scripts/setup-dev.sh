#!/bin/bash
# Development setup script for SSHplex

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info "Setting up SSHplex development environment..."

# Check if Python 3.8+ is available
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
major_version=$(echo $python_version | cut -d. -f1)
minor_version=$(echo $python_version | cut -d. -f2)

if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 8 ]); then
    print_warning "Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

print_info "Python version $python_version detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip

# Install package in development mode
print_info "Installing SSHplex in development mode..."
pip install -e .[dev]

# Install pre-commit hooks if available
if command -v pre-commit &> /dev/null; then
    print_info "Setting up pre-commit hooks..."
    pre-commit install
else
    print_warning "pre-commit not found, skipping hooks setup"
fi

print_info "Development environment setup complete!"
print_info ""
print_info "To activate the environment:"
print_info "  source venv/bin/activate"
print_info ""
print_info "To run SSHplex from source:"
print_info "  python -m sshplex.cli"
print_info "  or"
print_info "  sshplex"
print_info ""
print_info "To run tests:"
print_info "  pytest tests/"
print_info ""
print_info "To prepare a release:"
print_info "  ./scripts/release.sh <version>"
