"""O que e proprio deste projeto e nao cabe numa receita.

A paleta escolhida decide tudo: o tema das janelas, os icones, as cores do
terminal e o papel de parede. Cada paleta tem um jeito proprio de instalar o
tema, e e isso que as receitas leem daqui:

- nord: o autor publica o tema pronto em .tar.xz; a receita baixa e extrai
- gruvbox e everforest: repositorios do mesmo autor, com themes/install.sh que
  compila com sassc e escreve em ~/.themes

A barra em ilhas, o picom e o encaixe que respeita as margens vem do
d3bian-init-oasis-xfce.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

# paleta e modo -> fundo, texto e as 16 cores do terminal (8 normais, 8 claras)
#
# Claro nao e so trocar o tema das janelas: o papel de parede e o terminal
# tambem clareiam, entao cada paleta tem aqui as suas duas versoes. As cores
# claras do Gruvbox e do Everforest sao as que os proprios autores publicam; as
# do Nord sao escurecidas a partir das originais, porque o Nord so publica a
# versao escura e amarelo claro sobre fundo claro nao se le.
PALETAS = {
    "nord": {
        "escuro": ("#2E3440", "#D8DEE9", [
            "#3B4252", "#BF616A", "#A3BE8C", "#EBCB8B", "#81A1C1", "#B48EAD", "#88C0D0", "#E5E9F0",
            "#4C566A", "#BF616A", "#A3BE8C", "#EBCB8B", "#81A1C1", "#B48EAD", "#8FBCBB", "#ECEFF4"]),
        "claro": ("#ECEFF4", "#2E3440", [
            "#E5E9F0", "#B0535C", "#7E9A63", "#B08D4E", "#5E81AC", "#9A7B95", "#5E9BA8", "#4C566A",
            "#D8DEE9", "#BF616A", "#8FA876", "#C0A25E", "#81A1C1", "#B48EAD", "#88C0D0", "#2E3440"]),
    },
    "gruvbox": {
        "escuro": ("#282828", "#EBDBB2", [
            "#282828", "#CC241D", "#98971A", "#D79921", "#458588", "#B16286", "#689D6A", "#A89984",
            "#928374", "#FB4934", "#B8BB26", "#FABD2F", "#83A598", "#D3869B", "#8EC07C", "#EBDBB2"]),
        "claro": ("#FBF1C7", "#3C3836", [
            "#FBF1C7", "#CC241D", "#98971A", "#D79921", "#458588", "#B16286", "#689D6A", "#7C6F64",
            "#928374", "#9D0006", "#79740E", "#B57614", "#076678", "#8F3F71", "#427B58", "#3C3836"]),
    },
    "everforest": {
        "escuro": ("#2D353B", "#D3C6AA", [
            "#343F44", "#E67E80", "#A7C080", "#DBBC7F", "#7FBBB3", "#D699B6", "#83C092", "#D3C6AA",
            "#868D80", "#E67E80", "#A7C080", "#DBBC7F", "#7FBBB3", "#D699B6", "#83C092", "#EFEBD4"]),
        "claro": ("#FDF6E3", "#5C6A72", [
            "#F2EFDF", "#F85552", "#8DA101", "#DFA000", "#3A94C5", "#DF69BA", "#35A77C", "#5C6A72",
            "#939F91", "#E66868", "#93B259", "#C4880A", "#3A94C5", "#DF69BA", "#35A77C", "#4F585E"]),
    },
}

# paleta -> como o tema chega na maquina
#   release:    baixa o .tar.xz pronto do GitHub (nome do arquivo por modo)
#   instalador: clona e roda themes/install.sh (nome do tema e do repositorio)
#
# Tudo com versao fixa: o .tar.xz de um release conferido pelo SHA-256, e os
# repositorios num commit (o install.sh deles roda aqui). Para atualizar: no
# release, troque a versao e recalcule os hashes (sha256sum do arquivo baixado,
# o Nordic nao publica checksums); no repositorio, pegue o commit novo com
# `git ls-remote URL HEAD`, leia o que mudou e troque o "commit".
TEMAS = {
    "nord": {
        "metodo": "release",
        "url": "https://github.com/EliverLara/Nordic/releases/download/v2.2.0/",
        # o Nordic nao tem variante compacta; o claro chama-se Polar
        "arquivo": {"escuro": "Nordic-darker.tar.xz", "claro": "Nordic-Polar.tar.xz"},
        "sha256": {
            "escuro": "49115292bfa15aaa9aea661c7468b48918708a6940e4b8058ac46f3dbb81c626",
            "claro": "9b8dff73ee9de5649723e65ae140e50a51ce31eb1fdaa8487c5fd8c202a7f05e",
        },
        "nome": {"escuro": "Nordic-darker", "claro": "Nordic-Polar"},
    },
    "gruvbox": {
        "metodo": "instalador",
        "repo": "https://github.com/Fausto-Korpsvart/Gruvbox-GTK-Theme.git",
        "commit": "578cd220b5ff6e86b078a6111d26bb20ec8c733f",
        "pasta": "Gruvbox-GTK-Theme",
        "nome": "Gruvbox",
    },
    "everforest": {
        "metodo": "instalador",
        "repo": "https://github.com/Fausto-Korpsvart/Everforest-GTK-Theme.git",
        "commit": "9b8be4d6648ae9eaae3dd550105081f8c9054825",
        "pasta": "Everforest-GTK-Theme",
        "nome": "Everforest",
    },
}

# icones baixados, cada um num commit fixo (atualizar como os temas acima)
TELA_COMMIT = "a1fffc5bfab716bd022dd228ee96fe3965cdb33d"
QOGIR_COMMIT = "c633057ba0d27a504b3255144071c9691ed0264a"

# fora da pasta pessoal as receitas nao criam nada; o desfazer nao apaga la
APAGAVEIS_FORA_DE_CASA: set[str] = set()

# a cor do Tela que mais se aproxima de cada paleta (o instalador dele aceita
# nord, orange, green, entre outras)
TELA_COR = {"nord": "nord", "gruvbox": "orange", "everforest": "green"}

FONTES = {"inter": "Inter", "cantarell": "Cantarell", "sistema": ""}

# Cores so para as imagens de exemplo da pagina: uma aproximacao do que cada
# tema pinta nas janelas, para a pessoa escolher vendo. Nao entram em nenhuma
# receita, quem manda na maquina e o tema instalado.
#   paleta/modo -> janela, barra de titulo, texto, lateral, destaque, borda
AMOSTRA = {
    ("nord", "escuro"): ("#242933", "#2e3440", "#d8dee9", "#262b36", "#88c0d0", "#3b4252"),
    ("nord", "claro"): ("#eceff4", "#e5e9f0", "#2e3440", "#e5e9f0", "#5e81ac", "#d8dee9"),
    ("gruvbox", "escuro"): ("#282828", "#32302f", "#ebdbb2", "#3c3836", "#d79921", "#504945"),
    ("gruvbox", "claro"): ("#fbf1c7", "#ebdbb2", "#3c3836", "#f2e5bc", "#b57614", "#d5c4a1"),
    ("everforest", "escuro"): ("#2d353b", "#343f44", "#d3c6aa", "#343f44", "#a7c080", "#4f585e"),
    ("everforest", "claro"): ("#fdf6e3", "#f4f0d9", "#5c6a72", "#f4f0d9", "#8da101", "#e0dcc7"),
}

RELOGIO = {
    "curto": "%a %d %b  %H:%M",
    "completo": "%a, %d de %B de %Y  %H:%M",
    "so_hora": "%H:%M",
}

# a barra encosta pela borda, no formato que o xfce4-panel grava; os numeros
# vem da ordem do enum SnapPosition do painel (6 = canto superior esquerdo,
# 8 = inferior esquerdo)
POSICAO_BARRA = {"topo": "p=6;x=0;y=0", "baixo": "p=8;x=0;y=0"}

PAPEIS_DIR = Path.home() / ".local/share/backgrounds/paleta"

# raio dos cantos das ilhas; o picom usa o mesmo, para o desfoque nao vazar
RAIO = 14

# programas fixados no dock da ilha de baixo, na ordem; so entram os que existem
FAVORITOS = ["thunar", "xfce4-terminal", "firefox-esr", "firefox", "org.xfce.mousepad"]


def _misturar(a: str, b: str, quanto: float) -> str:
    """Cor entre duas, para o degrade do papel sair da propria paleta."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * quanto) for x, y in zip(ca, cb))


def _rgba(cor: str, alfa: float) -> str:
    """Cor em 0..1 por canal, que e como o xfce4-panel grava o fundo."""
    canais = " ".join(f"{int(cor[i:i + 2], 16) / 255:.3f}" for i in (1, 3, 5))
    return f"{canais} {alfa:.2f}"


def exec_desktop(*argumentos: str) -> str:
    """A linha Exec de um .desktop, com as aspas da especificacao: a pasta
    pessoal pode ter espaco ("/home/joao silva") ou %."""
    def um(arg: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_./:=+,@-]+", arg):
            arg = '"' + re.sub(r'([\\"`$])', r"\\\1", arg) + '"'
        return arg.replace("%", "%%")

    # o valor do .desktop tem os escapes do proprio arquivo: \ vira \\
    return " ".join(um(a) for a in argumentos).replace("\\", "\\\\")


# video sem aceleracao: o picom com glx e desfoque fica lento, ou as janelas
# param de redesenhar (o caso classico e a VM sem 3D)
_SOFTWARE = ("llvmpipe", "softpipe", "swrast", "software rasterizer")
# drivers de video que nao tem 3D (o virtio_gpu pode ter, com virgl, e fica de fora)
_VIDEO_SEM_3D = {"qxl", "bochs", "bochs-drm", "cirrus", "cirrus-qemu", "vboxvideo",
                 "simpledrm", "efifb", "vesafb", "hyperv_drm", "hyperv_fb"}


@functools.lru_cache(maxsize=4)
def _render_software(glxinfo: str, display: str, virtual: bool) -> tuple[bool, str]:
    if os.environ.get("LIBGL_ALWAYS_SOFTWARE") in ("1", "true"):
        return True, "LIBGL_ALWAYS_SOFTWARE ligado"
    if glxinfo and display:
        try:
            saida = subprocess.run([glxinfo, "-B"], capture_output=True, text=True, timeout=6,
                                   stdin=subprocess.DEVNULL,
                                   env={**os.environ, "LC_ALL": "C"}).stdout.lower()
        except (OSError, subprocess.TimeoutExpired):
            saida = ""
        if "direct rendering: no" in saida:
            return True, "sem renderizacao direta (glxinfo)"
        for linha in saida.splitlines():
            if "opengl renderer string" in linha:
                if any(s in linha for s in _SOFTWARE):
                    return True, "video desenhado pelo processador (" + linha.split(":", 1)[1].strip() + ")"
                return False, ""
    drivers = set()
    for card in Path("/sys/class/drm").glob("card[0-9]"):
        try:
            drivers.add(os.path.basename(os.readlink(card / "device/driver")))
        except OSError:
            pass
    if drivers and drivers <= _VIDEO_SEM_3D:
        return True, "placa de video sem 3D (" + ", ".join(sorted(drivers)) + ")"
    if virtual:
        return True, "maquina virtual sem confirmacao de aceleracao 3D"
    return False, ""


def render_software() -> tuple[bool, str]:
    """(sim ou nao, motivo). O glxinfo (mesa-utils) chega com a receita 10."""
    from . import sistema
    return _render_software(shutil.which("glxinfo") or "", os.environ.get("DISPLAY", ""),
                            sistema.maquina_virtual())


def _picom(cfg: dict[str, str]) -> dict[str, str]:
    efeitos = cfg.get("efeitos", "desligado")
    # so pergunta ao video quando o picom vai rodar
    software, motivo = render_software() if efeitos != "desligado" else (False, "")
    desfoque = efeitos == "desfoque" and not software
    if efeitos == "desligado":
        aviso = "efeitos desligados: vale o compositor do proprio Xfce"
    elif software:
        aviso = f"picom em modo leve (xrender, sem desfoque nem vsync): {motivo}"
    elif desfoque:
        aviso = "picom com desfoque, sombras e cantos arredondados"
    else:
        aviso = "picom com sombras e cantos arredondados, sem desfoque"
    linhas_desfoque = "\n".join([
        'blur-method = "dual_kawase";',
        "blur-strength = 5;",
        "blur-background = true;",
        "blur-background-frame = false;",
        "blur-background-fixed = false;",
        "blur-background-exclude = [",
        '  "window_type = \'desktop\'",',
        '  "window_type = \'dnd\'",',
        '  "window_type = \'tooltip\'",',
        '  "_GTK_FRAME_EXTENTS@",',
        '  "class_g = \'firefox\' && argb",',
        '  "class_g = \'firefox-esr\' && argb",',
        '  "class_g = \'Firefox-esr\' && argb"',
        "];",
    ]) if desfoque else "# sem desfoque (pela opcao ou pelo video desta maquina)"
    # janelas translucidas so com desfoque; sem ele o texto de tras atrapalha
    linhas_opacidade = "\n".join([
        "opacity-rule = [",
        '  "94:class_g = \'Xfce4-terminal\' && focused",',
        '  "88:class_g = \'Xfce4-terminal\' && !focused"',
        "];",
    ]) if desfoque else "# janelas opacas: a transparencia so vale junto com o desfoque"
    # a barra colada na borda fica reta; as ilhas sao arredondadas
    excluir_barra = "" if cfg.get("barra") == "ilhas" else '  "window_type = \'dock\'",'
    return {
        "picom_backend": "xrender" if software else "glx",
        "picom_vsync": "false" if software else "true",
        "picom_desfoque": linhas_desfoque,
        "picom_opacidade": linhas_opacidade,
        "picom_excluir_barra": excluir_barra,
        "picom_aviso": aviso,
        # o autostart chama o d3bian-picom, que religa o xfwm4 se o picom cair
        "picom_exec": exec_desktop(str(Path.home() / ".local/bin/d3bian-picom")),
    }


def contexto(cfg: dict[str, str]) -> dict[str, str]:
    paleta = cfg.get("paleta", "nord")
    if paleta not in PALETAS:
        paleta = "nord"
    escuro = cfg.get("modo", "escuro") == "escuro"
    modo = "escuro" if escuro else "claro"
    compacto = cfg.get("compacto", "sim") == "sim"
    fundo, texto, cores = PALETAS[paleta][modo]
    tema = TEMAS[paleta]

    if tema["metodo"] == "release":
        gtk_tema = tema["nome"][modo]
        tema_arquivo = tema["arquivo"][modo]
        tema_url = tema["url"] + tema_arquivo
        tema_sha256 = tema["sha256"][modo]
        repo = pasta = commit = ""
    else:
        # o instalador monta o nome: Gruvbox-Dark, Gruvbox-Dark-Compact...
        gtk_tema = tema["nome"] + ("-Dark" if escuro else "-Light") + ("-Compact" if compacto else "")
        tema_arquivo = tema_url = tema_sha256 = ""
        repo, pasta, commit = tema["repo"], tema["pasta"], tema["commit"]

    fonte = FONTES.get(cfg.get("fonte", ""), "Inter")
    icones = cfg.get("icones", "papirus")
    if icones == "tela":
        icones_tema = "Tela-" + TELA_COR[paleta] + ("-dark" if escuro else "-light")
    elif icones == "papirus":
        icones_tema = "Papirus-Dark" if escuro else "Papirus"
    elif icones == "qogir":
        # o instalador do Qogir gera Qogir, Qogir-dark e Qogir-light
        icones_tema = "Qogir-dark" if escuro else "Qogir"
    else:
        icones_tema = "Adwaita"

    papel = cfg.get("papel", "degrade")
    # a cor de destaque da paleta (a mesma das amostras): pinta o botao marcado
    # das ilhas e o indicador do dock
    destaque = AMOSTRA[(paleta, modo)][4]
    dr, dg, db = (int(destaque[i:i + 2], 16) for i in (1, 3, 5))
    fundo_barra = _misturar(fundo, "#000000" if escuro else "#ffffff", 0.22)
    ctx = {
        "paleta_nome": paleta,
        "gtk_tema": gtk_tema,
        "gtk_esquema": "prefer-dark" if escuro else "default",
        "gtk_escuro": "1" if escuro else "0",
        "icones_tema": icones_tema,
        "tela_cor": TELA_COR[paleta],
        "tema_metodo": tema["metodo"],
        "tema_url": tema_url,
        "tema_arquivo": tema_arquivo,
        "tema_sha256": tema_sha256,
        "tema_repo": repo,
        "tema_commit": commit,
        "tela_commit": TELA_COMMIT,
        "qogir_commit": QOGIR_COMMIT,
        "tema_pasta": pasta,
        "tema_nome_base": tema.get("nome") if isinstance(tema.get("nome"), str) else gtk_tema,
        "tema_cor_install": "dark" if escuro else "light",
        "tema_tamanho_install": "compact" if compacto else "standard",
        "fonte_ui": fonte or "Sans",
        "fonte_titulo": f"{fonte or 'Sans'} Bold 9",
        "cor_fundo": fundo,
        "cor_texto": texto,
        "paleta_xfce": ";".join(cores),
        "paleta_gnome": "[" + ", ".join(f"'{c}'" for c in cores) + "]",
        # o degrade sai da propria paleta: o fundo e uma versao um pouco mais clara dele
        "papel_cor_cima": _misturar(fundo, texto, 0.14),
        "papel_cor_baixo": fundo,
        "papel_tipo": papel,
        "papel_arquivo": str(PAPEIS_DIR / f"{paleta}-{modo}-{papel}.png"),
        "papeis_dir": str(PAPEIS_DIR),
        "relogio_formato": RELOGIO.get(cfg.get("relogio", ""), RELOGIO["curto"]),
        "painel_posicao": POSICAO_BARRA.get(cfg.get("barra", ""), POSICAO_BARRA["topo"]),
        # a barra sai da propria paleta, um tom alem do fundo, e quase opaca
        "painel_fundo": _rgba(_misturar(fundo, "#000000" if escuro else "#ffffff", 0.22), 0.94),
        "painel_texto": texto,
        "menu_titulo": "true" if cfg.get("menu") == "icone_texto" else "false",
        "icones_area_valor": {"nenhum": "0", "so_removiveis": "2", "tudo": "2"}.get(
            cfg.get("icones_area", "nenhum"), "0"),
        "mostrar_removiveis": "true" if cfg.get("icones_area") in ("so_removiveis", "tudo") else "false",
        "mostrar_arquivos": "true" if cfg.get("icones_area") == "tudo" else "false",
        # barra em ilhas: o mesmo tom da barra, um pouco translucido
        "raio": str(RAIO),
        "ilha_fundo_barra": _rgba(fundo_barra, 0.80),
        # a ilha de baixo fica sobre o fundo da paleta (a parte de baixo do papel):
        # um tom na direcao do texto, para aparecer
        "ilha_fundo": _rgba(_misturar(fundo, texto, 0.16 if escuro else 0.10), 0.90),
        "painel_hover": "rgba(255, 255, 255, 0.10)" if escuro else "rgba(0, 0, 0, 0.07)",
        "destaque_cor": destaque,
        "destaque_suave": f"rgba({dr}, {dg}, {db}, 0.22)",
        "favoritos": ";".join(FAVORITOS),
    }
    ctx.update(_picom(cfg))
    return ctx


def verificacoes(add: Callable[..., None]) -> None:
    """Checagens a mais. add(nome, ok, detalhe, critico=True, dica="")."""
    from . import sistema

    ambiente = sistema.desktop().upper()
    xfce = "XFCE" in ambiente
    add("Ambiente grafico", xfce, ambiente or "desconhecido", dica="este projeto e para o XFCE")

    tem_xfconf = bool(shutil.which("xfconf-query"))
    add("Configuracao do XFCE", tem_xfconf,
        "xfconf-query disponivel" if tem_xfconf else "falta o xfconf-query, que guarda os ajustes",
        dica="falta o xfconf-query")

    gravavel = os.access(Path.home(), os.W_OK)
    add("Pasta pessoal", gravavel,
        "gravavel" if gravavel else f"sem permissao de escrita em {Path.home()}",
        dica="não consigo escrever na pasta pessoal")

    # o Gruvbox e o Everforest sao compilados na hora; o Nord vem pronto
    tem_sassc = bool(shutil.which("sassc"))
    add("Compilador do tema (sassc)", tem_sassc,
        "disponivel" if tem_sassc else "sera instalado pela etapa de pacotes", critico=False)

    tem_convert = bool(shutil.which("convert") or shutil.which("magick"))
    add("ImageMagick", tem_convert,
        "disponivel" if tem_convert else "sem o convert, o papel de parede gerado nao e criado",
        critico=False)

    # so informa: com video sem 3D o picom roda em modo leve, sem desfoque
    from . import config
    if config.ler().get("efeitos", "desligado") != "desligado":
        software, motivo = render_software()
        add("Aceleracao de video", not software,
            "o picom pode usar glx e desfoque" if not software
            else f"{motivo}; o picom fica em modo leve, sem desfoque",
            critico=False)
