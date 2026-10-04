import json
import pytest
from agent_testing.engine import ScriptedAgent, run_agent
from agent_testing.tools import SimulatedTools, ToolError
from agent_testing.runner import ROOT, load_cases, run_suite, write_reports
from agent_testing.evaluation import evaluate_trace


def tool(name="get_order", args=None):
    return {"type": "tool", "name": name, "arguments": {"order_id": "ORD-001"} if args is None else args}


@pytest.mark.parametrize("args", [None, [], {}, {"order_id": 1}, {"order_id":"ORD-1"}, {"order_id":"ORD-001", "extra":1}])
def test_invalid_arguments_are_blocked(args):
    tools = SimulatedTools(["ORD-001"])
    with pytest.raises(ToolError):
        tools.execute("get_order", args)


def test_blocked_refund_has_no_effect():
    tools = SimulatedTools(["ORD-001"])
    trace = run_agent(ScriptedAgent([tool("request_refund")]), tools)
    assert trace[-1]["status"] == "blocked"
    assert tools.effect_count == 0


def test_unauthorized_refund_even_when_confirmed():
    tools = SimulatedTools(["ORD-001"], confirmed=True)
    with pytest.raises(ToolError, match="unauthorized"):
        tools.execute("request_refund", {"order_id":"ORD-999"})
    assert tools.effect_count == 0


def test_no_retry_for_invalid_request():
    trace = run_agent(ScriptedAgent([tool(args={})]), SimulatedTools(["ORD-001"]), max_retries=4)
    assert len([e for e in trace if e["type"] == "tool"]) == 1


def test_retry_then_refund_only_one_effect():
    tools = SimulatedTools(["ORD-001"], confirmed=True, failures={"request_refund":1})
    trace = run_agent(ScriptedAgent([tool("request_refund")]), tools)
    assert [e["status"] for e in trace] == ["temporary_unavailable", "ok", "completed"]
    assert tools.effect_count == 1


def test_duplicate_refund_result_is_explicit():
    tools = SimulatedTools(["ORD-001"], confirmed=True)
    tools.execute("request_refund", {"order_id":"ORD-001"})
    assert tools.execute("request_refund", {"order_id":"ORD-001"})["refund"] == "already_requested"
    assert tools.effect_count == 1


@pytest.mark.parametrize("action", [None, {"type":"unknown"}, {"type":"final", "text":""}])
def test_malformed_action_terminates(action):
    trace = run_agent(ScriptedAgent([action]), SimulatedTools([]))
    assert trace[-1]["status"] == "invalid_action"


@pytest.mark.parametrize("steps,retries", [(0,1),(1,-1)])
def test_invalid_limits_rejected(steps, retries):
    with pytest.raises(ValueError):
        run_agent(ScriptedAgent([]), SimulatedTools([]), steps, retries)


def test_exception_is_execution_error_not_fail():
    class Broken:
        def agent_for(self, case):
            raise RuntimeError("private token")
    report = run_suite(load_cases(ROOT / "data/cases.json")[:1], Broken())
    assert report["summary"]["error"] == 1
    assert "private token" not in json.dumps(report)


def test_trace_evaluator_detects_wrong_order():
    cases = load_cases(ROOT / "data/cases.json")
    case = cases[12]
    trace = run_agent(ScriptedAgent([tool("get_policy", {}),tool()]), SimulatedTools(["ORD-001"]))
    assert evaluate_trace(case, trace, 0)[0]["passed"] is False


def test_report_html_is_escaped(tmp_path):
    class Provider:
        def agent_for(self, case):
            return ScriptedAgent([{"type":"final","text":"<script>alert(1)</script>"}])
    report = run_suite(load_cases(ROOT / "data/cases.json")[:1], Provider())
    write_reports(report,tmp_path)
    page = (tmp_path / "report.html").read_text()
    assert "<script>" not in page
    assert "&lt;script&gt;" in page
    assert json.loads((tmp_path / "report.json").read_text())["summary"]["total"] == 1


def test_duplicate_case_ids(tmp_path):
    case = load_cases(ROOT / "data/cases.json")[0]
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([case,case]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_cases(path)
