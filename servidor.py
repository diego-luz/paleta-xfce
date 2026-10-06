"""Painel web local.

Escuta so em 127.0.0.1. Ele executa coisas na maquina, entao nao deve ficar
acessivel pela rede. Quem quiser usar de outro computador que faca tunel SSH.
"""

from __future__ import annotations

import html
import json
import signal
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import (DESCRICAO, NOME, PORTA, VERSAO, caminhos, config, programas,
               receitas, sistema)
from .tarefa import Tarefa

TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png", ".svg": "image/svg+xml",
    ".ico": "image/x-icon", ".woff2": "font/woff2",
}

# as paginas escrevem @@NOME@@ e o servidor troca ao entregar, do mesmo jeito
# que o motor faz nas receitas; assim a identidade mora so no __init__.py
IDENTIDADE = {"@@NOME@@": NOME, "@@VERSAO@@": VERSAO, "@@DESCRICAO@@": DESCRICAO}

tarefa = Tarefa()
parar = threading.Event()


class Painel(BaseHTTPRequestHandler):
    server_version = NOME

    def log_message(self, *_a) -> None:
        pass

    # ---- respostas -------------------------------------------------------
    def _envia(self, codigo: int, corpo: bytes, tipo: str) -> None:
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(corpo)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, dados: dict, codigo: int = 200) -> None:
        self._envia(codigo, json.dumps(dados, ensure_ascii=False).encode(),
                    "application/json; charset=utf-8")

    def corpo(self) -> dict:
        try:
            tamanho = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if tamanho <= 0 or tamanho > 64_000:
            return {}
        try:
            dados = json.loads(self.rfile.read(tamanho))
        except (json.JSONDecodeError, OSError):
            return {}
        return dados if isinstance(dados, dict) else {}

    def arquivo(self, alvo: Path) -> None:
        if not alvo.is_file():
            self._envia(404, b"nao encontrado", "text/plain; charset=utf-8")
            return
        corpo = alvo.read_bytes()
        if alvo.suffix.lower() == ".html":
            texto = corpo.decode("utf-8")
            for marca, valor in IDENTIDADE.items():
                texto = texto.replace(marca, html.escape(valor))
            corpo = texto.encode("utf-8")
        self._envia(200, corpo, TIPOS.get(alvo.suffix.lower(), "application/octet-stream"))

    # ---- GET -------------------------------------------------------------
    def do_GET(self) -> None:
        rota = self.path.split("?")[0]
        if rota == "/":
            rota = "/index.html"

        if rota == "/api/projeto":
            self.json({"nome": NOME, "versao": VERSAO, "descricao": DESCRICAO,
                       "host": sistema.distribuicao().get("PRETTY_NAME", ""),
                       "ambiente": sistema.desktop()})
            return

        if rota == "/api/estado":
            lista = receitas.carregar()
            self.json({
                "config": config.ler(),
                "opcoes": [o.como_dict() for o in config.OPCOES],
                "receitas": [r.como_dict() for r in lista],
                "instalado": receitas.instalado(lista),
            })
            return

        if rota == "/api/verificacoes":
            lista = sistema.verificacoes()
            self.json({"verificacoes": lista, "impedimentos": sistema.impedimentos(lista)})
            return

        if rota == "/api/desfazer/previa":
            from . import desfazer
            self.json(desfazer.previa_remocao())
            return

        if rota == "/api/progresso":
            try:
                desde = int(self.path.split("desde=")[1].split("&")[0])
            except (IndexError, ValueError):
                desde = 0
            self.json(tarefa.instantaneo(desde))
            return

        if rota == "/api/programas":
            self.json(programas.com_estado())
            return

        alvo = (caminhos.WEB / rota.lstrip("/")).resolve()
        if not str(alvo).startswith(str(caminhos.WEB.resolve())):
            self._envia(404, b"nao encontrado", "text/plain; charset=utf-8")
            return
        self.arquivo(alvo)

    # ---- POST ------------------------------------------------------------
    def do_POST(self) -> None:
        rota = self.path.split("?")[0]
        corpo = self.corpo()

        if rota == "/api/sair":
            self.json({"tchau": True})
            threading.Timer(0.4, parar.set).start()
            return

        if tarefa.ocupada() and rota != "/api/progresso":
            self.json({"iniciado": False, "motivo": "ocupado",
                       "detalhe": tarefa.rotulo}, 409)
            return

        if rota == "/api/aplicar":
            self._aplicar(corpo)
            return
        if rota == "/api/instalar":
            self._instalar_tudo(corpo)
            return
        if rota == "/api/desfazer":
            from . import desfazer
            apagar = bool(corpo.get("apagar"))
            iniciado = tarefa.funcao("Desfazendo" + (" e apagando" if apagar else ""),
                                     lambda diz: desfazer.executar(diz, apagar))
            self.json({"iniciado": iniciado, "motivo": "" if iniciado else "ocupado",
                       "etapas": [{"id": i, "nome": n} for i, n in desfazer.etapas(apagar)]},
                      200 if iniciado else 409)
            return
        if rota == "/api/programas/instalar":
            self._programas(corpo, remover=False)
            return
        if rota == "/api/programas/remover":
            self._programas(corpo, remover=True)
            return

        self._envia(404, b"nao encontrado", "text/plain; charset=utf-8")

    # ---- acoes -----------------------------------------------------------
    def _aplicar(self, corpo: dict) -> None:
        pedido = config.filtrar(corpo)
        if not pedido:
            self.json({"iniciado": False, "motivo": "nada valido"}, 400)
            return
        atual = config.ler()
        mudou = [c for c, v in pedido.items() if atual.get(c) != v]
        # sem diferenca, reaplica o conjunto: o botao sempre faz alguma coisa
        chaves = mudou or list(pedido)
        # receita que mudou depois de aplicada entra mesmo sem opcao alterada,
        # senao a versao nova dela nunca sairia do codigo
        pendentes = set(receitas.afetadas_por(list(pedido))) & receitas.desatualizadas()
        alvos = sorted(set(receitas.afetadas_por(chaves)) | pendentes,
                       key=lambda x: (len(x), x))
        if not alvos:
            # nenhuma receita depende dessas opcoes; guarda assim mesmo, senao
            # a escolha se perderia ao recarregar a pagina
            self.json({"iniciado": False, "motivo": "nada a fazer",
                       "gravou": config.gravar(pedido)})
            return

        novidade = bool(mudou or pendentes)
        rotulo = ("Aplicando" if novidade else "Reaplicando") + ": " + ", ".join(alvos)
        iniciado = tarefa.funcao(
            rotulo,
            lambda diz: receitas.executar(apenas=alvos, refazer=True, saida=diz,
                                          cfg={**atual, **pedido}),
        )
        if not iniciado:
            self.json({"iniciado": False, "motivo": "ocupado"}, 409)
            return
        # so grava depois que a execucao comecou, senao a config passaria a
        # dizer que algo foi aplicado sem ter sido
        config.gravar(pedido)
        self.json({"iniciado": True, "receitas": alvos, "mudou": mudou,
                   "reaplicou": not novidade})

    def _instalar_tudo(self, corpo: dict) -> None:
        impedem = sistema.impedimentos(sistema.verificacoes(usar_cache=False))
        if impedem:
            self.json({"iniciado": False, "motivo": "verificacoes",
                       "impedimentos": impedem}, 412)
            return
        pedido = config.filtrar(corpo)
        iniciado = tarefa.funcao(
            "Instalacao completa",
            lambda diz: receitas.executar(saida=diz, cfg={**config.ler(), **pedido}),
        )
        if not iniciado:
            self.json({"iniciado": False, "motivo": "ocupado"}, 409)
            return
        if pedido:
            config.gravar(pedido)
        self.json({"iniciado": True})

    def _programas(self, corpo: dict, remover: bool) -> None:
        try:
            escolhidos = programas.conferir(corpo.get("pacotes"))
        except programas.Recusado as erro:
            self.json({"iniciado": False, "erro": str(erro)}, 400)
            return
        externas = [] if remover else programas.fontes_necessarias(escolhidos)
        if externas and not corpo.get("confirmar_externo"):
            # nada e instalado antes de o usuario ver o que sera acrescentado
            # ao sistema; esta pergunta e separada da confirmacao de remocao
            self.json({"iniciado": False, "motivo": "fonte_externa",
                       "externas": externas})
            return

        if remover:
            extras = programas.arrastaria(escolhidos)
            if extras and not corpo.get("confirmar"):
                self.json({"iniciado": False, "motivo": "arrasta_outros",
                           "extras": extras})
                return
            comando = programas.comando_remover(escolhidos)
            rotulo = "Removendo: " + ", ".join(escolhidos)
            iniciado = tarefa.processo(rotulo, comando, root=True)
        else:
            rotulo = "Instalando: " + ", ".join(escolhidos)
            iniciado = tarefa.funcao(
                rotulo, lambda diz: programas.instalar(escolhidos, diz))
        self.json({"iniciado": iniciado, "pacotes": escolhidos,
                   "externas": [e["pkg"] for e in externas]})


def subir(porta: int = PORTA, abrir: bool = True) -> int:
    caminhos.preparar()
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", porta), Painel)
    except OSError as erro:
        print(f"  nao consegui abrir a porta {porta}: {erro}")
        return 1
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    endereco = f"http://127.0.0.1:{porta}/"
    print(f"\n  {NOME} aberto em {endereco}")
    print("  Feche pelo botao na pagina, ou com Ctrl+C aqui.\n")
    if abrir:
        try:
            subprocess.Popen(["xdg-open", endereco],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            print("  abra o endereco acima no seu navegador")

    signal.signal(signal.SIGINT, lambda *_: parar.set())
    signal.signal(signal.SIGTERM, lambda *_: parar.set())
    while not parar.is_set():
        time.sleep(0.3)
    print("  encerrando o painel")
    httpd.shutdown()
    return 0
