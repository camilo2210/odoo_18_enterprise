# -*- coding: utf-8 -*-
"""
Domain Utility Functions
------------------------

Converts Odoo-style domains into human-readable or Pythonic boolean expressions.
Example:
    Input:  ["|", ("partner_id", "in", [15]), ("partner_id.country_id", "=", 233)]
    Output: "(partner_id in [15]) or (partner_id.country_id == 233)"
"""

import logging
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


def domain_to_expression(domain):
    """
    Convert an Odoo domain (list or string) into a boolean-like expression string.

    :param domain: list or string (e.g. ["|", ("a", "=", 1), ("b", "=", 2)])
    :return: str expression (e.g. "(a == 1) or (b == 2)")
    """
    # Safely parse string representation
    if isinstance(domain, str):
        try:
            domain = safe_eval(domain)
        except Exception:
            _logger.warning("Invalid domain string: %s", domain)
            return ""

    if not isinstance(domain, list):
        return ""
    op_map = {
        "=": "==", "!=": "!=", ">": ">", "<": "<", ">=": ">=", "<=": "<=",
        "in": "in", "not in": "not in",
        "like": "like", "ilike": "ilike",
        "not like": "not like", "not ilike": "not ilike",
        "=like": "like",
        # Unsupported in expressions
        "child_of": None, "parent_of": None,
    }

    def _to_str(val):
        if isinstance(val, str):
            return f"'{val}'"
        if isinstance(val, (list, tuple, set)):
            return f"[{', '.join(map(_to_str, val))}]"
        return str(val)

    def _convert(dom):
        """Recursive helper"""
        if isinstance(dom, tuple) and len(dom) == 3:
            field, op, val = dom
            py_op = op_map.get(op)
            if not py_op:
                return f"/* Unsupported operator: {op} */"
            return f"{field} {py_op} {_to_str(val)}"

        if not isinstance(dom, list) or not dom:
            return ""

        token = dom[0]

        if token in ("|", "&", "!"):
            if token == "!":  # unary NOT
                expr = _convert(dom[1])
                return f"not ({expr})" if expr else ""
            else:
                op_symbol = "or" if token == "|" else "and"
                left = _convert(dom[1])
                right = _convert(dom[2])
                return f"({left}) {op_symbol} ({right})"

        parts = [_convert(x) for x in dom]
        parts = [p for p in parts if p]
        return " and ".join(parts)
    return _convert(domain)
