"""Cliente Supabase isolado por sessão.

IMPORTANTE: um cliente global compartilharia a sessão de autenticação entre
todos os visitantes do app. Aqui cada sessão do Streamlit tem o seu.
"""
from __future__ import annotations

import streamlit as st
from supabase import Client, create_client

from .config import segredo


def supabase() -> Client:
    if "_supabase" not in st.session_state:
        st.session_state["_supabase"] = create_client(
            segredo("SUPABASE_URL"), segredo("SUPABASE_KEY")
        )
    return st.session_state["_supabase"]
