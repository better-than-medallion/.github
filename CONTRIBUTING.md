# Contributing

These rules apply to every repository of the organization unless the repository says otherwise.

## Workflow

1. Open or pick an issue first. Research ideas use the "Research idea" form, defects the "Bug" form.
2. Branch from `main` with a short prefix: `feat/`, `fix/`, `research/`, `chore/`.
3. Write commit messages and pull request titles in the [Conventional Commits](https://www.conventionalcommits.org/) style: `feat: add order book snapshot loader`.
4. Open a pull request early as a draft and fill in the template.
5. One approval from another member is required before merging. The author merges.

## Code

- **Hot path (Rust or C++):** no allocation or blocking call in the event loop, benchmarks for anything latency-sensitive, `cargo clippy` / `clang-tidy` clean.
- **Research (Python):** notebooks are for exploration. Anything a decision relies on moves into a tested module.
- **Supervision (TypeScript):** strict mode, no `any` without a comment saying why.
- Tests come with the change. A bug fix starts with a failing test.

## Research hygiene

- State the hypothesis before running the backtest, and write it in the issue.
- Keep an untouched out-of-sample period. Looking at it twice turns it into in-sample data.
- Include fees, slippage and funding in every result. A result without costs is not a result.
- Label every figure as backtest, paper or live.

## Secrets

Never commit API keys, account identifiers or exchange credentials, not even in a test or a notebook output. Use environment variables or the secret store described in the repository. If a secret leaks, follow [SECURITY.md](SECURITY.md) immediately.
