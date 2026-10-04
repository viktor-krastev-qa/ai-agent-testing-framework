import json
from pathlib import Path
from agent_testing.tools import ToolError, TransientError


class ScriptedAgent:
    """Replays proposed actions, including intentionally bad decisions."""
    def __init__(self, actions):
        self.actions = list(actions)
        self.index = 0

    def next_action(self, observation):
        # Script deliberately does not reason about observation or prompt.
        if self.index >= len(self.actions):
            return {"type": "final", "text": "Completed."}
        action = self.actions[self.index]
        self.index += 1
        return action


class FixtureProvider:
    def __init__(self, path):
        self.plans = json.loads(Path(path).read_text(encoding="utf-8"))

    def agent_for(self, case):
        return ScriptedAgent(self.plans[case["id"]])


def run_agent(agent, tools, max_steps=5, max_retries=1):
    if max_steps < 1 or max_retries < 0:
        raise ValueError("Invalid execution limits")
    trace, observation = [], None
    for step in range(1, max_steps + 1):
        action = agent.next_action(observation)
        if not isinstance(action, dict):
            trace.append({"type": "final", "status": "invalid_action", "step": step})
            return trace
        if action.get("type") == "final":
            text = action.get("text")
            trace.append({"type": "final", "status": "completed" if isinstance(text, str) and text.strip() else "invalid_action",
                          "text": text if isinstance(text, str) else "", "step": step})
            return trace
        if action.get("type") != "tool":
            trace.append({"type": "final", "status": "invalid_action", "step": step})
            return trace
        name, arguments = action.get("name"), action.get("arguments")
        for attempt in range(1, max_retries + 2):
            event = {"type": "tool", "step": step, "attempt": attempt, "name": name, "arguments": arguments}
            try:
                observation = tools.execute(name, arguments)
                trace.append({**event, "status": "ok", "result": observation})
                break
            except TransientError:
                observation = {"error": "temporary_unavailable"}
                trace.append({**event, "status": "temporary_unavailable"})
                if attempt == max_retries + 1:
                    trace.append({"type": "final", "status": "retry_exhausted", "step": step})
                    return trace
            except ToolError as exc:
                trace.append({**event, "status": str(exc)})
                trace.append({"type": "final", "status": "blocked", "step": step})
                return trace
    trace.append({"type": "final", "status": "step_limit", "step": max_steps})
    return trace
