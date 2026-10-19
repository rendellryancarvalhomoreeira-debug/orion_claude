"""Persistência de conversas (`chats`) e preferências (`user_settings`).

Se as tabelas não existirem, o app continua funcionando só na sessão atual.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from . import auth
from .config import FUSO_HORARIO, PERSONAS
from .db import supabase

log = logging.getLogger(__name__)


def _uid() -> str:
    return str(auth.usuario().id)


def _agora() -> str:
    return datetime.now(ZoneInfo(FUSO_HORARIO)).isoformat()


def persistencia_ativa() -> bool:
    return st.session_state.get("_chats_tabela_ok", True)


def listar_chats() -> dict[str, dict]:
    try:
        res = (supabase().table("chats").select("id,title,messages")
               .eq("user_id", _uid()).order("updated_at", desc=True).execute())
        return {r["id"]: {"title": r["title"], "messages": r["messages"] or []}
                for r in (res.data or [])}
    except Exception as erro:
        log.info("Tabela 'chats' indisponível: %s", erro)
        st.session_state["_chats_tabela_ok"] = False
        return {}


def salvar_chat(chat_id: str, chat: dict) -> None:
    if not persistencia_ativa():
        return
    try:
        supabase().table("chats").upsert({
            "id": chat_id, "user_id": _uid(), "title": chat["title"],
            "messages": chat["messages"], "updated_at": _agora(),
        }).execute()
    except Exception as erro:
        log.warning("Não salvou a conversa: %s", erro)
        st.session_state["_chats_tabela_ok"] = False


def apagar_chat(chat_id: str) -> None:
    if not persistencia_ativa():
        return
    try:
        (supabase().table("chats").delete()
         .eq("id", chat_id).eq("user_id", _uid()).execute())
    except Exception as erro:
        log.warning("Não apagou a conversa: %s", erro)


def carregar_persona() -> str | None:
    try:
        res = (supabase().table("user_settings").select("persona")
               .eq("user_id", _uid()).maybe_single().execute())
        if res and res.data and res.data.get("persona") in PERSONAS:
            return res.data["persona"]
    except Exception:
        pass
    return None


def salvar_persona(persona: str) -> None:
    try:
        supabase().table("user_settings").upsert({
            "user_id": _uid(), "persona": persona, "updated_at": _agora(),
        }).execute()
    except Exception:
        pass
