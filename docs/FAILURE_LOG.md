# LynxMask Desktop — evaluation failure log

This file selects failure cases that are useful as evidence of AI-assisted system evaluation. It is not a complete bug database.

## Low recall hidden behind plausible output

Observed behavior: the pipeline could produce apparently successful masked documents while benchmark recall for some entity classes remained very poor.

Documented examples included very low recall for NUMER, TELEFON and EMAIL and a high Critical Leakage rate.

Evaluation lesson: visual plausibility is not safety evidence.

## False positives from aggressive entity detection

Observed behavior: organization/person detection could merge several organizations into one token, classify uppercase headings as people or classify technical acronyms as organizations.

Evaluation lesson: track false positives separately from recall. Privacy systems can fail in both directions.

## Token injection through internal placeholder format

Observed behavior: a user-entered value shaped like an internal token could interact with the pseudonymization map in unintended ways.

Evaluation lesson: machine-significant placeholder formats require adversarial testing.

## Security fix introduced a regression

Observed behavior: an attempted token-injection fix broke idempotent behavior and had to be reverted.

Evaluation lesson: AI-generated fixes remain hypotheses until regression checks pass.

## Mixed documents bypassed protection

Observed behavior: documents already containing existing tokens could skip parts of the masking path, leaving sensitive values unmasked.

Evaluation lesson: edge cases should include pipeline state, not only clean examples.

## Security function existed but was not active

Observed behavior: a checking function existed in code but was not called in the active execution path.

Evaluation lesson: evaluate runtime enforcement, not implementation intent.

## Guard behavior differed across paths

Observed behavior: one path could persist data without applying the same guard-blocked check used elsewhere.

Evaluation lesson: safety behavior must be consistent across execution paths.

## Coding agent could expand scope or trust stale documentation

Observed pattern: AI coding agents could move beyond the requested change or work from outdated documentation instead of current code.

Response: the workflow was narrowed to read-first, diagnose-first, one bounded change, test, then commit.

Evaluation lesson: agent reliability depends partly on task design and explicit stop conditions.

## Shared contract risk with Mobile

Risk: Desktop and Mobile maintain separate codebases but depend on compatible token formats, taxonomy and dictionary behavior.

Evaluation lesson: local correctness does not guarantee product-level correctness.

## Human ownership of ambiguous decisions

The project documentation explicitly reserves selected architecture and product decisions for the human owner rather than the coding agent.

Evaluation lesson: human-in-the-loop means retaining decision authority where the specification is ambiguous.
