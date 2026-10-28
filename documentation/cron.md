# Scheduled and background work

| Job | Trigger | External services / limits | Evidence and recovery |
|---|---|---|---|
| Live Research Benchmark | Mondays 03:00 UTC; manual dispatch | Real research APIs; provider timeouts apply | Actions logs and provider-status artifact; rerun after service recovery |
| Code CI | Push / PR | Dependency installation; renderer integration | Actions logs and test outcomes |
| Quality Benchmark smoke | Relevant PR / manual | Hermetic tests, no model calls | Benchmark smoke job |
| Full quality benchmark | Explicit manual dispatch | Configured model/research services; consumes quota | Run report artifacts; requires provider setup |
| Static demo deployment | Push to main / manual | GitHub Pages only | Pages workflow and deployment status |

These are repository CI workflows, not a scheduler inside PEBS. The application
does run user-requested builds in background execution threads; run IDs and
budgets identify them. Do not start overlapping writes to the same project from
independent processes. Artifact revision controls do not provide a distributed
job queue. Repeated external requests can consume additional quota.
