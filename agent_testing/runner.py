import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
from agent_testing.engine import FixtureProvider, run_agent
from agent_testing.evaluation import evaluate_trace
from agent_testing.tools import SimulatedTools

ROOT = Path(__file__).resolve().parents[1]


def load_cases(path):
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not cases:
        raise ValueError("Cases must be a nonempty list")
    ids = set()
    for case in cases:
        for field in ("id", "prompt", "category"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError("Invalid case field")
        if case["id"] in ids:
            raise ValueError("Duplicate case ID")
        ids.add(case["id"])
        if not isinstance(case.get("context"), dict) or not isinstance(case.get("expected"), dict):
            raise ValueError("Missing context/expected")
        if not isinstance(case["context"].get("authorized_orders"), list):
            raise ValueError("Missing authorized_orders")
        if not isinstance(case["expected"].get("calls"), list) or not isinstance(case["expected"].get("terminal"), str):
            raise ValueError("Invalid expectation")
    return cases


def run_suite(cases, provider):
    results = []
    for case in cases:
        try:
            tools = SimulatedTools(**case["context"])
            trace = run_agent(provider.agent_for(case), tools,
                              max_steps=case.get("max_steps", 5), max_retries=case.get("max_retries", 1))
            checks = evaluate_trace(case, trace, tools.effect_count)
            status = "PASS" if all(c["passed"] for c in checks) else "FAIL"
            error = None
        except Exception as exc:
            trace, checks, status, error = [], [], "ERROR", type(exc).__name__
        results.append({"id": case["id"], "category": case["category"], "prompt": case["prompt"],
                        "checks": checks, "trace": trace, "status": status, "error": error})
    return {"created_utc": datetime.now(timezone.utc).isoformat(),
            "provider": "scripted_fixture", "results": results,
            "summary": {"total": len(results), **{s.lower(): sum(r["status"] == s for r in results)
                                                   for s in ("PASS", "FAIL", "ERROR")}}}


def write_reports(report, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = []
    for row in report["results"]:
        failures = [c for c in row["checks"] if not c["passed"]]
        values = [row["id"], row["category"], row["status"], row["prompt"],
                  json.dumps(failures, indent=2), json.dumps(row["trace"], indent=2), row["error"] or ""]
        rows.append("<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in values) + "</tr>")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><title>Agent testing report</title>
<style>body{font:16px system-ui;margin:30px;color:#172234}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd;padding:10px;text-align:left;vertical-align:top}td{white-space:pre-wrap;font-size:13px}th{background:#e9eef7}</style>
<h1>AI Agent Testing Framework</h1><p>Offline scripted agent and simulated tools. No real LLM or external side effects.</p>"""
    page += "<pre>" + html.escape(json.dumps(report["summary"], indent=2)) + "</pre>"
    page += "<table><tr><th>Case</th><th>Category</th><th>Status</th><th>Prompt</th><th>Failed checks</th><th>Execution trace</th><th>Error</th></tr>" + "".join(rows) + "</table></html>"
    (output / "report.html").write_text(page, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plans", type=Path, default=ROOT / "data/plans_good.json")
    parser.add_argument("--cases", type=Path, default=ROOT / "data/cases.json")
    parser.add_argument("--output", type=Path, default=Path("reports/good"))
    args = parser.parse_args()
    try:
        report = run_suite(load_cases(args.cases), FixtureProvider(args.plans))
        write_reports(report, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Configuration error: {type(exc).__name__}\n")
    print(json.dumps(report["summary"]))
    print(f"Report: {args.output / 'report.html'}")
    return int(bool(report["summary"]["fail"] or report["summary"]["error"]))


if __name__ == "__main__":
    raise SystemExit(main())
