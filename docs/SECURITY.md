# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
|---------| ------------------ |
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in AIOps Agent, please report it responsibly:

1. **Do not** open a public issue.
2. Send an email to `security@example.com` with a detailed description.
3. Include steps to reproduce, affected versions, and any possible mitigations.
4. We will acknowledge receipt within 48 hours and provide a timeline for a fix.

## Security Best Practices

- Keep dependencies up to date (`pip install -r requirements.txt`).
- Run `bandit -r .` regularly to detect common Python security issues.
- Never commit secrets or credentials to the repository.
- Use environment variables for sensitive configuration (`DATABASE_URL`, `OPENAI_API_KEY`, etc.).
- Enable TLS in production and disable plain-text authentication.

## Disclosure Policy

We follow a 90-day disclosure policy. After a fix is released, we will publish a security advisory describing the issue and the fix.
