# Strategy
Separate the scripted planner, execution guards and trace evaluator. Test expected traces plus independently targeted guard invariants. Every suite case starts with new in-memory tools so effects cannot leak across cases.

The corpus includes fifteen authored scenarios. Negative tool proposals may be correct *test inputs*: rejecting unauthorized calls is a PASS when expected. Deliberately bad plans are mismatches to the expected task behavior. Neither set measures language understanding.

Review unsuccessful traces by first identifying execution ERROR vs evaluated FAIL, then inspecting exact arguments, successful sequence, tool errors, terminal status and effect count. Regression of live agents, semantic final answers and durable side effects remain future scope.
