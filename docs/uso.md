# Usando o d3bian-init-paleta-xfce

[← voltar ao README](../README.md)

## Rodar

Clone com o nome da pasta igual ao do pacote Python (com `_`) e rode como módulo:

```sh
git clone https://git.saberdl.dev.br/d3bian/paleta-xfce.git d3bian_init_paleta_xfce
python3 -m d3bian_init_paleta_xfce            # pede a senha uma vez e abre o painel
python3 -m d3bian_init_paleta_xfce aplicar --simular
```

O painel abre em `http://127.0.0.1:8931`. A página é violeta, para não confundir
com os outros painéis.

## Instalação pelo painel

1. `python3 -m d3bian_init_paleta_xfce` abre a página no navegador (pede a senha de administrador uma vez, no terminal).
2. Em **Ajustes**, escolha as opções e clique em **Instalar tudo**; o progresso de cada etapa aparece na hora.
3. Depois, mudar uma opção e **Aplicar** roda de novo só as etapas afetadas.
4. **Voltar ao que era antes** desfaz tudo; com **Remover também o que foi instalado**, tira também os pacotes.

A tela **Programas úteis** traz uma lista pronta de programas do repositório
oficial do Debian, mostrando só o que serve para o hardware encontrado.

## Paletas

A escolha da paleta vale para as janelas, os ícones, o terminal e o papel de parede.

| Paleta | Tema das janelas | Como chega |
|---|---|---|
| Nord | `Nordic-darker` (escuro) e `Nordic-Polar` (claro) | `.tar.xz` pronto do autor, baixado e extraído |
| Gruvbox | `Gruvbox-Dark` / `Gruvbox-Light`, com variante compacta | repositório clonado e compilado com `sassc` |
| Everforest | `Everforest-Dark` / `Everforest-Light`, idem | repositório clonado e compilado com `sassc` |

Os três trazem tema de janela (xfwm4), então a barra de título acompanha a paleta.
Claro não é só trocar o tema das janelas: o papel de parede e o terminal também
clareiam. As cores claras do Gruvbox e do Everforest são as que os próprios autores
publicam; as do Nord são escurecidas a partir das originais, porque o Nord só
publica a versão escura.

## Opções

| Opção | Valores |
|---|---|
| `paleta` | Nord, Gruvbox, Everforest |
| `modo` | escuro, claro |
| `compacto` (barras de título estreitas) | sim, não |
| `icones` | Papirus, Tela na cor da paleta, Qogir, Adwaita |
| `terminal` (cores da paleta no xfce4-terminal) | sim, não |
| `fonte` | Inter, Cantarell, a do sistema |
| `barra` | topo, embaixo |
| `barra_tarefas` (janelas abertas na barra) | docklike, botões, nenhuma |
| `relogio` | curto, completo, só a hora |
| `menu` | só ícone, ícone e texto, nenhum |
| `papel` | degradê, liso, manter o atual |
| `icones_area` | nenhum, só removíveis, tudo |
| `janelas` (encaixe e bordas) | sim, não |

## O que fica onde

| Caminho | Escrito por |
|---|---|
| `~/.config/d3bian-init-paleta-xfce` | opções |
| `~/.local/state/d3bian-init-paleta-xfce` | estado, registro, diário e cópias de segurança |
| `~/.local/share/d3bian-init-paleta-xfce/fontes` | repositórios clonados dos temas e ícones |
| `~/.themes` | tema das janelas da paleta, e a cópia com bordas mais largas |
| `~/.local/share/icons` | ícones Tela e Qogir |
| `~/.local/share/backgrounds/paleta` | papel de parede desenhado pelo ImageMagick |
| `~/.local/bin/d3bian-janelas`, `d3bian-layouts`, `d3bian-bordas` | encaixe, layouts e bordas de janela |
| `~/.local/share/applications/xfce4-terminal.desktop` | nova janela e nova aba no clique direito do terminal |
| `~/.config/gtk-3.0/settings.ini`, `gtk.css`, `~/.gtkrc-2.0` | tema e fonte para os programas GTK |
| xfconf (`xsettings`, `xfwm4`, `xfce4-panel`, `xfce4-desktop`, `xfce4-terminal`, `xfce4-keyboard-shortcuts`) | tema, ícones, fonte, barra, área de trabalho, cores do terminal e atalhos |

## Sistemas

Família Debian (a verificação aceita `debian` no `ID` ou no `ID_LIKE` do
`/etc/os-release`), numa sessão gráfica do Xfce com o `xfconf-query`. O Gruvbox e
o Everforest são compilados na hora com o `sassc`, que a etapa de pacotes instala;
sem o ImageMagick o papel de parede gerado não é criado (aviso, não impede).

## Voltar ao que era antes

Em Ajustes, **Voltar ao que era antes**, ou `restaurar --sim`. A barra volta pelo
`xfce4-panel-profiles`; temas e ícones baixados saem porque as receitas anotam
cada pasta antes de criar. Com **Remover também o que foi instalado** saem os
pacotes que o projeto instalou.
