# Security Policy

## Supported versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a vulnerability

If you discover a security issue in this project, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, send an email to the maintainer at the address listed in the repository contact with the following information:

- A description of the vulnerability.
- Steps to reproduce or a proof-of-concept.
- The affected version or commit.
- Suggested mitigation if known.

We aim to respond within 7 days and release a fix or mitigation within 30 days.

## Security best practices

- Never commit secrets, passwords or API tokens to the repository.
- Use environment variables or a secrets manager for configuration.
- Keep dependencies up to date and review security advisories regularly.
- Run `bandit` before submitting changes.

## Disclosure policy

Once a fix is released, we will disclose the issue in the [CHANGELOG](CHANGELOG.md) with appropriate credit to the reporter.
