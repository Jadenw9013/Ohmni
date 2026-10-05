"""Small arithmetic vocabulary for explicitly authored electrical equations.

Unknown names or unsupported syntax are errors, never zero or a passing check.
No Python eval, attributes, indexing, imports or user functions are available.
"""

from __future__ import annotations

import ast
import math
import operator


class ExpressionUnavailable(ValueError):
    pass


def evaluate(expression: str, values: dict[str, float]) -> float | bool:
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.Div: operator.truediv, ast.Pow: operator.pow}
    comparisons = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
                   ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}
    functions = {"abs": abs, "min": min, "max": max, "sqrt": math.sqrt,
                 "clamp": lambda x, low, high: min(high, max(low, x))}

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in {int, float, bool}:
            return node.value
        if isinstance(node, ast.Name) and node.id in values:
            return values[node.id]
        if isinstance(node, ast.Name) and node.id == "pi":
            return math.pi
        if isinstance(node, ast.BinOp) and type(node.op) in binary:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 64:
                raise ExpressionUnavailable("exponent outside bounded arithmetic")
            return binary[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp):
            if isinstance(node.op, ast.USub):
                return -visit(node.operand)
            if isinstance(node.op, ast.UAdd):
                return visit(node.operand)
            if isinstance(node.op, ast.Not):
                return not visit(node.operand)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions and not node.keywords:
            return functions[node.func.id](*(visit(arg) for arg in node.args))
        if isinstance(node, ast.Compare) and all(type(op) in comparisons for op in node.ops):
            operands = [visit(node.left), *(visit(x) for x in node.comparators)]
            return all(comparisons[type(op)](operands[i], operands[i + 1]) for i, op in enumerate(node.ops))
        if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
            evaluated = [bool(visit(x)) for x in node.values]
            return all(evaluated) if isinstance(node.op, ast.And) else any(evaluated)
        if isinstance(node, ast.IfExp):
            return visit(node.body) if visit(node.test) else visit(node.orelse)
        raise ExpressionUnavailable(f"unsupported syntax or unknown name: {ast.dump(node)}")

    try:
        tree = ast.parse(expression, mode="eval")
        if len(list(ast.walk(tree))) > 256:
            raise ExpressionUnavailable("expression exceeds bounded arithmetic size")
        if any(not math.isfinite(v) for v in values.values()):
            raise ExpressionUnavailable("non-finite input")
        result = visit(tree.body)
        if type(result) not in {int, float, bool} or not math.isfinite(result):
            raise ExpressionUnavailable("non-finite result")
        return result
    except (SyntaxError, TypeError, OverflowError, ZeroDivisionError, ValueError) as exc:
        raise ExpressionUnavailable(str(exc)) from exc
