"""Chamada ao modelo (Groq) com streaming."""
from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from groq import Groq

from . import memory
from .config import (FUSO_HORARIO, MAX_MENSAGENS_CONTEXTO, MODELOS_COM_BUSCA,
                     PERSONAS, PROMPT_BASE, PROMPT_BUSCA, segredo)


@st.cache_resource
def cliente() -> Groq:
    return Groq(api_key=segredo("GROQ_API_KEY"))


def _data_hora() -> str:
    agora = datetime.now(ZoneInfo(FUSO_HORARIO))
    return agora.strftime("%d/%m/%Y, %H:%M (horário de Brasília)")


def suporta_busca(modelo: str) -> bool:
    return modelo in MODELOS_COM_BUSCA


def montar_mensagens(persona: str, historico: list[dict], busca: bool = False) -> list[dict]:
    partes = [PROMPT_BASE, PERSONAS[persona]["prompt"],
              f"Data e hora atuais: {_data_hora()}. Nunca invente a data ou a hora."]
    if busca:
        partes.append(PROMPT_BUSCA)
    partes.append(memory.como_contexto())
    sistema = "\n\n".join(partes)
    recentes = historico[-MAX_MENSAGENS_CONTEXTO:]
    return [{"role": "system", "content": sistema}, *recentes]


def stream_resposta(modelo: str, mensagens: list[dict],
                    temperatura: float = 0.7, max_tokens: int = 2048) -> Iterator[str]:
    fluxo = cliente().chat.completions.create(
        model=modelo, messages=mensagens, temperature=temperatura,
        max_tokens=max_tokens, stream=True,
    )
    for pedaco in fluxo:
        if not pedaco.choices:
            continue
        texto = pedaco.choices[0].delta.content
        if texto:
            yield texto


def gerar_resposta(modelo: str, mensagens: list[dict], temperatura: float = 0.7) -> str:
    """Resposta completa (sem streaming) com pesquisa na internet habilitada."""
    resp = cliente().chat.completions.create(
        model=modelo, messages=mensagens, temperature=temperatura,
        tools=[{"type": "browser_search"}], tool_choice="auto",
    )
    return resp.choices[0].message.content or ""
