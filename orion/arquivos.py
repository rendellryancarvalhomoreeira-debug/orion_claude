"""Análise de arquivos: imagens (visão) e documentos (PDF/texto)."""
from __future__ import annotations

import base64
import io

from . import llm
from .config import MODELO_VISAO

EXT_IMAGEM = (".png", ".jpg", ".jpeg", ".webp", ".gif")
LIMITE_TEXTO = 12000
LIMITE_IMAGEM = 3_000_000  # a Groq limita imagens em base64 a ~4 MB


def eh_imagem(nome: str) -> bool:
    return nome.lower().endswith(EXT_IMAGEM)


def analisar_imagem(dados: bytes, nome: str, pergunta: str) -> str:
    if len(dados) > LIMITE_IMAGEM:
        raise ValueError("A imagem passa de 3 MB. Envie uma versão menor.")
    ext = nome.lower().rsplit(".", 1)[-1]
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"
    url = f"data:{mime};base64,{base64.b64encode(dados).decode()}"
    resp = llm.cliente().chat.completions.create(
        model=MODELO_VISAO, temperature=0.4, max_tokens=1500,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": f"{pergunta}\n\nResponda em português do Brasil."},
            {"type": "image_url", "image_url": {"url": url}},
        ]}],
    )
    return resp.choices[0].message.content or ""


def extrair_texto(nome: str, dados: bytes) -> str:
    if nome.lower().endswith(".pdf"):
        from pypdf import PdfReader
        leitor = PdfReader(io.BytesIO(dados))
        texto = "\n".join((p.extract_text() or "") for p in leitor.pages)
    else:
        texto = dados.decode("utf-8", errors="replace")
    texto = texto.strip()
    if not texto:
        raise ValueError("Não encontrei texto nesse arquivo (PDF escaneado?).")
    if len(texto) > LIMITE_TEXTO:
        texto = texto[:LIMITE_TEXTO] + "\n[... conteúdo cortado por tamanho ...]"
    return texto
