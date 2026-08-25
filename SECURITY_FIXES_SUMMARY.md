# Security Dependency Fixes Summary

## Overview
This document summarizes the security vulnerability fixes applied to the AIOps Agent project dependencies.

## Date
2025-01-XX

## Fixed Vulnerabilities

### 1. PyJWT (CVE-2024-53861, CVE-2024-33663)
- **Severity**: Medium
- **Issue**: Algorithm allow-list bypass when decoding with PyJWK/PyJWKClient keys, and incorrect string comparison in issuer field checking
- **Affected Versions**: <= 2.12.1
- **Fixed Version**: >= 2.13.0
- **Files Updated**:
  - `requirements.txt`: pyjwt[crypto]>=2.9.0 → pyjwt[crypto]>=2.13.0
  - `pyproject.toml`: pyjwt>=2.9.0 → pyjwt>=2.13.0

### 2. aiohttp (CVE-2024-52304, CVE-2025-69224, CVE-2025-53643)
- **Severity**: High
- **Issue**: Multiple HTTP request smuggling vulnerabilities due to incorrect parsing of chunk extensions, trailer sections, and Unicode header values
- **Affected Versions**: < 3.13.3
- **Fixed Version**: >= 3.13.3
- **Files Updated**:
  - `requirements.txt`: aiohttp>=3.10.0 → aiohttp>=3.13.3
  - `pyproject.toml`: aiohttp>=3.10.0 → aiohttp>=3.13.3

### 3. FastAPI (CVE-2024-24762)
- **Severity**: High
- **Issue**: Regular expression Denial of Service (ReDoS) via Content-Type header when using form data with python-multipart
- **Affected Versions**: < 0.109.1
- **Fixed Version**: >= 0.109.1
- **Files Updated**:
  - `requirements.txt`: fastapi>=0.104.0 → fastapi>=0.109.1
  - `pyproject.toml`: fastapi>=0.104.0 → fastapi>=0.109.1

### 4. Pillow (CVE-2025-48379)
- **Severity**: High
- **Issue**: Heap buffer overflow when writing large images in DDS format
- **Affected Versions**: >= 11.2.0, < 11.3.0
- **Fixed Version**: >= 11.3.0
- **Files Updated**:
  - `requirements.txt`: Pillow>=11.0.0 → Pillow>=11.3.0
  - `pyproject.toml`: Pillow>=11.0.0 → Pillow>=11.3.0

### 5. httpx (CVE-2025-43859 via h11)
- **Severity**: Medium
- **Issue**: HTTP request smuggling via h11 dependency (CVE-2025-43859)
- **Affected Versions**: < 0.27.2
- **Fixed Version**: >= 0.27.2
- **Files Updated**:
  - `requirements.txt`: httpx>=0.27.0 → httpx>=0.27.2 (both occurrences)
  - `pyproject.toml`: httpx>=0.27.0 → httpx>=0.27.2
  - `sdk/python/pyproject.toml`: httpx>=0.25.1 → httpx>=0.27.2

### 6. python-multipart (CVE-2024-24762, CVE-2024-53981)
- **Severity**: High
- **Issue**: ReDoS via Content-Type header and excessive logging DoS
- **Affected Versions**: < 0.0.18
- **Fixed Version**: >= 0.0.18
- **Files Updated**:
  - `requirements.txt`: python-multipart>=0.0.9 → python-multipart>=0.0.18
  - `pyproject.toml`: python-multipart>=0.0.9 → python-multipart>=0.0.18

### 7. Pydantic (ReDoS Vulnerability)
- **Severity**: Medium
- **Issue**: Regular expression denial of service via crafted email strings
- **Affected Versions**: < 2.4.0
- **Fixed Version**: >= 2.4.0
- **Files Updated**:
  - `requirements.txt`: pydantic>=2.0.0 → pydantic>=2.4.0 (both occurrences)
  - `pyproject.toml`: pydantic>=2.0.0 → pydantic>=2.4.0

### 8. sentence-transformers (RCE Vulnerability)
- **Severity**: High
- **Issue**: Arbitrary code execution when loading PyTorch model files without weights_only=True
- **Affected Versions**: < 3.1.0
- **Fixed Version**: >= 3.1.0
- **Files Updated**:
  - `requirements.txt`: sentence-transformers>=3.0.0 → sentence-transformers>=3.1.0
  - `pyproject.toml`: sentence-transformers>=3.0.0 → sentence-transformers>=3.1.0

## Dependencies Already Secure

The following dependencies were already at secure versions:
- **setuptools**: >=78.1.1 (fixes CVE-2024-6345, CVE-2025-47273)
- **cryptography**: >=43.0.0 (fixes CVE-2024-26130, CVE-2023-50782)
- **authlib**: >=1.3.1 (fixes CVE-2024-37568)
- **passlib**: >=1.7.4 (no known vulnerabilities in latest version)
- **hiredis**: >=3.0.0 (fixes CVE-2021-32765)
- **uvicorn**: >=0.24.0 (fixes CVE-2020-7694, CVE-2020-7695)

## Testing

A compatibility test script has been created at `test_dependency_compatibility.py` to verify that the updated dependencies work correctly with the project.

To run the test:
```bash
python test_dependency_compatibility.py
```

## Recommendations

1. **Update Dependencies**: Run the following to install the updated dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   ```

2. **Review Code**: Review any code that uses the updated APIs, especially:
   - PyJWT verification with PyJWK/PyJWKClient
   - FastAPI form data handling
   - Pillow image processing with DDS format
   - sentence-transformers model loading

3. **Monitor**: Continue monitoring security advisories for these packages and update as needed.

4. **Automate**: Consider setting up automated dependency scanning (e.g., Dependabot, Renovate) to catch future vulnerabilities early.

## References

- [PyJWT Security Advisory](https://github.com/jpadilla/pyjwt/security/advisories)
- [aiohttp Security Advisories](https://github.com/aio-libs/aiohttp/security/advisories)
- [FastAPI Security Advisory](https://github.com/tiangolo/fastapi/security/advisories)
- [Pillow Security Advisory](https://github.com/python-pillow/Pillow/security/advisories)
- [httpx Security](https://github.com/encode/httpx/security)
- [python-multipart Security Advisory](https://github.com/Kludex/python-multipart/security/advisories)
- [Pydantic Security](https://github.com/pydantic/pydantic/security)
- [sentence-transformers Security](https://security.snyk.io/vuln/SNYK-PYTHON-SENTENCETRANSFORMERS-8161344)

## Files Modified

1. `requirements.txt` - Updated 8 dependency versions
2. `pyproject.toml` - Updated 8 dependency versions
3. `sdk/python/pyproject.toml` - Updated 1 dependency version
4. `test_dependency_compatibility.py` - New compatibility test script (created)
5. `SECURITY_FIXES_SUMMARY.md` - This document (created)
