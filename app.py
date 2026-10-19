"""ORION AI — ponto de entrada. Execute: streamlit run app.py"""
import streamlit as st

st.set_page_config(page_title="ORION AI", page_icon="🤖", layout="wide")

from orion import auth, ui  # noqa: E402  (depois do set_page_config)

ui.inicializar_estado()

if not auth.logado():
    ui.tela_login()
    st.stop()

ui.preparar_usuario()
ui.sidebar()
ui.area_chat()
