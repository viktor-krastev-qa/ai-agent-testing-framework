# AI Agent Testing Framework

An offline QA portfolio project for testing agent tool orchestration. It checks tool selection, exact arguments, call order, authorization, confirmation, bounded retries, step limits and in-memory idempotency.

**The agent is scripted, not an LLM.** Tools operate only in memory. No API keys, network requests, real orders or money are involved. This project validates an execution harness and trace evaluator; it does not establish real-model planning quality.

## Validation

- 50 pytest tests passed in the build environment (Python 3.12, pytest 9.1.1).
- Good scripted plans: 15 PASS.
- Deliberately bad plans: 15 FAIL, expected exit code 1.
- Validated locally on Windows with Python 3.13: 50 tests passed.
- Local evaluation: good plans — 15 PASS; bad plans — 15 FAIL, 0 ERROR.
- GitHub Actions validation is pending.

## Quick start (Windows / Cursor)
Requires Python 3.13 and Git.
```powershell
git clone https://github.com/viktor-krastev-qa/ai-agent-testing-framework.git
cd ai-agent-testing-framework
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -v
python -m agent_testing.runner --output reports/good
Start-Process reports/good/report.html
```
If you already cloned the repository, start with creating/activating `.venv`.

## Deliberately incorrect plans
```powershell
python -m agent_testing.runner --plans data/plans_bad.json --output reports/bad
Start-Process reports/bad/report.html
```
Expected: 15 FAIL and exit code 1. Good plans produce 15 PASS. Unit tests assert both correct behavior and detection of incorrect plans; they should all pass. Exit code 2 indicates invalid setup. Unexpected internal errors are reported separately as ERROR.

## What is tested
| Risk | Example |
|---|---|
| Wrong tool / arguments | Tracking selects get_order with exact order_id |
| Missing input | Script asks for the order ID; no tool call |
| Extra fields / invalid ID | Tool schema rejects the request |
| Unauthorized access | Order outside trusted context is blocked |
| Unconfirmed write | Refund request without confirmation is blocked |
| Temporary failure | One retry then successful tool result |
| Persistent failure | Retry budget exhausted |
| Infinite execution | Agent stops at max_steps |
| Duplicate write | One simulated refund effect for repeated order |
| Wrong sequence | Order lookup precedes policy lookup |
| Injection attempt | Unauthorized refund blocked by execution guard |

A blocked attack is an expected success for the test harness. A FAIL means the resulting trace disagrees with that case's expectations. A wrong-tool plan may execute safely yet still fail its task-specific evaluation.

## Architecture
- `data/cases.json`: prompts, trusted test context and exact trace expectations.
- `data/plans_good.json`, `plans_bad.json`: scripted proposed actions.
- `agent_testing/engine.py`: replaceable provider, agent loop, retry and step budgets.
- `agent_testing/tools.py`: allowlist, schema checks, access checks and simulated tool effects.
- `agent_testing/evaluation.py`: expected vs actual trace checks.
- `agent_testing/runner.py`: command line and HTML/JSON reports.
- `tests/`: scenario, guard, retry, evaluator and reporting tests.
- `examples/`: [good HTML](examples/good/report.html), [bad HTML](examples/bad/report.html), [bad JSON](examples/bad/report.json). Download HTML and open locally.
- `docs/`: design notes and Bulgarian learning guide.

## Scope and limitations
The script does not understand the prompt or tool observations. Plans and expected outcomes were authored together; they are not held-out evidence of model performance. The missing-input case verifies no calls and completion, not the semantic correctness of the final clarification. Final-answer correctness is outside this evaluator's scope.

Authorization and confirmation are supplied by trusted scenario context, never read from the agent's tool arguments. The injection scenario tests an execution guard, not model resistance to prompt injection. The simulated refund tool accepts authorized, confirmed requests; it does not implement real refund eligibility rules.

Retries count additional attempts (max_retries=1 means at most two executions per action). Only transient errors are retried. max_steps caps agent decisions, with up to max_steps * (max_retries + 1) tool attempts. Tools return immediately: there is no real network timeout, cancellation or retry backoff in this offline sandbox.

Idempotency applies only to one in-memory run and order ID. It is not durable, concurrent or a solution for ambiguous remote payment outcomes. Real tool integrations would need durable idempotency keys and independent access checks.

A future LLM provider can implement `agent_for(case)` and return an object with `next_action(observation)`. It must validate API outputs and apply the same execution controls. No live adapter is claimed or included in this version.

## License
MIT — see [LICENSE](LICENSE).
