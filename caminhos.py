"""Onde cada coisa mora.

Segue o padrao XDG, entao nada fica espalhado pela pasta pessoal. Os recursos
do programa (receitas, paginas, arquivos modelo) vem de dentro do proprio
pacote, o que permite rodar direto do codigo-fonte ou instalado, sem mudar
nada.
"""

from __future__ import annotations

import os
from pathlib import Path

from . import NOME

PACOTE = Path(__file__).resolve().parent
RECURSOS = PACOTE / "recursos"
RECEITAS = RECURSOS / "receitas"
WEB = RECURSOS / "web"
ARQUIVOS = RECURSOS / "arquivos"
CATALOGO = RECURSOS / "programas.json"
OPCOES = RECURSOS / "opcoes.toml"


def _xdg(variavel: str, padrao: str) -> Path:
    bruto = os.environ.get(variavel, "").strip()
    base = Path(bruto) if bruto.startswith("/") else Path.home() / padrao
    return base


CONFIG_DIR = _xdg("XDG_CONFIG_HOME", ".config") / NOME
ESTADO_DIR = _xdg("XDG_STATE_HOME", ".local/state") / NOME
DADOS_DIR = _xdg("XDG_DATA_HOME", ".local/share") / NOME

CONFIG = CONFIG_DIR / "config.json"
REGISTRO = ESTADO_DIR / "registro.log"
APLICADO = ESTADO_DIR / "aplicado"
BACKUP = ESTADO_DIR / "backup"
FONTES = DADOS_DIR / "fontes"          # repositorios clonados


def preparar() -> None:
    """Cria as pastas de trabalho. Barato, pode chamar sempre."""
    for pasta in (CONFIG_DIR, ESTADO_DIR, APLICADO, BACKUP, DADOS_DIR, FONTES):
        pasta.mkdir(parents=True, exist_ok=True)
