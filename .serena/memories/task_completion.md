# Task Completion Checklist
- Run `make lint`.
- Run `make typecheck`.
- Run `make unit`.
- If changing orchestration or evaluation flow, verify whether an end-to-end run or `python -m sim_eval.smoke_test` is also needed.
- Check `git status --short --branch` before finishing to avoid describing user-owned changes as your own.
- Be careful with baseline/candidate evaluation semantics in `agent_runner` and `sim_eval`, since current codebase is still a PoC and not all integration paths are validated by tests.