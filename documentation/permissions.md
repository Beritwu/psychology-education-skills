# Permissions and identity

There is one trusted local operator context. No login, tenant role claims, RLS,
or multi-user authorization layer is provided by the application. SQLite access
is controlled by the OS and application code. A project ID selects data; it is
not a security credential.

| Resource / operation | Who or what | Application boundary / rejection |
|---|---|---|
| Create/read/edit project | Local operator | Project/path validation; not user-based authorization |
| Accept changeset | Local operator | Conflicts, target revisions and preserved artifact locks |
| Declare a claim supported | Evidence workflow / actual human review | Locatable quote in stored source; no button-only approval |
| Submit teacher rating | Operator acting for a real teacher | Human/teacher labels and exact run/target binding; no identity verification |
| Write artifact | Runtime node | Declared emits/produces contract and immutable revisions |
| Invoke external skill | Approved, pinned, allowed skill | Restricted input context; denied when lifecycle checks fail |
| Execute candidate scripts | Verified sandbox adapter | Filesystem/network/memory controls required; no host fallback |
| Formal export | Local operator | Applicable current gates, non-fixture revisions, required review |
| Publish externally through PEBS | Not a supported course-build action | Permission layer denies out-of-scope side effects |

Publishing this source repository is a maintainer action outside the PEBS course
runtime. Exposing the local server publicly would require an independently
designed authentication and authorization deployment, not merely a different bind address.
