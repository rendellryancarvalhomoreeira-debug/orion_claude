"""Interface Streamlit: login, barra lateral e área de chat."""
from __future__ import annotations

import hashlib
import logging
import uuid

import streamlit as st

from . import auth, llm, memory, storage, voice
from .config import (APP_NOME, MODELO_PADRAO, MODELOS, PERSONA_PADRAO, PERSONAS)
from .render import renderizar_resposta

log = logging.getLogger(__name__)


# ---------------------------------------------------------------- estado
def inicializar_estado() -> None:
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("modelo", MODELO_PADRAO)
    st.session_state.setdefault("temperatura", 0.7)
    st.session_state.setdefault("voz_ativa", True)
    st.session_state.setdefault("busca_ativa", True)
    st.session_state.setdefault("persona", PERSONA_PADRAO)


def preparar_usuario() -> None:
    """Carrega conversas e preferências uma única vez após o login."""
    if st.session_state.get("_preparado"):
        return
    salva = storage.carregar_persona()
    if salva:
        st.session_state["persona"] = salva
    chats = storage.listar_chats()
    if not chats:
        chats = {_novo_id(): {"title": "Nova conversa", "messages": []}}
    st.session_state["chats"] = chats
    st.session_state["chat_ativo"] = next(iter(chats))
    memory.carregar()
    st.session_state["_preparado"] = True


def _novo_id() -> str:
    return str(uuid.uuid4())


def _chat_atual() -> dict:
    return st.session_state["chats"][st.session_state["chat_ativo"]]


# ---------------------------------------------------------------- login
def tela_login() -> None:
    st.title(f"🤖 {APP_NOME}")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Criar conta"])

    with aba_login, st.form("form_login"):
        email = st.text_input("E-mail", placeholder="seu@email.com")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("🔐 Entrar", use_container_width=True):
            if not email or not senha:
                st.warning("Digite seu e-mail e sua senha.")
            else:
                ok, msg = auth.entrar(email.strip(), senha)
                if ok:
                    st.rerun()
                st.error(msg)

    with aba_cadastro, st.form("form_cadastro"):
        novo_email = st.text_input("E-mail", placeholder="seu@email.com", key="cad_email")
        nova_senha = st.text_input("Senha", type="password", key="cad_senha")
        confirmar = st.text_input("Confirmar senha", type="password")
        if st.form_submit_button("🆕 Criar conta", use_container_width=True):
            if not novo_email or not nova_senha:
                st.warning("Preencha todos os campos.")
            elif nova_senha != confirmar:
                st.error("As senhas não são iguais.")
            elif len(nova_senha) < auth.TAMANHO_MINIMO_SENHA:
                st.error(f"A senha precisa ter ao menos {auth.TAMANHO_MINIMO_SENHA} caracteres.")
            else:
                ok, msg = auth.criar_conta(novo_email.strip(), nova_senha)
                if ok and auth.logado():
                    st.rerun()
                (st.success if ok else st.error)(msg)


# ---------------------------------------------------------------- barra lateral
def _ao_mudar_persona() -> None:
    storage.salvar_persona(st.session_state["persona"])


def _nova_conversa() -> None:
    novo = _novo_id()
    st.session_state["chats"] = {novo: {"title": "Nova conversa", "messages": []},
                                 **st.session_state["chats"]}
    st.session_state["chat_ativo"] = novo


def _apagar_conversa_atual() -> None:
    ativo = st.session_state["chat_ativo"]
    storage.apagar_chat(ativo)
    del st.session_state["chats"][ativo]
    if not st.session_state["chats"]:
        _nova_conversa()
    else:
        st.session_state["chat_ativo"] = next(iter(st.session_state["chats"]))


def _exportar_markdown(chat: dict) -> str:
    partes = [f"# {chat['title']}\n"]
    for m in chat["messages"]:
        quem = "Você" if m["role"] == "user" else "ORION"
        partes.append(f"**{quem}:** {m['content']}\n")
    return "\n".join(partes)


def sidebar() -> None:
    with st.sidebar:
        st.title(f"🤖 {APP_NOME}")
        st.caption(auth.usuario().email)
        if st.button("🚪 Sair", use_container_width=True):
            auth.sair()
            st.rerun()

        st.divider()
        st.subheader("⚙️ Ajustes")
        st.selectbox("Personalidade", list(PERSONAS), key="persona",
                     on_change=_ao_mudar_persona)
        st.caption(PERSONAS[st.session_state["persona"]]["descricao"])
        st.selectbox("Modelo", list(MODELOS), key="modelo")
        st.slider("Criatividade", 0.0, 1.5, step=0.1, key="temperatura",
                  help="Valores baixos = respostas mais precisas; altos = mais criativas.")
        st.toggle("🔊 Falar as respostas", key="voz_ativa")
        busca_ok = llm.suporta_busca(MODELOS[st.session_state["modelo"]])
        st.toggle("🌐 Pesquisar na internet", key="busca_ativa", disabled=not busca_ok,
                  help="Disponível nos modelos GPT-OSS. Nesse modo a resposta aparece de uma vez.")
        if st.button("Testar voz", use_container_width=True):
            voice.falar("Olá. Eu sou o ORION. Estou pronto para ajudar.")

        st.divider()
        st.subheader("💬 Conversas")
        if st.button("➕ Nova conversa", use_container_width=True):
            _nova_conversa()
            st.rerun()
        for chat_id, chat in st.session_state["chats"].items():
            ativo = chat_id == st.session_state["chat_ativo"]
            if st.button(chat["title"], key=f"chat_{chat_id}", use_container_width=True,
                         type="primary" if ativo else "secondary"):
                st.session_state["chat_ativo"] = chat_id
                st.rerun()
        if not storage.persistencia_ativa():
            st.caption("⚠️ Conversas salvas só nesta sessão (veja schema.sql).")

        with st.expander("Gerenciar conversa atual"):
            atual = _chat_atual()
            novo_titulo = st.text_input("Título", value=atual["title"], key="campo_titulo")
            if st.button("Renomear", use_container_width=True) and novo_titulo.strip():
                atual["title"] = novo_titulo.strip()[:60]
                storage.salvar_chat(st.session_state["chat_ativo"], atual)
                st.rerun()
            st.download_button("⬇️ Exportar (.md)", _exportar_markdown(atual),
                               file_name="conversa_orion.md", mime="text/markdown",
                               use_container_width=True)
            if st.button("🗑️ Apagar conversa", use_container_width=True):
                _apagar_conversa_atual()
                st.rerun()

        st.divider()
        _secao_memoria()


def _secao_memoria() -> None:
    memorias = memory.carregar()
    st.subheader(f"🧠 Memória ({len(memorias)})")
    with st.expander("Ver e gerenciar"):
        if not memorias:
            st.caption("Nenhuma memória ainda. Diga, por exemplo: “meu nome é Ana”.")
        for m in memorias:
            col_texto, col_btn = st.columns([5, 1])
            col_texto.caption(f"**{m['category']}**: {m['content']}")
            if col_btn.button("✕", key=f"mem_{m['id']}", help="Esquecer"):
                memory.remover(m["id"])
                st.rerun()
        with st.form("form_memoria", clear_on_submit=True):
            nota = st.text_input("Adicionar nota", placeholder="Ex.: prefiro respostas curtas")
            if st.form_submit_button("Salvar") and nota.strip():
                memory.salvar("nota", nota)
                st.rerun()


# ---------------------------------------------------------------- chat
def _transcrever_audio(audio) -> str | None:
    if audio is None:
        return None
    dados = audio.getvalue()
    assinatura = hashlib.sha256(dados).hexdigest()
    if assinatura == st.session_state.get("_ultimo_audio"):
        return None  # mesma gravação: não reprocessar a cada rerun
    st.session_state["_ultimo_audio"] = assinatura
    try:
        texto = voice.transcrever(dados)
    except Exception as erro:
        log.error("Falha na transcrição: %s", erro)
        st.error("Não consegui transcrever o áudio.")
        return None
    if not texto:
        st.warning("Não reconheci palavras nessa gravação.")
        return None
    return texto


def _responder(prompt: str) -> None:
    chat_id = st.session_state["chat_ativo"]
    chat = _chat_atual()
    chat["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    nome = memory.extrair_nome(prompt)
    if nome:
        memory.salvar("nome", nome, unica=True)

    modelo = MODELOS[st.session_state["modelo"]]
    busca = st.session_state["busca_ativa"] and llm.suporta_busca(modelo)
    mensagens = llm.montar_mensagens(st.session_state["persona"], chat["messages"], busca)
    temperatura = st.session_state["temperatura"]

    with st.chat_message("assistant"):
        area = st.empty()
        resposta = ""
        try:
            if busca:
                with st.spinner("Pensando e pesquisando..."):
                    resposta = llm.gerar_resposta(modelo, mensagens, temperatura)
            else:
                for pedaco in llm.stream_resposta(modelo, mensagens, temperatura):
                    resposta += pedaco
                    area.markdown(resposta + "▌")
        except Exception as erro:
            log.error("Falha ao gerar resposta: %s", erro)
            if not resposta:
                area.empty()
                chat["messages"].pop()
                st.error("Não consegui gerar a resposta agora. Tente novamente.")
                return
            st.warning("A resposta foi interrompida antes do fim.")

        if not resposta:
            resposta = "Desculpe, não consegui gerar uma resposta agora."
        with area.container():
            renderizar_resposta(resposta)
        if st.session_state["voz_ativa"]:
            voice.falar(resposta)

    chat["messages"].append({"role": "assistant", "content": resposta})
    if chat["title"] == "Nova conversa":
        chat["title"] = prompt.strip().replace("\n", " ")[:40] or "Conversa"
    storage.salvar_chat(chat_id, chat)


def area_chat() -> None:
    chat = _chat_atual()
    st.title(chat["title"])
    for m in chat["messages"]:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                renderizar_resposta(m["content"])
            else:
                st.markdown(m["content"])

    with st.expander("🎙️ Falar com o ORION"):
        audio = st.audio_input("Gravar mensagem de voz", key="entrada_audio")
    texto = st.chat_input("Digite sua mensagem para o ORION...")
    prompt = texto or _transcrever_audio(audio)
    if prompt:
        _responder(prompt)
