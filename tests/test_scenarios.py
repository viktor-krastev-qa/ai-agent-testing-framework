import pytest
from agent_testing.runner import ROOT, load_cases, run_suite
from agent_testing.engine import FixtureProvider

CASES = load_cases(ROOT / "data/cases.json")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_expected_agent_traces(case):
    report = run_suite([case], FixtureProvider(ROOT / "data/plans_good.json"))
    assert report["results"][0]["status"] == "PASS", report


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_deliberately_bad_plans_are_detected(case):
    report = run_suite([case], FixtureProvider(ROOT / "data/plans_bad.json"))
    assert report["results"][0]["status"] == "FAIL", report
