# Operational flows

## Build a course

Actor: trusted local operator. Precondition: provider configuration and sanitized
input. Success: inspectable candidate revisions and run/gate records.

1. UI/CLI → engine: validate project identity and request/material PII. Identifiable
   data must be blocked/excluded before the external prompt boundary.
2. Engine → planner: apply deterministic requirements and validate explicit skills
   against the registry and allowlist. Unapproved skills are denied.
3. Runtime → providers: apply input and execution budgets. External model/research
   calls spend provider quota and return data, not authority to change permissions.
4. Agent → Store: writes must satisfy the node's artifact contract. Out-of-contract
   writes fail; revisions remain immutable and fixture-tagged where applicable.
5. Local user → accept/reject: optimistic conflict checks and preservation locks
   protect revisions. Acceptance does not bypass formal export gates.

## Change a course

Actor: local operator; existing course required. Conversation intent resolves
targets and affected dependencies. Preserve clauses establish artifact locks.
Only the affected artifacts can change in that patch; stale dependencies require
new checks. Candidate changes remain subject to explicit accept/reject.

## Export and evaluate

Export reads the accepted target revisions. Formal export checks applicable current
gates, fixture isolation and review requirements. Drafts remain labeled.
Evaluation packages freeze target hashes and run identity. A real teacher's score
is submitted to the project/run it describes; missing, stale or mismatched targets
are rejected. Performance binding must use the generation-time skill identity.
These checks enforce record integrity, not the teacher's real-world identity.

## Install skills

Operator → downloader crosses the repository/network boundary. Prefix allowlist,
archive/path/symlink/size checks apply. Import never executes package files.
Approval/publishing/pinning controls runtime selection. Scripts may run only
through the verified sandbox adapter; failure does not allow a host fallback.

## Public example

GitHub Pages → static browser files only. Playback is local JavaScript, no network
model calls, cookies, analytics, credential handling or learner data submission.
