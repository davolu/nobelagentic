"""math pack: safe expression evaluation + unit conversion."""
from __future__ import annotations

import ast
import math
import operator as op

from ..tools import tool

_OPS = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
        ast.Pow: op.pow, ast.Mod: op.mod, ast.USub: op.neg, ast.FloorDiv: op.floordiv}
_FUNCS = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_FUNCS.update(abs=abs, round=round, min=min, max=max, sum=sum)


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _FUNCS:
        return _FUNCS[node.func.id](*(_eval(a) for a in node.args))
    if isinstance(node, ast.Name) and node.id in {"pi", "e"}:
        return getattr(math, node.id)
    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


@tool
def calculate(expression: str) -> float:
    """Evaluate a math expression safely, e.g. 'sqrt(2) * 10 ** 3' or '15 % 4'."""
    return _eval(ast.parse(expression, mode="eval").body)


_UNITS = {  # to base unit
    "km": 1000, "m": 1, "cm": 0.01, "mi": 1609.344, "ft": 0.3048, "in": 0.0254,
    "kg": 1, "g": 0.001, "lb": 0.45359237, "oz": 0.028349523,
    "l": 1, "ml": 0.001, "gal": 3.785411784,
}


@tool
def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert between common length, mass and volume units (km, m, mi, ft, kg, lb, l, gal...)."""
    f, t = from_unit.lower(), to_unit.lower()
    if f in {"c", "f"} and t in {"c", "f"}:
        return value if f == t else (value * 9 / 5 + 32 if f == "c" else (value - 32) * 5 / 9)
    return value * _UNITS[f] / _UNITS[t]


TOOLS = [calculate, convert_units]
