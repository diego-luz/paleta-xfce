"""Executa os passos de uma receita.

Cada passo e um dicionario com um campo `tipo`. O motor sabe executar uns
poucos tipos bem definidos, e `script` fica como valvula de escape para o que
nao vale a pena descrever em dados.

Todo texto passa por substituicao com o contexto, entao a receita escreve
`@@HOME@@/@@pasta_projetos@@` e o motor resolve.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Iterable

from . import NOME, caminhos, diario, estado, projeto, sistema

Saida = Callable[[str], None]


# --------------------------------------------------------------------------
# contexto: os valores que as receitas podem interpolar
# --------------------------------------------------------------------------

def montar_contexto(cfg: dict[str, str]) -> dict[str, str]:
    """As opcoes, o que vale para todo projeto, e o que o projeto.py calcula."""
    ctx: dict[str, str] = dict(cfg)
    ctx.update({
        "HOME": str(Path.home()),
        "USUARIO": os.environ.get("USER", ""),
        "NOME": NOME,
        "arquivos": str(caminhos.ARQUIVOS),
        "fontes": str(caminhos.FONTES),
        "estado_dir": str(caminhos.ESTADO_DIR),
        # para trocar o que depende de video de verdade, como compositor com glx
        "maquina_virtual": "sim" if sistema.maquina_virtual() else "nao",
    })
    ctx.update({c: str(v) for c, v in projeto.contexto(cfg).items()})
    return ctx


# @@chave@@ em vez de {chave}: as chaves colidiriam com a sintaxe do
# CSS e do shell, que aparecem nos modelos
_CHAVE = re.compile(r"@@([a-zA-Z_][a-zA-Z0-9_]*)@@")


def resolver(valor, ctx: dict[str, str]):
    """Troca @@chave@@ pelo valor do contexto, em textos e dentro de listas."""
    if isinstance(valor, str):
        return _CHAVE.sub(lambda m: str(ctx.get(m.group(1), m.group(0))), valor)
    if isinstance(valor, list):
        return [resolver(x, ctx) for x in valor]
    if isinstance(valor, dict):
        return {c: resolver(v, ctx) for c, v in valor.items()}
    return valor


def condicao_atende(expressao: str, ctx: dict[str, str]) -> bool:
    """Avalia `chave == valor` ou `chave != valor`. Nada alem disso, de proposito."""
    for operador, esperado in ((" != ", False), (" == ", True)):
        if operador in expressao:
            chave, _, alvo = expressao.partition(operador)
            igual = ctx.get(chave.strip(), "") == alvo.strip().strip('"\'')
            return igual is esperado
    return bool(ctx.get(expressao.strip()))


# --------------------------------------------------------------------------
# motor
# --------------------------------------------------------------------------

# arquivo de configuracao mexido pelo usuario: fica o dele, sem perguntar
APT_SEM_PERGUNTAS = ["-o", "Dpkg::Options::=--force-confdef",
                     "-o", "Dpkg::Options::=--force-confold"]

# ref de git com 40 hexadecimais e um commit fixo (ver passo_git)
_COMMIT = re.compile(r"[0-9a-f]{40}")

# Copia como root de uma pasta da pessoa (copiar com root = true). Nunca cp -a
# direto: levaria o dono (a pessoa) para /usr/share ou /etc, e ela poderia
# trocar o arquivo depois. O root copia antes para uma pasta so dele (mktemp
# -d), recusa link simbolico e arquivo especial, tira escrita de outros e
# setuid, e so entao poe no lugar, ja como dono.
INSTALAR_COMO_ROOT = r'''
set -eu
t=$(mktemp -d)
trap 'rm -rf "$t"' EXIT
cp -R -P --no-preserve=ownership -- "$1" "$t/x"
if [ -n "$(find "$t/x" ! -type f ! -type d -print -quit)" ]; then
  echo "recusado: link simbolico ou arquivo especial em $1" >&2
  exit 1
fi
chown -R root:root "$t/x"
chmod -R go-w,u-s,g-s "$t/x"
mkdir -p -- "$(dirname -- "$2")"
rm -rf -- "$2"
mv -T -- "$t/x" "$2"
'''


class ErroDePasso(Exception):
    pass


class Motor:
    def __init__(self, ctx: dict[str, str], saida: Saida | None = None,
                 simular: bool = False, receita: str = "", anotar: bool = True) -> None:
        self.ctx = ctx
        self.simular = simular
        self._saida = saida or (lambda t: None)
        # o diario (diario.py) guarda o que mudou, para o desfazer; a simulacao
        # e o proprio desfazer nao anotam
        self.receita = receita
        self.anotar = anotar and not simular

    def _anotar(self, tipo: str, **dados) -> None:
        if self.anotar:
            diario.anotar(tipo, receita=self.receita, **dados)

    # ---- utilidades ------------------------------------------------------
    def diz(self, texto: str) -> None:
        self._saida(texto)
        estado.registrar(texto)

    def _executa(self, argumentos: list[str], root: bool = False,
                 entrada: str | None = None) -> int:
        if root:
            # o sudo limpa o ambiente: o DEBIAN_FRONTEND precisa ir por dentro,
            # senao um pacote com pergunta (debconf) espera para sempre
            argumentos = ["sudo", "-n", "env", "DEBIAN_FRONTEND=noninteractive", *argumentos]
        if self.simular:
            self.diz("  [simulacao] " + " ".join(shlex.quote(a) for a in argumentos))
            return 0
        estado.registrar("+ " + " ".join(shlex.quote(a) for a in argumentos))
        try:
            proc = subprocess.run(
                argumentos, input=entrada, capture_output=True, text=True,
                # sem entrada, nada pode ficar esperando o teclado
                stdin=subprocess.DEVNULL if entrada is None else None,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive", "TERM": "dumb"},
            )
        except OSError as erro:
            raise ErroDePasso(f"nao consegui executar {argumentos[0]}: {erro}") from erro
        for linha in (proc.stdout or "").splitlines():
            estado.registrar("  " + linha)
        if proc.returncode != 0:
            for linha in (proc.stderr or "").splitlines()[-8:]:
                self.diz("  " + linha)
        return proc.returncode

    def _caminho(self, bruto: str) -> Path:
        return Path(resolver(bruto, self.ctx)).expanduser()

    # ---- passos ----------------------------------------------------------
    def passo_apt(self, p: dict) -> None:
        pedidos = [x for x in resolver(p.get("pacotes", []), self.ctx) if x]
        faltam, inexistentes = [], []
        estados = sistema.estado_pacotes(pedidos)
        for nome in pedidos:
            info = estados.get(nome, {})
            if info.get("instalado"):
                continue
            (faltam if info.get("disponivel") else inexistentes).append(nome)
        if inexistentes:
            self.diz(f"  nao existem no repositorio, ignorados: {', '.join(inexistentes)}")
        if not faltam:
            self.diz("  pacotes ja presentes")
            return
        self.diz(f"  instalando: {', '.join(faltam)}")
        antes = sistema.pacotes_instalados()
        codigo = self._executa(["apt-get", *APT_SEM_PERGUNTAS, "install", "-y",
                                "--no-install-recommends", *faltam], root=True)
        if codigo != 0:
            raise ErroDePasso(f"apt-get falhou ao instalar {', '.join(faltam)}")
        # so os que faltavam: o que ja existia na maquina nunca entra no remover.
        # As dependencias que vieram junto tambem ficam anotadas: o autoremove do
        # Debian guarda as que outro pacote so sugere, e elas sobrariam
        vieram = sorted(sistema.pacotes_instalados() - antes - set(faltam)) if antes else []
        self._anotar("pacotes", nomes=faltam, dependencias=vieram)

    def passo_xfconf(self, p: dict) -> None:
        """Propriedade do XFCE. So faz sentido em projeto de desktop XFCE."""
        canal = resolver(p["canal"], self.ctx)
        chave = resolver(p["chave"], self.ctx)
        # "tipo" ja e o tipo do passo; o tipo do valor do xfconf vem em
        # "tipo_valor", senao um sobrescreve o outro
        tipo = p.get("tipo_valor", "string")
        valor = resolver(p["valor"], self.ctx)
        if self.anotar and shutil.which("xfconf-query"):
            # o valor de antes, para o desfazer devolver; sem ele a propriedade some
            antes = subprocess.run(["xfconf-query", "-c", canal, "-p", chave],
                                   capture_output=True, text=True, env={**os.environ, "LC_ALL": "C"})
            self._anotar("xfconf", canal=canal, chave=chave, existia=antes.returncode == 0,
                         valor=antes.stdout, tipo_valor=tipo)
        valores = valor.split() if tipo == "double-array" else [str(valor)]
        tipos = ["double"] * len(valores) if tipo == "double-array" else [tipo]
        args = ["xfconf-query", "-c", canal, "-p", chave]
        for t in tipos:
            args += ["-t", t]
        for v in valores:
            args += ["-s", v]
        if self._executa([*args, "-n"]) != 0 and self._executa(args) != 0:
            # a propriedade pode existir com outro tipo; recria
            self._executa(["xfconf-query", "-c", canal, "-p", chave, "-r"])
            if self._executa([*args, "-n"]) != 0:
                self.diz(f"  nao consegui definir {canal}{chave}")

    def passo_arquivo(self, p: dict) -> None:
        destino = self._caminho(p["destino"])
        if p.get("modelo"):
            origem = caminhos.ARQUIVOS / resolver(p["modelo"], self.ctx)
            try:
                conteudo = origem.read_text()
            except OSError as erro:
                raise ErroDePasso(f"modelo ausente: {origem}") from erro
        else:
            conteudo = p.get("conteudo", "")
        conteudo = resolver(conteudo, self.ctx)
        existia = destino.exists()
        if self.simular:
            self.diz(f"  [simulacao] escreveria {destino}")
            return
        estado.copia_de_seguranca(destino)
        caminhos.escrever(destino, conteudo, int(str(p["modo"]), 8) if p.get("modo") else None)
        self._anotar("alterado" if existia else "criado", caminho=str(destino))
        self.diz(f"  escrito {destino}")

    def passo_bloco(self, p: dict) -> None:
        """Insere ou troca um trecho marcado dentro de um arquivo existente."""
        destino = self._caminho(p["destino"])
        marca = resolver(p.get("marca", NOME), self.ctx)
        conteudo = resolver(p.get("conteudo", ""), self.ctx)
        abre, fecha = f"/* {marca} */", f"/* fim {marca} */"
        if p.get("comentario") == "#":
            abre, fecha = f"# {marca}", f"# fim {marca}"
        if self.simular:
            self.diz(f"  [simulacao] bloco '{marca}' em {destino}")
            return
        estado.copia_de_seguranca(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        existia = destino.exists()
        texto = destino.read_text() if existia else ""
        # marcas ancoradas na linha inteira: "# fim x" nao pode casar dentro do
        # bloco de outro projeto com nome parecido no mesmo arquivo
        texto = re.sub(r"^" + re.escape(abre) + r"$.*?^" + re.escape(fecha) + r"$", "", texto,
                       flags=re.S | re.M)
        texto = texto.rstrip() + f"\n\n{abre}\n{conteudo.strip()}\n{fecha}\n"
        caminhos.escrever(destino, texto)
        # so o bloco sai no desfazer; o que a pessoa escreveu no arquivo depois fica
        self._anotar("bloco", caminho=str(destino), marca=marca,
                     comentario=p.get("comentario", ""), arquivo_novo=not existia)
        self.diz(f"  bloco '{marca}' em {destino}")

    def passo_git(self, p: dict) -> None:
        """Clona ou atualiza um repositorio num commit exato (40 hex), conferido.

        So commit fixo: um ramo (main, master, HEAD) mudaria por baixo do
        projeto, e o que roda tem de ser sempre o que foi conferido. Para
        atualizar, pegue o commit novo com `git ls-remote URL HEAD`, leia o que
        mudou e troque o ref. O git roda sem os hooks do clone (que ficam numa
        pasta do usuario) e sem perguntar nada no terminal; o resultado tem de
        ser exatamente o commit pedido, com a arvore limpa, senao o passo falha
        em vez de seguir com o que estava la.
        """
        destino = self._caminho(p["destino"])
        url = resolver(p["url"], self.ctx)
        ref = resolver(p.get("ref", ""), self.ctx)
        if not _COMMIT.fullmatch(ref):
            raise ErroDePasso(f"repositorio sem commit fixo (ref = {ref or 'vazio'}): {url}")
        if self.simular:
            self.diz(f"  [simulacao] buscaria {url} no commit {ref[:12]} em {destino}")
            return
        git = ["env", "GIT_TERMINAL_PROMPT=0", "git", "-c", "core.hooksPath=/dev/null", "-C", str(destino)]
        novo = not (destino / ".git").is_dir()
        if novo:
            self.diz(f"  clonando {destino.name} em {ref[:12]}")
            # sobra de uma tentativa anterior (sem .git): comeca do zero
            if destino.is_symlink():
                destino.unlink()
            elif destino.exists():
                shutil.rmtree(destino, ignore_errors=True)
            destino.mkdir(parents=True)
            if self._executa([*git, "init", "-q"]) != 0:
                raise ErroDePasso(f"nao consegui criar {destino}")
            self._anotar("criado", caminho=str(destino))
            self._executa([*git, "remote", "add", "origin", url])
        else:
            self.diz(f"  atualizando {destino.name} para {ref[:12]}")
            self._executa([*git, "remote", "set-url", "origin", url])
        if self._executa([*git, "fetch", "-q", "--depth", "1", "origin", ref]) != 0:
            raise ErroDePasso(f"nao consegui buscar {url} no commit {ref[:12]}")
        if self._executa([*git, "checkout", "-q", "-f", "--detach", "FETCH_HEAD"]) != 0:
            raise ErroDePasso(f"nao consegui usar o commit {ref[:12]} de {url}")
        if self._executa([*git, "clean", "-q", "-ffdx"]) != 0:
            raise ErroDePasso(f"nao consegui limpar {destino}")
        atual = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True,
                               stdin=subprocess.DEVNULL).stdout.strip()
        sujo = subprocess.run([*git, "status", "--porcelain", "--ignored"], capture_output=True,
                              text=True, stdin=subprocess.DEVNULL).stdout.strip()
        if atual != ref or sujo:
            raise ErroDePasso(f"{destino.name} nao ficou no commit {ref[:12]} com a arvore limpa")

    def passo_comando(self, p: dict) -> None:
        argumentos = [str(x) for x in resolver(p["argumentos"], self.ctx)]
        codigo = self._executa(argumentos, root=bool(p.get("root")))
        if codigo != 0 and not p.get("tolera_falha"):
            raise ErroDePasso(f"comando falhou ({codigo}): {' '.join(argumentos)}")

    def passo_script(self, p: dict) -> None:
        """Trecho de shell. Usado onde descrever em dados custaria mais que ajudar.

        O contexto chega tambem como variaveis CTX_*, entao o trecho pode usar
        "$CTX_HOME" em vez de @@HOME@@ quando isso ler melhor.
        """
        corpo = resolver(p["corpo"], self.ctx)
        if self.simular:
            self.diz("  [simulacao] rodaria um trecho de shell")
            return
        # sem TERM, instaladores que mexem no terminal (setterm, tput) param com
        # erro; e o que acontece com o painel aberto pelo menu, fora de um terminal
        ambiente = {**os.environ, "DEBIAN_FRONTEND": "noninteractive",
                    "TERM": os.environ.get("TERM") or "dumb"}
        for chave, valor in self.ctx.items():
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", chave):
                ambiente[f"CTX_{chave.upper()}"] = str(valor)
        # as funcoes d3_antes, d3_gsettings... que anotam no diario (ver diario.py)
        ambiente.update(diario.ambiente_shell(self.receita, self.anotar))
        # so o trecho que chama o sudo ele mesmo usa a senha ja confirmada (que
        # vale para este terminal); os outros rodam fora dele, numa sessao nova,
        # entao um instalador de terceiros que tente "sudo" por conta propria falha
        usa_sudo = re.search(r"\bsudo\b", corpo) is not None
        if not usa_sudo:
            ambiente["SUDO_ASKPASS"] = "/bin/false"
        estado.registrar("+ shell:\n" + corpo)
        proc = subprocess.run(["bash", "-euo", "pipefail", "-c", diario.FUNCOES_SHELL + corpo],
                              capture_output=True, text=True, env=ambiente,
                              stdin=subprocess.DEVNULL, start_new_session=not usa_sudo)
        for linha in (proc.stdout or "").splitlines():
            self.diz("  " + linha)
        if proc.returncode != 0:
            for linha in (proc.stderr or "").splitlines()[-10:]:
                self.diz("  " + linha)
            if not p.get("tolera_falha"):
                raise ErroDePasso(f"o trecho de shell falhou ({proc.returncode})")

    def passo_copiar(self, p: dict) -> None:
        origem = self._caminho(p["origem"])
        destino = self._caminho(p["destino"])
        if not origem.exists():
            # na simulacao o passo git nao clona, entao a origem pode so faltar ainda
            if self.simular:
                self.diz(f"  [simulacao] copiaria {origem} para {destino} (origem ainda nao existe)")
                return
            if p.get("tolera_falha"):
                self.diz(f"  origem ausente, ignorando: {origem}")
                return
            raise ErroDePasso(f"origem nao existe: {origem}")
        if self.simular:
            self.diz(f"  [simulacao] copiaria {origem} para {destino}")
            return
        existia = destino.exists()
        if existia:
            estado.copia_de_seguranca(destino)
        if p.get("root"):
            if self._executa(["sh", "-c", INSTALAR_COMO_ROOT, "_", str(origem), str(destino)],
                             root=True) != 0:
                raise ErroDePasso(f"nao consegui copiar para {destino}")
        else:
            destino.parent.mkdir(parents=True, exist_ok=True)
            if destino.exists() and destino.is_dir():
                shutil.rmtree(destino, ignore_errors=True)
            if origem.is_dir():
                shutil.copytree(origem, destino, symlinks=True, dirs_exist_ok=True)
            else:
                shutil.copy2(origem, destino)
        self._anotar("alterado" if existia else "criado", caminho=str(destino))
        self.diz(f"  copiado para {destino}")

    def passo_autostart(self, p: dict) -> None:
        ident = resolver(p["id"], self.ctx)
        arquivo = Path.home() / ".config/autostart" / f"{ident}.desktop"
        if p.get("remover"):
            if not self.simular and arquivo.exists():
                estado.copia_de_seguranca(arquivo)
                arquivo.unlink()
                self._anotar("alterado", caminho=str(arquivo))
            self.diz(f"  inicializacao automatica removida: {ident}")
            return
        conteudo = (
            "[Desktop Entry]\nType=Application\n"
            f"Name={resolver(p.get('nome', ident), self.ctx)}\n"
            f"Exec={resolver(p['comando'], self.ctx)}\n"
            "Terminal=false\nX-GNOME-Autostart-enabled=true\n"
            f"X-GNOME-Autostart-Delay={p.get('atraso', 3)}\n"
        )
        if self.simular:
            self.diz(f"  [simulacao] inicializacao automatica: {ident}")
            return
        existia = arquivo.exists()
        estado.copia_de_seguranca(arquivo)
        caminhos.escrever(arquivo, conteudo)
        self._anotar("alterado" if existia else "criado", caminho=str(arquivo))
        self.diz(f"  inicializacao automatica: {ident}")

    def passo_processo(self, p: dict) -> None:
        """Para, inicia ou reinicia um programa da sessao grafica."""
        nome = resolver(p["nome"], self.ctx)
        acao = p.get("acao", "reiniciar")
        if self.simular:
            self.diz(f"  [simulacao] {acao} {nome}")
            return
        if acao in ("parar", "reiniciar"):
            subprocess.run(["pkill", "-x", nome], capture_output=True)
        if acao in ("iniciar", "reiniciar"):
            argumentos = [str(x) for x in resolver(p.get("argumentos", [nome]), self.ctx)]
            try:
                subprocess.Popen(["setsid", "--fork", *argumentos],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 stdin=subprocess.DEVNULL, start_new_session=True)
            except OSError as erro:
                self.diz(f"  nao consegui iniciar {nome}: {erro}")
                return
        self.diz(f"  {acao}: {nome}")

    def passo_backup(self, p: dict) -> None:
        for bruto in resolver(p.get("caminhos", []), self.ctx):
            # simular nao pode escrever nada, nem copia de seguranca
            if self.simular:
                self.diz(f"  [simulacao] guardaria copia de {bruto}")
                continue
            if estado.copia_de_seguranca(Path(bruto).expanduser()):
                self.diz(f"  guardado: {bruto}")

    # ---- despacho --------------------------------------------------------
    TIPOS = {
        "apt": passo_apt, "xfconf": passo_xfconf, "arquivo": passo_arquivo,
        "bloco": passo_bloco, "git": passo_git, "comando": passo_comando,
        "script": passo_script, "copiar": passo_copiar,
        "autostart": passo_autostart, "processo": passo_processo,
        "backup": passo_backup,
    }

    def rodar(self, passos: Iterable[dict]) -> None:
        for passo in passos:
            tipo = passo.get("tipo")
            funcao = self.TIPOS.get(tipo)
            if funcao is None:
                raise ErroDePasso(f"tipo de passo desconhecido: {tipo}")
            condicao = passo.get("se")
            if condicao and not condicao_atende(str(condicao), self.ctx):
                continue
            if passo.get("dizer"):
                self.diz(resolver(passo["dizer"], self.ctx))
            funcao(self, passo)
