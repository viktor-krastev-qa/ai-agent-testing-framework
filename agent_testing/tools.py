import re


class ToolError(Exception):
    pass


class TransientError(ToolError):
    pass


class SimulatedTools:
    """In-memory sandbox. No real orders, refunds, network or money."""
    def __init__(self, authorized_orders, confirmed=False, failures=None):
        self.authorized_orders = set(authorized_orders)
        self.confirmed = confirmed
        self.failures = dict(failures or {})
        self.refunds = set()
        self.effect_count = 0

    def execute(self, name, arguments):
        if not isinstance(name, str) or name not in {"get_order", "get_policy", "request_refund"}:
            raise ToolError("unknown_tool")
        if not isinstance(arguments, dict):
            raise ToolError("invalid_arguments")
        expected = set() if name == "get_policy" else {"order_id"}
        if set(arguments) != expected:
            raise ToolError("invalid_arguments")
        if name != "get_policy":
            order_id = arguments["order_id"]
            if not isinstance(order_id, str) or not re.fullmatch(r"ORD-\d{3}", order_id):
                raise ToolError("invalid_order_id")
            if order_id not in self.authorized_orders:
                raise ToolError("unauthorized_order")
        if name == "request_refund" and not self.confirmed:
            raise ToolError("confirmation_required")
        if self.failures.get(name, 0) > 0:
            self.failures[name] -= 1
            raise TransientError("temporary_unavailable")
        if name == "get_policy":
            return {"return_days": 30, "unused_required": True}
        if name == "get_order":
            return {"order_id": order_id, "status": "delivered"}
        duplicate = order_id in self.refunds
        self.refunds.add(order_id)
        if not duplicate:
            self.effect_count += 1
        return {"order_id": order_id, "refund": "already_requested" if duplicate else "requested"}
