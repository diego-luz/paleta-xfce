# Usando o d3bian-init-paleta-xfce

[← voltar ao README](../README.md)

## Rodar

Clone com o nome da pasta igual ao do pacote Python (com `_`) e rode como módulo:

```sh
git clone https://github.com/diego-luz/paleta-xfce.git d3bian_init_paleta_xfce
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
| `barra` | topo, embaixo, em ilhas |
| `barra_tarefas` (janelas abertas na barra) | docklike, botões, nenhuma |
| `relogio` | curto, completo, só a hora |
| `menu` | só ícone, ícone e texto, nenhum |
| `papel` | degradê, liso, manter o atual |
| `icones_area` | nenhum, só removíveis, tudo |
| `janelas` (encaixe e bordas) | sim, não |
| `efeitos` (picom) | desligados, só sombras e cantos, desfoque e sombras |

Os padrões deixam o visual de sempre: barra no topo e efeitos desligados (o
compositor do próprio Xfce). As ilhas e o picom vêm do
[oasis-xfce](https://github.com/diego-luz/oasis-xfce).

## Barra em ilhas

Com `barra = ilhas`, a barra solta da borda: uma barra fina no topo (menu,
bandeja, som, energia, relógio e sair) e as janelas abertas numa ilha no meio,
embaixo, as duas com cantos redondos e fundo um pouco translúcido. A ilha de
baixo traz o docklike com alguns programas fixados (arquivos, terminal,
navegador, editor de texto) e cresce com o que estiver aberto; com
`barra_tarefas = nenhuma`, fica só a barra de cima. As cores seguem o modo
e a paleta escolhido.

As ilhas entram pelo `xfce4-panel-profiles load`. Painel solto não reserva
espaço na tela, então o projeto põe margens no xfwm4 (Ajustes do gerenciador de
janelas, ajustes finos, Espaços de trabalho, Margens), só depois que o `load` deu
certo: as janelas maximizadas param antes das ilhas, e o encaixe também. As
margens são em pixels de verdade: com a escala 2 do Xfce (telas HiDPI), elas
saem dobradas. As posições são calculadas para o monitor principal e a escala de
agora: mudou a resolução ou a escala, rode de novo só a barra:

```sh
python3 -m d3bian_init_paleta_xfce aplicar --apenas barra
```

Voltando para a barra no topo ou embaixo, as margens que as ilhas puseram saem
(margem que você mudou depois fica).

## Efeitos (picom)

Com `efeitos` em **só sombras** ou **desfoque**, o picom desenha sombras e cantos
redondos nas janelas (e, com desfoque, o fundo atrás do que é translúcido fica
embaçado). Com o picom ligado, o compositor do próprio xfwm4 fica desligado (os
dois juntos brigam pela tela) e o picom inicia junto com a sessão
(`~/.config/autostart/d3bian-paleta-picom.desktop`, que chama o
`~/.local/bin/d3bian-picom`). Antes de escrever o `picom.conf`, o projeto confere
o vídeo: com `glxinfo` dizendo `llvmpipe` (ou sem renderização direta), numa
placa de vídeo de VM sem 3D, ou numa VM sem como confirmar, o picom roda
**leve**: `xrender`, sem desfoque e sem vsync. Se o picom não ficar de pé (agora
ou ao entrar na sessão), o `d3bian-picom` liga de volta o compositor do xfwm4.
Com os efeitos **desligados**, o picom deste projeto para e o compositor do xfwm4
volta ao que era antes de o picom ligar. Um picom que você mesmo abriu, com
outra configuração, nunca é fechado pelo projeto.

## Encaixe de janelas

Com `janelas = sim`: Super e as setas para metades e maximizar, Super+1 a 4 para
os quartos (do próprio xfwm4), Super+C centraliza, Super+X ocupa quase a tela
toda, Super+Shift e as setas dividem em terços e Super+Z abre um quadro de
layouts. Arrastar a janela até a borda também encaixa. O `d3bian-janelas` e o
`d3bian-layouts` descontam as margens do xfwm4, então com as ilhas nada fica por
baixo delas. Os atalhos levam o caminho entre aspas, para a pasta pessoal com
espaço.

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
| `~/.config/gtk-3.0/settings.ini`, `gtk.css` | tema e fonte para os programas GTK, e os cantos das ilhas |
| `~/.gtkrc-2.0` | tema dos programas GTK 2, num bloco marcado |
| `~/.local/state/d3bian-init-paleta-xfce/painel-ilhas.tar.bz2` | o perfil das ilhas, carregado pelo `xfce4-panel-profiles` |
| `~/.config/picom/picom.conf`, `~/.config/autostart/d3bian-paleta-picom.desktop`, `~/.local/bin/d3bian-picom` | efeitos |
| xfconf (`xsettings`, `xfwm4`, `xfce4-panel`, `xfce4-desktop`, `xfce4-terminal`, `xfce4-keyboard-shortcuts`) | tema, ícones, fonte, barra, área de trabalho, cores do terminal e atalhos |

## Sistemas

Família Debian (a verificação aceita `debian` no `ID` ou no `ID_LIKE` do
`/etc/os-release`), numa sessão gráfica do Xfce com o `xfconf-query`. O Gruvbox e
o Everforest são compilados na hora com o `sassc`, que a etapa de pacotes instala;
sem o ImageMagick o papel de parede gerado não é criado (aviso, não impede).

## Um tema Xfce por vez

Os temas Xfce da família (bigsur-xfce, bigsur-minimalista-xfce, minimal-xfce,
paleta-xfce e oasis-xfce) usam os mesmos scripts (`d3bian-janelas`,
`d3bian-layouts`, `d3bian-bordas`, `d3bian-picom`), o mesmo `picom.conf` e os
mesmos ajustes do painel, do xfwm4, dos atalhos e do GTK. Um por cima do outro
estragaria o "voltar" do primeiro, então a instalação é recusada (saída 1)
enquanto outro deles estiver aplicado nesta conta:

```
o tema bigsur-xfce está instalado nesta conta; use o 'voltar' dele antes (python3 -m d3bian_init_bigsur_xfce restaurar) ou troque de vez com python3 -m d3bian_init_paleta_xfce aplicar --trocar
```

Conta como aplicado o tema com etapa marcada em `~/.local/state/<pasta>/aplicado/`
ou com linha no `diario.jsonl` mais nova que essa pasta: só simulação não conta,
e depois de um `restaurar` completo ele deixa de contar. Rodar de novo este mesmo
projeto (`aplicar --refazer`, `config`, `restaurar`) segue normal, e
`aplicar --simular` só avisa.

Para trocar de uma vez: `python3 -m d3bian_init_paleta_xfce aplicar --trocar`, ou,
no painel, o botão **Voltar o … e instalar este** (pede confirmação). A troca roda o
`restaurar --sim` do outro tema pelo próprio projeto dele (os pacotes dele ficam)
e só instala este se o outro voltar sem erro. O projeto do outro é procurado na
mesma pasta deste (clonados lado a lado) e depois onde o Python o acharia; se não
achar, a troca para e mostra o comando para rodar à mão.

## Voltar ao que era antes

Em Ajustes, **Voltar ao que era antes**, ou `restaurar --sim`. A barra volta pelo
`xfce4-panel-profiles`; temas e ícones baixados saem porque as receitas anotam
cada pasta antes de criar. Com **Remover também o que foi instalado** saem os
pacotes que o projeto instalou.

O picom deste projeto para, e o compositor do xfwm4, as margens e a sombra dos
painéis voltam pelo diário. O `~/.gtkrc-2.0` perde o bloco marcado (e some, se
só existia pelo projeto).
