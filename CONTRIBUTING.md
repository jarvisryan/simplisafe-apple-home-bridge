# Contributing

Thank you for contributing. By participating, you agree to follow
`CODE_OF_CONDUCT.md`.

## Before opening an issue

- Search existing issues and discussions.
- Reproduce against the latest release.
- Remove tokens, signed URLs, ICE credentials, account/location IDs, addresses,
  camera serials, images and other personal data from logs.
- Use GitHub's private vulnerability reporting for security issues.

## Pull requests

1. Create a focused branch and include tests for behavioural changes.
2. Run `ruff check .`, `mypy` and `pytest`.
3. Update documentation and `CHANGELOG.md` for user-visible changes.
4. Use Conventional Commit-style subjects where practical.
5. Confirm that no generated configuration, token, pairing data or backup has
   been committed.

At least one approving review and passing required checks are expected before
merge. New device support also requires a redacted hardware-test report.

