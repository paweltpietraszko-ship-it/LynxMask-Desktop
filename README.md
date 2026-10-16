# LynxMask Desktop

**Python / FastAPI / Tauri implementation of the LynxMask privacy product.**

LynxMask is one product with two independent platform implementations:

- **Mobile:** https://github.com/paweltpietraszko-ship-it/LynxMask — Android / Kotlin
- **Desktop:** this repository — Python / FastAPI / Tauri

The two codebases do not share implementation files, but they are expected to preserve the same product-level contracts for token format, entity taxonomy, self-learning behavior and dictionary exchange.

This repository is included in my AI evaluation portfolio as evidence of hands-on system evaluation, adversarial testing, privacy failure analysis and human-in-the-loop control. It is not presented as evidence that I am a software engineer or ML engineer.

## My role

My role has been to define product behavior, decide which failures matter, set acceptance targets, challenge AI-generated implementations and retain final product and architecture decisions. AI coding agents, especially Claude Code, were used heavily to inspect, implement and revise the codebase.

A recurring working rule is deliberately narrow:

1. Read the actual file first.
2. Diagnose before modifying.
3. Make one bounded change.
4. Run the relevant test or benchmark.
5. Commit only after evidence.

When the coding agent expands scope, the instruction is to stop and return to the exact task.

## Evaluation focus

The Desktop implementation exposes a different set of privacy and reliability problems from Mobile, including:

- NER recall
- false positives
- critical leakage
- token injection
- mixed-document behavior
- guardrail coverage
- deterministic output checks
- security regressions
- execution-path consistency

The key lesson is that a masked document can look plausible while still leaking sensitive data or violating deterministic guarantees.

## Examples of evaluation-driven iteration

The development record includes cases where:

- recall for selected entity classes was extremely low despite apparently successful output
- aggressive entity detection created large false-positive groups
- a token-injection fix introduced an idempotency regression and had to be rolled back
- mixed documents could skip parts of the masking path
- a security function existed in code but was not called in the active path
- guard behavior differed between execution paths

These cases pushed the project toward measurable acceptance criteria, regression checks and deterministic controls rather than relying on model explanations or visual inspection.

## Shared contracts with Mobile

Several decisions are product-level contracts and must not drift independently:

- token format
- `TOKEN_RE` compatibility
- self-learning behavior
- `.lynxdict` exchange
- shared entity taxonomy
- selected user-visible behavior

A local PASS on each platform is not enough if the shared contract diverges.

## What this project demonstrates

- privacy and safety evaluation
- failure-mode analysis
- false-positive / false-negative tradeoffs
- regression testing
- adversarial edge cases
- deterministic guardrails around probabilistic components
- coding-agent task scoping
- execution-path verification
- human-in-the-loop adjudication
- cross-platform contract governance

See [`docs/FAILURE_LOG.md`](docs/FAILURE_LOG.md) for selected failure cases.

## Project status

LynxMask Desktop is an experimental, actively iterated project. It is included here because the repository contains real evidence of repeated evaluation, falsification, measurement and model-control work rather than a claim of commercial ML engineering experience.
