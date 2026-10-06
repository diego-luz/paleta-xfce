"""Preferencias do usuario.

As opcoes sao descritas em recursos/opcoes.toml, e nao em codigo: um projeto
novo muda o que oferece sem tocar em Python. Os valores escolhidos ficam num
unico arquivo JSON, validados contra essa tabela. A validacao serve tanto
para o terminal quanto para a pagina web: qualquer valor que nao esteja na
tabela e recusado antes de chegar ao motor.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import Any

from . import caminhos, estado


class Opcao:
    """Uma preferencia: o que ela aceita, o padrao e para que serve."""

    def __init__(self, chave: str, padrao: str, valores: tuple[str, ...],
                 titulo: str, ajuda: str = "", livre: str = "", grupo: str = "",
                 nomes: dict[str, str] | None = None,
                 exemplos: dict[str, str] | None = None) -> None:
        self.chave = chave
        self.padrao = padrao
        self.valores = valores
        self.titulo = titulo
        self.ajuda = ajuda
        # expressao que descreve os valores aceitos alem da lista; vazia
        # significa que so a lista vale
        self.livre = livre
        self.grupo = grupo
        # rotulo de cada valor na pagina, e imagem de exemplo por valor
        self.nomes = nomes or {}
        self.exemplos = exemplos or {}

    def valida(self, valor: Any) -> bool:
        if not isinstance(valor, str) or not valor:
            return False
        if valor in self.valores:
            return True
        return bool(self.livre) and bool(re.fullmatch(self.livre, valor))

    def como_dict(self) -> dict:
        return {"chave": self.chave, "padrao": self.padrao,
                "valores": list(self.valores), "titulo": self.titulo,
                "ajuda": self.ajuda, "livre": self.livre, "grupo": self.grupo,
                "nomes": self.nomes, "exemplos": self.exemplos}


def _texto(tabela: Any) -> dict[str, str]:
    return {str(c): str(v) for c, v in tabela.items()} if isinstance(tabela, dict) else {}


def _carregar() -> tuple[Opcao, ...]:
    try:
        dados = tomllib.loads(caminhos.OPCOES.read_text())
    except (OSError, tomllib.TOMLDecodeError) as erro:
        # sem opcoes o painel ainda abre; so nao ha o que ajustar
        estado.registrar(f"opcoes invalidas em {caminhos.OPCOES.name}: {erro}")
        return ()
    saida: list[Opcao] = []
    for bruto in dados.get("opcao", []):
        chave = str(bruto.get("chave", ""))
        valores = tuple(str(v) for v in bruto.get("valores", []))
        padrao = str(bruto.get("padrao", valores[0] if valores else ""))
        opcao = Opcao(chave, padrao, valores, str(bruto.get("titulo", chave)),
                      ajuda=str(bruto.get("ajuda", "")), livre=str(bruto.get("livre", "")),
                      grupo=str(bruto.get("grupo", "")), nomes=_texto(bruto.get("nomes")),
                      exemplos=_texto(bruto.get("exemplos")))
        # a chave vira @@chave@@ nas receitas e variavel de ambiente nos scripts
        if not re.fullmatch(r"[a-z_][a-z0-9_]*", chave) or not opcao.valida(padrao):
            estado.registrar(f"opcao ignorada, chave ou padrao invalido: {chave!r}")
            continue
        saida.append(opcao)
    return tuple(saida)


OPCOES: tuple[Opcao, ...] = _carregar()

POR_CHAVE = {o.chave: o for o in OPCOES}


def padroes() -> dict[str, str]:
    return {o.chave: o.padrao for o in OPCOES}


def ler() -> dict[str, str]:
    """Config do usuario por cima dos padroes, ignorando lixo."""
    valores = padroes()
    try:
        salvo = json.loads(caminhos.CONFIG.read_text())
    except (OSError, json.JSONDecodeError):
        return valores
    if not isinstance(salvo, dict):
        return valores
    for chave, valor in salvo.items():
        opcao = POR_CHAVE.get(chave)
        if opcao and opcao.valida(valor):
            valores[chave] = valor
    return valores


def gravar(novos: dict[str, Any]) -> list[str]:
    """Grava so o que e valido e mudou. Devolve as chaves alteradas."""
    atual = ler()
    mudou = []
    for chave, valor in novos.items():
        opcao = POR_CHAVE.get(chave)
        if opcao and opcao.valida(valor) and atual.get(chave) != valor:
            atual[chave] = valor
            mudou.append(chave)
    if mudou:
        caminhos.preparar()
        caminhos.escrever(caminhos.CONFIG, json.dumps(atual, ensure_ascii=False, indent=2) + "\n")
    return mudou


def filtrar(bruto: dict[str, Any]) -> dict[str, str]:
    """So as chaves conhecidas e com valor aceito."""
    return {c: v for c, v in bruto.items()
            if c in POR_CHAVE and POR_CHAVE[c].valida(v)}
