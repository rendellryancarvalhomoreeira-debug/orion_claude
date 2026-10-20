"""Calculadora segura (sem eval): só números, operadores e funções matemáticas."""
from __future__ import annotations

import ast
import math
import operator as op

_OPS = {
    ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Pow: op.pow, ast.Mod: op.mod, ast.FloorDiv: op.floordiv,
    ast.USub: op.neg, ast.UAdd: op.pos,
}
_FUNCOES = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "abs": abs, "round": round, "min": min, "max": max,
}
_CONSTANTES = {"pi": math.pi, "e": math.e}


def _avaliar(no):
    if isinstance(no, ast.Constant) and isinstance(no.value, (int, float)):
        return no.value
    if isinstance(no, ast.BinOp) and type(no.op) in _OPS:
        esq, dir_ = _avaliar(no.left), _avaliar(no.right)
        if isinstance(no.op, ast.Pow) and abs(dir_) > 1000:
            raise ValueError("expoente grande demais")
        return _OPS[type(no.op)](esq, dir_)
    if isinstance(no, ast.UnaryOp) and type(no.op) in _OPS:
        return _OPS[type(no.op)](_avaliar(no.operand))
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in _FUNCOES:
        return _FUNCOES[no.func.id](*[_avaliar(a) for a in no.args])
    if isinstance(no, ast.Name) and no.id in _CONSTANTES:
        return _CONSTANTES[no.id]
    raise ValueError("expressão não permitida")


def calcular(expressao: str) -> float | int:
    expressao = expressao.strip().replace("^", "**").replace(",", ".")
    if not expressao or len(expressao) > 200:
        raise ValueError("expressão vazia ou longa demais")
    return _avaliar(ast.parse(expressao, mode="eval").body)
