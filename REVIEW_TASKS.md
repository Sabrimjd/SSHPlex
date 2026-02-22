# Code Review PR Tasks - SSHPlex

## Executive Summary
- Codebase: 6,137 LOC across 24 Python files
- Overall quality: Good with significant room for improvement

## Critical Issues (P0) - Must Fix

### 1. Security: SSH Command Injection Vulnerability
**File**: `sshplex_connector.py` - `_build_ssh_command()`
**Issue**: SSH command construction uses string concatenation which is vulnerable to injection if hostname contains special characters.

### 2. Security: SSL Verification Default
**File**: `config.py` - `NetBoxConfig`
**Issue**: `verify_ssl` defaults to `True` which is good, but `ConsulConfig` has `verify: False` as default - insecure.

### 3. Security: Credential Logging
**File**: Multiple files
**Issue**: Error messages may expose tokens/credentials in logs.

## High Priority (P1) - Should Fix

### 4. Code Quality: Replace `Any` with Proper Types
**Files**: `main.py`, `cli.py`, `config.py`, `sshplex_connector.py`
**Issue**: Extensive use of `Any` type hints reduces type safety.

### 5. Architecture: SoTFactory Code Duplication
**File**: `sot/factory.py`
**Issue**: `get_all_hosts()` and `get_all_hosts_parallel()` have significant code duplication.

### 6. Security: SSH Host Key Checking
**File**: `sshplex_connector.py`
**Issue**: `StrictHostKeyChecking=accept-new` is acceptable but should be more configurable.

### 7. Testing: Missing Edge Case Tests
**File**: Multiple test files
**Issue**: No tests for cache expiration, connection failures, error paths.

## Medium Priority (P2) - Nice to Have

### 8. Documentation: Missing docstring tests
**File**: All modules
**Issue**: Docstrings exist but no examples showing usage.

### 9. Performance: Consistent Naming
**File**: Various
**Issue**: Some functions use `get_*` pattern inconsistently.

### 10. Code Style: Missing type hints on some functions
**File**: Various
**Issue**: Some functions lack return type annotations.

## Action Plan
1. Fix security vulnerabilities (P0)
2. Replace `Any` types with proper types (P1)
3. Refactor SoTFactory to remove duplication (P1)
4. Add edge case tests (P1)
5. Add docstring examples (P2)
6. Fix minor style issues (P2)
