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
    # log, diario e copias de seguranca podem ter caminhos e variaveis da
    # pessoa: so ela le
    for pasta in (ESTADO_DIR, BACKUP):
        os.chmod(pasta, 0o700)


# copias de arquivos do sistema (de root) ficam numa pasta do root: a pasta de
# copias da pessoa e gravavel por ela, e o que o root devolve dali viraria um
# atalho para mudar qualquer arquivo do sistema
BACKUP_SISTEMA = Path("/var/backups") / NOME


def proteger_codigo() -> None:
    """Tira a escrita de grupo e de outros do proprio codigo. Parte dele roda
    com sudo; um arquivo que outra conta pudesse mudar viraria um atalho para
    o root. So mexe no que e da pessoa."""
    uid = os.getuid()
    for raiz, pastas, arquivos in os.walk(PACOTE):
        for nome in [*pastas, *arquivos]:
            caminho = os.path.join(raiz, nome)
            try:
                info = os.lstat(caminho)
            except OSError:
                continue
            if info.st_uid == uid and info.st_mode & 0o022 and not os.path.islink(caminho):
                os.chmod(caminho, info.st_mode & ~0o022)


def escrever(destino: Path, texto: str, modo: int | None = None) -> None:
    """Grava inteiro ou nada: um corte no meio (queda de energia, Ctrl+C) nao
    deixa o .bashrc pela metade. Mantem a permissao do arquivo que existia."""
    import tempfile
    destino.parent.mkdir(parents=True, exist_ok=True)
    if modo is None:
        try:
            modo = destino.stat().st_mode & 0o7777
        except OSError:
            modo = 0o644
    fd, temp = tempfile.mkstemp(dir=destino.parent, prefix=f".{destino.name}.")
    try:
        with os.fdopen(fd, "w") as arquivo:
            arquivo.write(texto)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.chmod(temp, modo)
        os.replace(temp, destino)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


class Ocupado(RuntimeError):
    """Outra execucao (o painel ou a linha de comando) ja esta mexendo."""


class trava:
    """Uma execucao por vez entre processos: o painel e a linha de comando
    rodando juntos brigariam pelo apt e pelos mesmos arquivos."""

    def __enter__(self):
        import fcntl
        preparar()
        self._arquivo = open(ESTADO_DIR / "trava", "w")
        try:
            fcntl.flock(self._arquivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._arquivo.close()
            raise Ocupado("outra execucao deste projeto ja esta rodando") from None
        return self

    def __exit__(self, *_a) -> None:
        self._arquivo.close()
