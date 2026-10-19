"""Memória permanente do usuário (tabela `memories`)."""
from __future__ import annotations

import logging
import re

import streamlit as st

from . import auth
from .db import supabase

log = logging.getLogger(__name__)

_GATILHOS_NOME = re.compile(
    r"(?:meu nome (?:é|e)|me chamo|eu me chamo|pode me chamar de)\s+"
    r"([^\W\d_]+(?:\s+[^\W\d_]+){0,2})",
    re.IGNORECASE,
)
_PARADAS = {"e", "mas", "porque", "que", "pra", "para", "e,"}


def extrair_nome(texto: str) -> str | None:
    """Extrai um nome de frases como 'meu nome é Ana Souza e eu gosto de…'."""
    achado = _GATILHOS_NOME.search(texto)
    if not achado:
        return None
    palavras = []
    for palavra in achado.group(1).split():
        if palavra.lower() in _PARADAS:
            break
        palavras.append(palavra)
    return " ".join(palavras).title() if palavras else None


def carregar(forcar: bool = False) -> list[dict]:
    """Carrega memórias uma vez por sessão (evita consultar o banco a cada rerun)."""
    if forcar or "_memorias" not in st.session_state:
        try:
            res = (
                supabase().table("memories").select("*")
                .eq("user_id", str(auth.usuario().id))
                .order("created_at").execute()
            )
            st.session_state["_memorias"] = res.data or []
        except Exception as erro:
            log.error("Erro ao carregar memórias: %s", erro)
            st.session_state["_memorias"] = []
    return st.session_state["_memorias"]


def salvar(categoria: str, conteudo: str, unica: bool = False) -> bool:
    """Salva uma memória sem duplicar. `unica=True` substitui a da mesma categoria."""
    conteudo = conteudo.strip()
    if not conteudo:
        return False
    existentes = carregar()
    if any(m["category"] == categoria and m["content"].lower() == conteudo.lower()
           for m in existentes):
        return True
    if unica:
        for antiga in [m for m in existentes if m["category"] == categoria]:
            remover(antiga["id"], recarregar=False)
    try:
        supabase().table("memories").insert({
            "user_id": str(auth.usuario().id),
            "category": categoria,
            "content": conteudo,
        }).execute()
        carregar(forcar=True)
        return True
    except Exception as erro:
        log.error("Erro ao salvar memória: %s", erro)
        return False


def remover(memoria_id, recarregar: bool = True) -> bool:
    try:
        (supabase().table("memories").delete()
         .eq("id", memoria_id).eq("user_id", str(auth.usuario().id)).execute())
        if recarregar:
            carregar(forcar=True)
        return True
    except Exception as erro:
        log.error("Erro ao remover memória: %s", erro)
        return False


def como_contexto() -> str:
    memorias = carregar()
    if not memorias:
        return "O usuário ainda não tem memórias salvas."
    linhas = "\n".join(f"- {m['category']}: {m['content']}" for m in memorias)
    return f"Memórias sobre o usuário (use quando forem relevantes):\n{linhas}"
