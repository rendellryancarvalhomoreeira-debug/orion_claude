"""Renderização de respostas: Markdown + fórmulas matemáticas."""
from __future__ import annotations

import re

import streamlit as st

_INLINE = re.compile(r"\\\((.+?)\\\)")
_SINAIS_MATEMATICOS = ("=", "^", "\\", "√", "∑", "∫", "≤", "≥")


def _formula_isolada(linha: str) -> str | None:
    limpa = linha.strip()
    if limpa.startswith(r"\[") and limpa.endswith(r"\]"):
        return limpa[2:-2].strip()
    if limpa.startswith("$$") and limpa.endswith("$$") and len(limpa) > 4:
        return limpa[2:-2].strip()
    if (len(limpa) >= 3 and limpa.startswith("[") and limpa.endswith("]")
            and any(s in limpa for s in _SINAIS_MATEMATICOS)
            and not limpa.startswith(("[http", "[www."))):
        return limpa[1:-1].strip()
    return None


def renderizar_resposta(texto: str) -> None:
    if not texto:
        return
    linhas = str(texto).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    bloco: list[str] = []
    em_codigo = False

    def descarregar() -> None:
        if bloco:
            st.markdown("\n".join(bloco))
            bloco.clear()

    for linha in linhas:
        if linha.strip().startswith("```"):
            em_codigo = not em_codigo
            bloco.append(linha)
            continue
        if not em_codigo:  # nunca mexe em fórmulas dentro de blocos de código
            formula = _formula_isolada(linha)
            if formula:
                descarregar()
                st.latex(formula)
                continue
            linha = _INLINE.sub(lambda m: f"${m.group(1).strip()}$", linha)
        bloco.append(linha)
    descarregar()
