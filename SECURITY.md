# Security

## Reporting a problem

Do not open a public issue for a security problem. Members report it in the private team channel and tag the repository owner. Anyone else can use GitHub's private vulnerability reporting on the repository concerned, if enabled, or contact an organization owner.

## If a key or credential leaks

1. Revoke the key on the venue or service at once, before anything else.
2. Check the venue for orders, withdrawals or transfers you did not make.
3. Remove the secret from the code and rotate it. Deleting the commit is not enough: the key stays in the history and in forks.
4. Write a short incident note: what leaked, for how long, what was done.

## Key rules

- Exchange and broker keys are **trade-only**: never enable withdrawals on a key used by code.
- Restrict keys to known IP addresses whenever the venue allows it.
- One key per bot and per environment (paper, live), so one can be revoked without stopping the others.
