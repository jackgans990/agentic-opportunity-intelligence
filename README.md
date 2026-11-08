# agentic-opportunity-intelligence

Evidence-driven intelligence, opportunity discovery, evaluation, monitoring, and execution framework for agentic and on-chain ecosystems.

This repository contains instructions, rules, and data formats for an AI research agent. It does not contain executable code.

## Where things are

| Path | Purpose |
|------|---------|
| `skills/agentic-opportunity-intelligence/SKILL.md` | Main mission, workflow, scoring and safety rules |
| `integrations/GROK_INSTRUCTIONS.md` | Instructions specific to the Grok agent, including untrusted-content rules |
| `integrations/grok_output.schema.json` | Format of research findings |
| `integrations/mint_request.schema.json` | Format of the handoff from research to execution |
| `config/execution_policy.yaml` | What may be executed automatically, plus gas and daily limits, `emergency_stop` |
| `config/scoring.yaml` | Score weights, rating rubric, qualification thresholds, execution gate |
| `config/chains.yaml`, `config/monitoring.yaml` | Supported chains and watchlist/reassessment rules |
| `discovery/` | Search keywords, queries, and excluded terms |
| `database/` | Record formats for projects, evidence, and watchlist |
| `sources/raw/` | Seed data. initial_wallets.csv is immutable; the other files are append-only working files. |

## Workflow

search -> filter -> evaluate -> (free mint) simulate and execute within limits -> report -> watchlist/monitor

Paid mints are recommendations only. Selling assets always requires explicit owner approval.

## Emergency stop

Set `global.emergency_stop: true` in `config/execution_policy.yaml` to halt all automatic execution.
