# Recommended GitHub settings

Apply these settings after creating the public repository.

## General

- Enable Issues and Discussions.
- Use squash merging and automatically delete merged branches.
- Add the topics `apple-home`, `homebridge`, `homekit`, `simplisafe` and
  `self-hosted`.
- Do not enable a public wiki; keep versioned documentation under `docs/`.

## Main branch protection

- Require a pull request and at least one approving review.
- Dismiss stale approvals when new commits are pushed.
- Require conversation resolution.
- Require the `python`, `docker` and `CodeQL` status checks.
- Require branches to be up to date before merge.
- Block force pushes and branch deletion.
- Apply the rule to administrators where practical.

## Security

- Enable private vulnerability reporting.
- Enable Dependabot alerts, security updates and grouped version updates.
- Enable secret scanning and push protection.
- Enable dependency review for pull requests.
- Review the Actions permission granted to every new workflow.

Do not add real SimpliSafe credentials as repository or Actions secrets. The CI
suite is intentionally hardware-free and uses mocks.

