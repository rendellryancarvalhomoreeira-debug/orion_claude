"""Tarefas e lembretes do usuário (tabela `tasks`)."""
from __future__ import annotations

import logging

import streamlit as st

from . import auth
from .db import supabase

log = logging.getLogger(__name__)


def listar(forcar: bool = False) -> list[dict]:
    """Tarefas pendentes, em cache na sessão."""
    if forcar or "_tarefas" not in st.session_state:
        try:
            res = (supabase().table("tasks").select("*")
                   .eq("user_id", str(auth.usuario().id)).eq("done", False)
                   .order("created_at").execute())
            st.session_state["_tarefas"] = res.data or []
        except Exception as erro:
            log.error("Erro ao listar tarefas: %s", erro)
            st.session_state["_tarefas"] = []
    return st.session_state["_tarefas"]


def criar(titulo: str, prazo: str = "") -> bool:
    try:
        supabase().table("tasks").insert({
            "user_id": str(auth.usuario().id), "title": titulo.strip(),
            "due": prazo.strip(), "done": False,
        }).execute()
        listar(forcar=True)
        return True
    except Exception as erro:
        log.error("Erro ao criar tarefa: %s", erro)
        return False


def concluir(tarefa_id) -> bool:
    try:
        (supabase().table("tasks").update({"done": True})
         .eq("id", tarefa_id).eq("user_id", str(auth.usuario().id)).execute())
        listar(forcar=True)
        return True
    except Exception as erro:
        log.error("Erro ao concluir tarefa: %s", erro)
        return False


def concluir_por_titulo(trecho: str) -> str:
    trecho = trecho.strip().lower()
    achadas = [t for t in listar(forcar=True) if trecho in t["title"].lower()]
    if not achadas:
        return f"Nenhuma tarefa pendente contém '{trecho}'."
    if len(achadas) > 1:
        nomes = "; ".join(t["title"] for t in achadas)
        return f"Mais de uma tarefa combina: {nomes}. Peça ao usuário para ser mais específico."
    return (f"Tarefa '{achadas[0]['title']}' concluída."
            if concluir(achadas[0]["id"]) else "Não consegui concluir a tarefa.")
