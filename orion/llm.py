"""Chamadas ao modelo (Groq): streaming, agente com ferramentas e pesquisa."""
from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from groq import Groq

from . import memory, tools
from .config import (FUSO_HORARIO, MAX_MENSAGENS_CONTEXTO, MODELO_PESQUISA,
                     PERSONAS, PROMPT_BASE, PROMPT_FERRAMENTAS, segredo)

log = logging.getLogger(__name__)
MAX_PASSOS_AGENTE = 5


@st.cache_resource
def cliente() -> Groq:
    return Groq(api_key=segredo("GROQ_API_KEY"))


def _data_hora() -> str:
    agora = datetime.now(ZoneInfo(FUSO_HORARIO))
    return agora.strftime("%d/%m/%Y, %H:%M (horário de Brasília)")


def montar_mensagens(persona: str, historico: list[dict],
                     ferramentas: bool = False) -> list[dict]:
    partes = [PROMPT_BASE, PERSONAS[persona]["prompt"],
              f"Data e hora atuais: {_data_hora()}. Nunca invente a data ou a hora."]
    if ferramentas:
        partes.append(PROMPT_FERRAMENTAS)
    partes.append(memory.como_contexto())
    return [{"role": "system", "content": "\n\n".join(partes)},
            *historico[-MAX_MENSAGENS_CONTEXTO:]]


def stream_resposta(modelo: str, mensagens: list[dict],
                    temperatura: float = 0.7, max_tokens: int = 2048) -> Iterator[str]:
    fluxo = cliente().chat.completions.create(
        model=modelo, messages=mensagens, temperature=temperatura,
        max_tokens=max_tokens, stream=True)
    for pedaco in fluxo:
        if pedaco.choices and pedaco.choices[0].delta.content:
            yield pedaco.choices[0].delta.content


def completar(modelo: str, mensagens: list[dict], temperatura: float = 0.7) -> str:
    resp = cliente().chat.completions.create(
        model=modelo, messages=mensagens, temperature=temperatura, max_tokens=2048)
    return resp.choices[0].message.content or ""


def pesquisar(consulta: str) -> str:
    """Pesquisa na web usando o browser_search da Groq (chamado pela ferramenta)."""
    resp = cliente().chat.completions.create(
        model=MODELO_PESQUISA, temperature=0.2,
        messages=[
            {"role": "system", "content": (
                "Pesquise na internet e responda em português com os fatos "
                "atuais, de forma objetiva e citando o nome das fontes. Se as "
                "fontes divergirem ou faltar informação, diga isso. "
                f"Data atual: {_data_hora()}.")},
            {"role": "user", "content": consulta},
        ],
        tools=[{"type": "browser_search"}], tool_choice="auto")
    return resp.choices[0].message.content or "Sem resultados."


def executar_agente(modelo: str, mensagens: list[dict], temperatura: float = 0.7,
                    ao_usar_ferramenta: Callable[[str, dict], None] | None = None) -> str:
    """Laço de function calling: o modelo chama ferramentas até ter a resposta."""
    msgs = list(mensagens)
    for _ in range(MAX_PASSOS_AGENTE):
        resp = cliente().chat.completions.create(
            model=modelo, messages=msgs, temperature=temperatura,
            tools=tools.FERRAMENTAS, tool_choice="auto")
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return msg.content or ""
        msgs.append({"role": "assistant", "content": msg.content or None,
                     "tool_calls": [{"id": c.id, "type": "function",
                                     "function": {"name": c.function.name,
                                                  "arguments": c.function.arguments}}
                                    for c in msg.tool_calls]})
        for chamada in msg.tool_calls:
            try:
                args = json.loads(chamada.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if ao_usar_ferramenta:
                ao_usar_ferramenta(chamada.function.name, args)
            msgs.append({"role": "tool", "tool_call_id": chamada.id,
                         "content": tools.executar(chamada.function.name, args)})
    # Limite de passos atingido: pede a resposta final sem ferramentas.
    return completar(modelo, msgs, temperatura)
