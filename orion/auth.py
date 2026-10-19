"""Autenticação com Supabase."""
from __future__ import annotations

import logging

import streamlit as st

from .db import supabase

log = logging.getLogger(__name__)
TAMANHO_MINIMO_SENHA = 8


def logado() -> bool:
    return st.session_state.get("user") is not None


def usuario():
    return st.session_state["user"]


def entrar(email: str, senha: str) -> tuple[bool, str]:
    try:
        resp = supabase().auth.sign_in_with_password({"email": email, "password": senha})
        if resp.session is None or resp.user is None:
            return False, "Não foi possível iniciar a sessão."
        st.session_state["user"] = resp.user
        return True, "Login realizado."
    except Exception as erro:
        log.warning("Falha no login: %s", erro)
        return False, "E-mail ou senha inválidos."


def criar_conta(email: str, senha: str) -> tuple[bool, str]:
    try:
        resp = supabase().auth.sign_up({"email": email, "password": senha})
        if resp.session is None:
            return True, "Conta criada! Confirme o e-mail para entrar."
        st.session_state["user"] = resp.user
        return True, "Conta criada com sucesso!"
    except Exception as erro:
        log.warning("Falha no cadastro: %s", erro)
        return False, f"Não foi possível criar a conta: {erro}"


def sair() -> None:
    try:
        supabase().auth.sign_out()
    except Exception:
        pass
    # Limpa tudo: conversas, memórias em cache e o cliente da sessão.
    for chave in list(st.session_state.keys()):
        del st.session_state[chave]
