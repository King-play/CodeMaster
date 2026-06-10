# Security Policy

## Reporting a Vulnerability

Please do not open public issues for vulnerabilities. Email the maintainers or use GitHub private vulnerability reporting if it is enabled for the repository.

Include:

- Affected version or commit
- Steps to reproduce
- Impact
- Any suggested mitigation

## Supported Versions

CodeMate is currently pre-1.0. Security fixes are applied to the `main` branch.

## Important Notes

CodeMate may process source code and model prompts. Treat submitted code as sensitive. Production deployments should replace demo credentials, rotate `SECRET_KEY`, configure HTTPS, add rate limiting, use secure key management, and define deployment-specific logging and code-retention rules.
