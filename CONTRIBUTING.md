# Contributing

Thanks for helping improve CodeMate.

## Local Setup

```bash
cp .env.example .env
npm install
npm run install:all
npm run dev
```

## Before Opening a Pull Request

Please run:

```bash
npm run test
npm run lint:web
npm run build:web
```

## Pull Request Expectations

- Keep changes focused.
- Add or update tests when behavior changes.
- Do not commit secrets, API keys, local databases, or generated build output.
- Explain user-visible behavior changes in the PR description.
- For AI behavior changes, include sample input and output.

## Code Style

- Backend code should prefer small service functions and Pydantic schemas for API boundaries.
- Frontend code should keep task workflow controls visible and keyboard-accessible.
- Use structured data instead of parsing free-form model text when possible.

