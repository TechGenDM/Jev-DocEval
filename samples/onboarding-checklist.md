# Onboarding Checklist: New Engineer

Welcome. Complete these steps in your first two days. Ping `#eng-oncall`
if anything is blocked for more than an hour.

## Day 1

1. Accept the GitHub org invite (IT ticket already filed as ONB-####).
2. Install the company VPN and confirm you can reach `https://intranet.example`.
3. Clone `platform/dev-env` and run `make bootstrap`.
4. Join Slack channels: `#eng`, `#eng-oncall`, `#team-<your-team>`.

## Day 2

1. Pair with your buddy to ship a docs typo PR (any repo).
2. Read the [incident runbook](../runbooks/incidents.md) and note one
   question for your manager 1:1.
3. Set up local secrets with `sops` using the team AGE key from 1Password
   item "Eng AGE key".

## Done when

- [ ] `make test` passes in `platform/dev-env`
- [ ] You can open a staging deploy in Argo CD
- [ ] Your manager has confirmed access to the pager schedule

Owner: Engineering People Ops. Last updated: 2026-03-01.
