"""Ferramentas que o ORION pode chamar (function calling)."""
from __future__ import annotations

import logging

import requests

from . import memory, tarefas
from .calculo import calcular

log = logging.getLogger(__name__)

ROTULOS = {
    "pesquisar_web": "Pesquisando na internet",
    "obter_clima": "Consultando o clima",
    "calcular": "Calculando",
    "criar_tarefa": "Criando tarefa",
    "listar_tarefas": "Lendo suas tarefas",
    "concluir_tarefa": "Concluindo tarefa",
    "salvar_memoria": "Guardando na memória",
}


def _def(nome: str, descricao: str, propriedades: dict, obrigatorios: list[str]) -> dict:
    return {"type": "function", "function": {
        "name": nome, "description": descricao,
        "parameters": {"type": "object", "properties": propriedades,
                       "required": obrigatorios}}}


FERRAMENTAS = [
    _def("pesquisar_web",
         "Pesquisa na internet informações atuais: notícias, preços, cotações, "
         "resultados de jogos, lançamentos, política e fatos recentes.",
         {"consulta": {"type": "string", "description": "O que pesquisar, de forma específica."}},
         ["consulta"]),
    _def("obter_clima", "Clima atual e previsão de 3 dias de uma cidade.",
         {"cidade": {"type": "string", "description": "Nome da cidade, ex.: Goiânia"}},
         ["cidade"]),
    _def("calcular", "Calcula uma expressão matemática com exatidão.",
         {"expressao": {"type": "string", "description": "Ex.: 15% de 230 -> 230*0.15; sqrt(144)"}},
         ["expressao"]),
    _def("criar_tarefa", "Cria uma tarefa ou lembrete na lista do usuário.",
         {"titulo": {"type": "string"},
          "prazo": {"type": "string", "description": "Data/hora em texto claro, ex.: 2026-10-25 14:00. Opcional."}},
         ["titulo"]),
    _def("listar_tarefas", "Lista as tarefas pendentes do usuário.", {}, []),
    _def("concluir_tarefa", "Marca uma tarefa pendente como concluída, pelo título.",
         {"titulo": {"type": "string", "description": "Trecho do título da tarefa."}},
         ["titulo"]),
    _def("salvar_memoria",
         "Guarda um fato duradouro sobre o usuário (preferência, cidade, rotina) "
         "quando ele pedir para lembrar ou revelar algo que vale manter.",
         {"categoria": {"type": "string", "description": "Ex.: preferência, cidade, rotina, projeto"},
          "conteudo": {"type": "string"}},
         ["categoria", "conteudo"]),
]

_CODIGOS_CLIMA = {
    0: "céu limpo", 1: "predominantemente limpo", 2: "parcialmente nublado",
    3: "nublado", 45: "neblina", 48: "neblina com geada", 51: "garoa leve",
    53: "garoa", 55: "garoa forte", 61: "chuva fraca", 63: "chuva",
    65: "chuva forte", 80: "pancadas leves", 81: "pancadas de chuva",
    82: "pancadas fortes", 95: "trovoadas", 96: "trovoadas com granizo",
    99: "trovoadas fortes com granizo",
}


def _clima(cidade: str) -> str:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": cidade, "count": 1, "language": "pt"}, timeout=8,
    ).json()
    if not geo.get("results"):
        return f"Não encontrei a cidade '{cidade}'."
    local = geo["results"][0]
    dados = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": local["latitude"], "longitude": local["longitude"],
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "precipitation,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "auto", "forecast_days": 3,
        }, timeout=8,
    ).json()
    atual, dia = dados["current"], dados["daily"]
    linhas = [
        f"{local['name']} ({local.get('admin1', '')}): {atual['temperature_2m']}°C "
        f"(sensação {atual['apparent_temperature']}°C), "
        f"{_CODIGOS_CLIMA.get(atual['weather_code'], 'condição desconhecida')}, "
        f"umidade {atual['relative_humidity_2m']}%, vento {atual['wind_speed_10m']} km/h."
    ]
    for i, data in enumerate(dia["time"]):
        linhas.append(
            f"{data}: mín {dia['temperature_2m_min'][i]}°C, máx {dia['temperature_2m_max'][i]}°C, "
            f"chance de chuva {dia['precipitation_probability_max'][i]}%."
        )
    return "\n".join(linhas)


def executar(nome: str, args: dict) -> str:
    """Executa uma ferramenta e devolve texto (nunca levanta exceção)."""
    try:
        if nome == "pesquisar_web":
            from . import llm  # import tardio: llm também importa este módulo
            return llm.pesquisar(args.get("consulta", ""))
        if nome == "obter_clima":
            return _clima(args.get("cidade", ""))
        if nome == "calcular":
            return str(calcular(args.get("expressao", "")))
        if nome == "criar_tarefa":
            ok = tarefas.criar(args.get("titulo", ""), args.get("prazo", ""))
            return "Tarefa criada." if ok else "Falha ao criar a tarefa."
        if nome == "listar_tarefas":
            lista = tarefas.listar(forcar=True)
            if not lista:
                return "Nenhuma tarefa pendente."
            return "\n".join(f"- {t['title']}" + (f" (prazo: {t['due']})" if t.get("due") else "")
                             for t in lista)
        if nome == "concluir_tarefa":
            return tarefas.concluir_por_titulo(args.get("titulo", ""))
        if nome == "salvar_memoria":
            ok = memory.salvar(args.get("categoria", "nota"), args.get("conteudo", ""))
            return "Memória salva." if ok else "Falha ao salvar a memória."
        return f"Ferramenta desconhecida: {nome}"
    except Exception as erro:
        log.error("Erro na ferramenta %s: %s", nome, erro)
        return f"Erro ao executar {nome}: {erro}"
