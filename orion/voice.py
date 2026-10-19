"""Voz: transcrição (Groq Whisper) e síntese (Cartesia) com cache."""
from __future__ import annotations

import logging
import os
import re
import tempfile
from pathlib import Path

import streamlit as st
from cartesia import Cartesia

from . import llm
from .config import MAX_CARACTERES_VOZ, MODELO_TRANSCRICAO, segredo

log = logging.getLogger(__name__)


def limpar_para_voz(texto: str) -> str:
    """Remove Markdown e símbolos que não devem ser pronunciados."""
    texto = re.sub(r"```[\s\S]*?```", " trecho de código omitido. ", str(texto or ""))
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", texto)
    texto = re.sub(r"[*_~`#]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) > MAX_CARACTERES_VOZ:
        corte = texto[:MAX_CARACTERES_VOZ]
        fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
        texto = corte[: fim + 1] if fim > 200 else corte
    return texto


@st.cache_data(show_spinner=False, max_entries=64, ttl=3600)
def _sintetizar(texto: str, voice_id: str, model_id: str) -> bytes:
    with Cartesia(api_key=segredo("CARTESIA_API_KEY")) as cli:
        audio = cli.tts.generate(
            model_id=model_id,
            transcript=texto,
            voice=voice_id,
            language="pt",
            output_format={"container": "wav", "encoding": "pcm_s16le",
                           "sample_rate": 44100},
        )
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as arq:
            caminho = arq.name
        try:
            audio.write_to_file(caminho)
            return Path(caminho).read_bytes()
        finally:
            if os.path.exists(caminho):
                os.remove(caminho)


def falar(texto: str) -> None:
    texto = limpar_para_voz(texto)
    if not texto:
        return
    if not segredo("CARTESIA_API_KEY") or not segredo("CARTESIA_VOICE_ID"):
        st.info("Configure CARTESIA_API_KEY e CARTESIA_VOICE_ID para ativar a voz.")
        return
    try:
        dados = _sintetizar(texto, segredo("CARTESIA_VOICE_ID"),
                            segredo("CARTESIA_MODEL_ID", "sonic-3.6"))
        st.audio(dados, format="audio/wav", autoplay=True)
    except Exception as erro:
        log.error("Falha na síntese de voz: %s", erro)
        st.error("Não consegui gerar a voz. Verifique a chave e o ID da voz.")


def transcrever(audio_bytes: bytes) -> str:
    resp = llm.cliente().audio.transcriptions.create(
        file=("orion_audio.wav", audio_bytes),
        model=MODELO_TRANSCRICAO,
        language="pt",
        response_format="text",
    )
    return str(resp).strip()
