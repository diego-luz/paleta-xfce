#!/usr/bin/env python3
"""Gera as imagens de exemplo que a pagina de Ajustes mostra em cada opcao.

Nao roda na maquina de quem usa o painel: e ferramenta de quem mantem o
projeto, e as imagens vao prontas em recursos/web/exemplos.

Cada imagem e uma *simulacao* da area de trabalho desenhada em HTML e
fotografada pelo chromium: papel de parede, barra, uma janela e um terminal com
as cores da paleta. Nao e foto do Xfce rodando, e serve para escolher vendo.
Por isso nada de dado da maquina de quem gera: o usuario e sempre "ana", a
maquina "debian" e o relogio uma hora fixa.

    python3 ferramentas/gerar_exemplos.py            # desenha e mostra o que faria
    python3 ferramentas/gerar_exemplos.py --gravar   # e aponta no opcoes.toml

Precisa de chromium e ImageMagick.
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ.parent))
PACOTE = RAIZ.name
projeto = __import__(PACOTE + ".projeto", fromlist=["projeto"])

EXEMPLOS = RAIZ / "recursos/web/exemplos"
OPCOES = RAIZ / "recursos/opcoes.toml"

# dados de mentira, iguais em qualquer maquina que gere as imagens
USUARIO, MAQUINA = "ana", "debian"
HORA = "seg 15 set  14:20"
PASTAS = ["Documentos", "Imagens", "Downloads", "Projetos", "Musica", "Videos"]


# --------------------------------------------------------------------------
# a cena: papel de parede, barra, janela e terminal
# --------------------------------------------------------------------------

PAGINA = """<!doctype html><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1280px;height:640px;overflow:hidden}}
body{{font:13px/1.4 "DejaVu Sans",system-ui,sans-serif;background:{papel}}}
.area{{position:relative;width:1280px;height:640px;display:flex;flex-direction:column}}
.barra{{position:absolute;left:0;right:0;{borda_barra}:0;height:34px;display:flex;
  align-items:center;gap:10px;padding:0 12px;background:{barra_fundo};color:{barra_texto};
  font-size:12.5px;backdrop-filter:blur(6px)}}
.barra .menu{{display:grid;grid-template-columns:repeat(3,4px);gap:3px;padding:6px 8px;border-radius:6px}}
.barra .menu i{{width:4px;height:4px;border-radius:1px;background:{barra_texto};opacity:.85}}
.barra .apps{{display:flex;gap:6px;align-items:center}}
.barra .apps b{{width:22px;height:22px;border-radius:6px;display:block;opacity:.9}}
.barra .esp{{flex:1}}
.barra .bandeja{{display:flex;gap:9px;align-items:center;opacity:.8}}
.barra .bandeja i{{width:12px;height:12px;border-radius:3px;background:{barra_texto};opacity:.55}}
.barra .relogio{{font-variant-numeric:tabular-nums;opacity:.95}}
.jan{{position:absolute;border-radius:10px;overflow:hidden;background:{janela};color:{texto};
  box-shadow:0 18px 50px rgba(0,0,0,.45);border:1px solid {borda}}}
.tit{{height:{alt_titulo}px;display:flex;align-items:center;padding:0 12px;background:{titulo};
  font-weight:600;font-size:12.5px;position:relative;border-bottom:1px solid {borda}}}
.tit span{{position:absolute;left:0;right:0;text-align:center;opacity:.9}}
.tit .bts{{margin-left:auto;display:flex;gap:8px;z-index:1}}
.tit .bts i{{width:11px;height:11px;border-radius:50%;background:{texto};opacity:.35;display:block}}
.corpo{{display:flex;height:calc(100% - {alt_titulo}px)}}
.lado{{width:170px;background:{lateral};border-right:1px solid {borda};padding:10px 8px;
  display:flex;flex-direction:column;gap:2px}}
.lado a{{display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:7px;
  font-size:12.5px;opacity:.85}}
.lado a.on{{background:{destaque};color:{sobre_destaque};opacity:1;font-weight:600}}
.lado a b{{width:13px;height:11px;border-radius:2px;background:{destaque};opacity:.8;display:block}}
.lado a.on b{{background:{sobre_destaque}}}
.grade{{flex:1;padding:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px;align-content:start}}
.grade div{{text-align:center;font-size:11.5px;opacity:.85}}
.grade div b{{display:block;height:46px;border-radius:8px;background:{destaque};opacity:.22;margin-bottom:6px}}
.term{{font:13.5px/1.55 "DejaVu Sans Mono",monospace;padding:12px 14px;white-space:pre;
  background:{term_fundo};color:{term_texto};height:100%}}
.term u{{text-decoration:none}}
.cores{{display:flex;gap:5px;margin-top:10px}}
.cores i{{width:20px;height:13px;border-radius:3px;display:block}}
</style>
<div class="area">
  <div class="barra">
    {menu}
    <div class="apps">{apps}</div>
    <div class="esp"></div>
    <div class="bandeja"><i></i><i></i><i></i></div>
    <div class="relogio">{hora}</div>
  </div>

  <div class="jan" style="left:80px;top:{topo_janela}px;width:640px;height:330px">
    <div class="tit"><span>Arquivos</span><div class="bts"><i></i><i></i><i></i></div></div>
    <div class="corpo">
      <div class="lado">{lado}</div>
      <div class="grade">{grade}</div>
    </div>
  </div>

  <div class="jan" style="left:470px;top:{topo_terminal}px;width:640px;height:215px">
    <div class="tit"><span>Terminal</span><div class="bts"><i></i><i></i><i></i></div></div>
    <div class="term">{terminal}</div>
  </div>
</div>"""


def _rgba(quatro: str) -> str:
    r, g, b, a = (float(x) for x in quatro.split())
    return f"rgba({round(r * 255)},{round(g * 255)},{round(b * 255)},{a})"


def _claro(cor: str) -> bool:
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return (r * 299 + g * 587 + b * 114) / 1000 > 140


def _terminal(cores: list[str], fundo: str, texto: str) -> str:
    """Um terminal curtinho, so para as cores aparecerem em uso."""
    az, vd, am, cy = cores[12], cores[10], cores[11], cores[14]
    e = html.escape
    linhas = [
        f'<u style="color:{vd}">{e(USUARIO)}@{e(MAQUINA)}</u>'
        f'<u style="color:{texto};opacity:.6"> ~ </u>'
        f'<u style="color:{az}">$</u> ls',
        f'<u style="color:{az}">Documentos</u>  <u style="color:{az}">Imagens</u>  '
        f'<u style="color:{az}">Projetos</u>  <u style="color:{vd}">notas.md</u>',
        f'<u style="color:{vd}">{e(USUARIO)}@{e(MAQUINA)}</u>'
        f'<u style="color:{texto};opacity:.6"> ~ </u>'
        f'<u style="color:{az}">$</u> git status',
        f'<u style="color:{am}">modificado:</u> app.py   '
        f'<u style="color:{cy}">ramo:</u> principal',
    ]
    faixa = "".join(f'<i style="background:{c}"></i>' for c in cores[8:16])
    return "\n".join(linhas) + f'\n<div class="cores">{faixa}</div>'


def cena(ctx: dict[str, str], cfg: dict[str, str]) -> str:
    paleta = ctx.get("paleta_nome", "")
    modo = cfg.get("modo", "escuro")
    chave = (paleta, modo) if paleta else modo
    janela, titulo, texto, lateral, destaque, borda = projeto.AMOSTRA[chave]
    sobre = "#ffffff" if not _claro(destaque) else "#1c1c1c"
    # as cores do terminal vem prontas do proprio contexto, na mesma ordem que a
    # receita grava no xfce4-terminal
    cores = ctx["paleta_xfce"].split(";")

    embaixo = ctx["painel_posicao"].startswith("p=8")
    # o papel de parede: o mesmo degrade que a receita desenha, ou a cor lisa
    cima, baixo = ctx["papel_cor_cima"], ctx["papel_cor_baixo"]
    papel = (f"linear-gradient(160deg,{cima},{baixo})" if cfg.get("papel", "degrade") == "degrade"
             else baixo)

    menu = ('<div class="menu">' + "<i></i>" * 9 + "</div>"
            if cfg.get("menu", "icone") != "nenhum" else "")
    tarefas = cfg.get("barra_tarefas", "docklike")
    if tarefas == "docklike":
        apps = "".join(f'<b style="background:{c}"></b>' for c in (destaque, cores[10], cores[13]))
    elif tarefas == "botoes":
        apps = "".join(
            f'<b style="width:118px;border-radius:5px;background:{texto};opacity:.16"></b>'
            for _ in range(3))
    else:
        apps = ""

    lado = "".join(
        f'<a class="{"on" if i == 0 else ""}"><b></b>{html.escape(p)}</a>'
        for i, p in enumerate(["Início"] + PASTAS[:4]))
    grade = "".join(f"<div><b></b>{html.escape(p)}</div>" for p in PASTAS)

    return PAGINA.format(
        papel=papel, janela=janela, titulo=titulo, texto=texto, lateral=lateral,
        destaque=destaque, sobre_destaque=sobre, borda=borda,
        alt_titulo=30 if cfg.get("compacto", "sim") == "sim" else 42,
        barra_fundo=_rgba(ctx["painel_fundo"]), barra_texto=ctx["painel_texto"],
        borda_barra="bottom" if embaixo else "top",
        topo_janela=70 if not embaixo else 46, topo_terminal=300 if not embaixo else 276,
        menu=menu, apps=apps, hora=html.escape(HORA), lado=lado, grade=grade,
        term_fundo=ctx["cor_fundo"], term_texto=ctx["cor_texto"],
        terminal=_terminal(cores, ctx["cor_fundo"], ctx["cor_texto"]))


def fotografar(pagina: str, destino: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        arq = Path(tmp) / "cena.html"
        arq.write_text(pagina)
        png = Path(tmp) / "cena.png"
        subprocess.run(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu",
                        "--hide-scrollbars", "--force-device-scale-factor=1",
                        "--window-size=1280,640", f"--screenshot={png}", f"file://{arq}"],
                       capture_output=True, timeout=120, check=True)
        destino.parent.mkdir(parents=True, exist_ok=True)
        # cores cheias: reduzir a paleta granula o degrade do papel de parede
        subprocess.run(["convert", str(png), "-resize", "900x", "-strip",
                        "-define", "png:compression-level=9", str(destino)], check=True)
    print(f"  {destino.name}  {destino.stat().st_size // 1024} KB")


# --------------------------------------------------------------------------
# quais imagens cada opcao ganha
# --------------------------------------------------------------------------

# chave da opcao -> o resto da configuracao que fica fixo naquela serie, para a
# imagem mostrar so a diferenca daquela opcao. Valor que nao muda nada na tela
# (ou que so mantem o que ja existe) fica de fora.
SERIES = {
    "paleta": ({"modo": "escuro"}, None),
    "modo": ({"paleta": "nord"}, None),
    "compacto": ({"paleta": "nord", "modo": "escuro"}, None),
    "barra": ({"paleta": "nord", "modo": "escuro"}, None),
    "barra_tarefas": ({"paleta": "nord", "modo": "escuro"}, None),
    "menu": ({"paleta": "nord", "modo": "escuro"}, ["icone", "nenhum"]),
    "papel": ({"paleta": "nord", "modo": "escuro"}, ["degrade", "liso"]),
}


def opcoes() -> dict[str, dict]:
    with OPCOES.open("rb") as f:
        return {o["chave"]: o for o in tomllib.load(f)["opcao"]}


def gravar(mapas: dict[str, dict[str, str]]) -> None:
    """Escreve a linha exemplos = { ... } de cada opcao no opcoes.toml."""
    texto = OPCOES.read_text()
    for chave, mapa in mapas.items():
        linha = "exemplos = { " + ", ".join(
            f'"{v}" = "{a}"' for v, a in mapa.items()) + " }"
        bloco = re.search(rf'(\[\[opcao\]\]\nchave = "{chave}"\n(?:.*\n)*?)(?=\n\[\[opcao\]\]|\Z)',
                          texto)
        if not bloco:
            print(f"  atencao: nao achei a opcao {chave} no opcoes.toml")
            continue
        novo = re.sub(r"^exemplos = \{.*\}\n", "", bloco.group(1), flags=re.M).rstrip("\n")
        texto = texto.replace(bloco.group(1), novo + "\n" + linha + "\n\n")
    OPCOES.write_text(texto)
    print(f"opcoes.toml atualizado: {', '.join(mapas)}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gravar", action="store_true", help="aponta as imagens no opcoes.toml")
    p.add_argument("--apenas", help="so esta opcao (paleta, modo, barra...)")
    args = p.parse_args()

    todas = opcoes()
    padroes = {c: o["padrao"] for c, o in todas.items()}
    mapas: dict[str, dict[str, str]] = {}
    for chave, (fixo, quais) in SERIES.items():
        if args.apenas and chave != args.apenas:
            continue
        if chave not in todas:
            continue
        print(f"{chave}:")
        mapas[chave] = {}
        for valor in (quais or todas[chave]["valores"]):
            cfg = {**padroes, **fixo, chave: valor}
            arquivo = f"{chave}-{valor}.png"
            fotografar(cena(projeto.contexto(cfg), cfg), EXEMPLOS / arquivo)
            mapas[chave][valor] = arquivo

    if args.gravar:
        gravar(mapas)
    else:
        print("\nnada gravado; use --gravar para apontar as imagens no opcoes.toml")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
