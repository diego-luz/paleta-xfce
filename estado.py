"""O que ja foi aplicado, o registro e as copias de seguranca."""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import subprocess
from pathlib import Path

from . import caminhos


def _agora() -> str:
    return _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")


def registrar(texto: str) -> None:
    caminhos.preparar()
    try:
        with caminhos.REGISTRO.open("a", encoding="utf-8") as arq:
            arq.write(f"[{_agora()}] {texto}\n")
    except OSError:
        pass


def marca(ident: str) -> Path:
    return caminhos.APLICADO / ident


def aplicado(ident: str) -> bool:
    return marca(ident).is_file()


def quando(ident: str) -> str:
    try:
        return marca(ident).read_text().strip()
    except OSError:
        return ""


def marcar(ident: str) -> None:
    caminhos.preparar()
    try:
        caminhos.escrever(marca(ident), _agora() + "\n")
    except OSError:
        pass


def desmarcar(ident: str) -> None:
    marca(ident).unlink(missing_ok=True)


def limpar_marcas() -> None:
    for arquivo in caminhos.APLICADO.glob("*"):
        arquivo.unlink(missing_ok=True)


def copia_de_seguranca(alvo: Path) -> bool:
    """Guarda o arquivo ou pasta antes de mexer, preservando a arvore.

    So guarda a primeira versao: o objetivo e poder voltar ao estado anterior
    ao programa, nao ter historico de cada execucao.
    """
    # normalizado: um ".." no caminho faria a copia cair fora da pasta de copias
    alvo = Path(os.path.abspath(Path(alvo).expanduser()))
    if not alvo.exists():
        return False
    if not da_pessoa(alvo):
        return _copia_do_sistema(alvo)
    destino = caminhos.BACKUP / str(alvo).lstrip("/")
    if destino.exists():
        return True
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        if alvo.is_dir():
            shutil.copytree(alvo, destino, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(alvo, destino)
        registrar(f"copia de seguranca: {alvo}")
        return True
    except (OSError, shutil.Error) as erro:
        registrar(f"falhou a copia de {alvo}: {erro}")
        return False


def da_pessoa(caminho: Path) -> bool:
    return caminho == Path.home() or caminho.is_relative_to(Path.home())


def copia_do_sistema(alvo: Path) -> Path:
    """Onde fica a copia (do root) de um arquivo do sistema. So caminho
    absoluto e normalizado: com ".." a copia sairia da pasta das copias."""
    bruto = str(alvo)
    if not bruto.startswith("/") or bruto.startswith("//") or os.path.normpath(bruto) != bruto:
        raise ValueError(f"caminho invalido para copia do sistema: {bruto}")
    return caminhos.BACKUP_SISTEMA / bruto.lstrip("/")


def _sudo(*argumentos: str) -> bool:
    try:
        return subprocess.run(["sudo", "-n", *argumentos], capture_output=True,
                              stdin=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def _copia_do_sistema(alvo: Path) -> bool:
    """Arquivo fora da casa: a copia vai para a pasta do root (0700), e so dali
    o desfazer devolve. Uma copia na pasta da pessoa poderia ser trocada por
    ela antes de o root a por de volta em /etc."""
    try:
        destino = copia_do_sistema(alvo)
    except ValueError as erro:
        registrar(str(erro))
        return False
    if _sudo("test", "-e", str(destino)):
        return True
    ok = (_sudo("install", "-d", "-m", "0700", "-o", "root", "-g", "root", str(caminhos.BACKUP_SISTEMA))
          and _sudo("mkdir", "-p", str(destino.parent))
          and _sudo("cp", "-a", str(alvo), str(destino)))
    registrar(f"copia de seguranca (root): {alvo}" if ok else f"falhou a copia (root) de {alvo}")
    return ok


def restaurar_tudo() -> list[str]:
    """Devolve os arquivos guardados para o lugar. Retorna o que foi restaurado."""
    feitos: list[str] = []
    raiz = caminhos.BACKUP
    if not raiz.is_dir():
        return feitos
    for origem in sorted(raiz.rglob("*")):
        if origem.is_dir():
            continue
        destino = Path("/") / origem.relative_to(raiz)
        # daqui (pasta da pessoa) so volta o que e da pessoa; o do sistema mora
        # na copia do root
        if not da_pessoa(destino):
            continue
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)
            feitos.append(str(destino))
        except OSError as erro:
            registrar(f"nao consegui restaurar {destino}: {erro}")
    return feitos
