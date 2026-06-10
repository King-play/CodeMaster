# Open Source Checklist

Use this checklist before publishing CodeMate on GitHub.

## Repository

- README explains purpose, features, setup, and API overview.
- MIT license is present.
- CONTRIBUTING, CODE_OF_CONDUCT, and SECURITY files are present.
- Issue forms and PR template are present.
- CI runs backend tests, frontend lint, frontend build, and dependency audit.
- CodeQL and Dependabot are configured.
- Generated files, local databases, node_modules, build output, and secrets are ignored.

## Security

- Replace default local users before public deployment.
- Rotate `SECRET_KEY`.
- Keep `OPENAI_API_KEY` in deployment secrets only.
- Enable GitHub secret scanning and push protection in repository settings.
- Enable Dependabot alerts and security updates.
- Review code-retention policy before accepting private repositories.

## Release

- Tag releases with semantic versions, for example `v0.1.0`.
- Include migration notes when database schema changes.
- Publish Docker deployment notes with each release.

