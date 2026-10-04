def evaluate_trace(case, trace, effects):
    expected = case["expected"]
    calls = [e for e in trace if e["type"] == "tool"]
    successful = [e for e in calls if e["status"] == "ok"]
    actual = [{"name": e["name"], "arguments": e["arguments"]} for e in successful]
    failed = [e["status"] for e in calls if e["status"] != "ok"]
    terminal = trace[-1]["status"]
    pairs = [("tool_sequence_and_arguments", actual, expected["calls"]),
             ("terminal_status", terminal, expected["terminal"]),
             ("tool_error_sequence", failed, expected.get("errors", [])),
             ("side_effect_count", effects, expected.get("effects", 0))]
    return [{"name": name, "passed": actual == target, "actual": actual, "expected": target}
            for name, actual, target in pairs]
