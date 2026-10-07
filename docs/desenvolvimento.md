# Desenvolvimento

[← voltar ao README](../README.md)

Painel em Python puro (só a biblioteca padrão) com HTML/JS sem dependências.
O motor, o servidor e as telas comuns vêm do [modelo](https://git.saberdl.dev.br/d3bian-temas/modelo);
os detalhes deles e as armadilhas conhecidas estão em [nucleo.md](nucleo.md).

## Receitas

| id | nome | afetada por |
|---|---|---|
| 00 | backup (arquivos e a barra de antes) | |
| 10 | pacotes | `paleta`, `icones`, `fonte`, `barra_tarefas` |
| 20 | tema (baixa ou compila) | `paleta`, `modo`, `compacto` |
| 25 | ícones | `icones`, `paleta`, `modo` |
| 30 | aparência | `paleta`, `modo`, `compacto`, `icones`, `fonte` |
| 35 | janelas (encaixe, bordas e atalhos) | `janelas`, `paleta`, `modo`, `compacto` |
| 36 | novo terminal no clique direito | |
| 40 | barra | `barra`, `barra_tarefas`, `relogio`, `menu`, `modo` |
| 50 | terminal | `paleta`, `modo`, `terminal` |
| 60 | papel de parede e área de trabalho | `papel`, `paleta`, `modo`, `icones_area` |

Paletas, nomes de tema e o jeito de instalar cada um ficam no `projeto.py`:
`PALETAS` (fundo, texto e as 16 cores do terminal, por modo), `TEMAS`
(`release` baixa o `.tar.xz` pronto; `instalador` clona e roda o
`themes/install.sh`) e `TELA_COR` (a cor do Tela mais próxima de cada paleta).

## Imagens de exemplo

As imagens de `recursos/web/exemplos` são simulações da área de trabalho
desenhadas em HTML e fotografadas pelo chromium pelo `ferramentas/gerar_exemplos.py`:
papel de parede, barra, uma janela e um terminal com as cores da paleta
(`AMOSTRA` no `projeto.py`). Não é foto do Xfce rodando, e nada da máquina de quem
gera entra nelas: o usuário é sempre "ana", a máquina "debian" e o relógio uma
hora fixa.

```sh
python3 ferramentas/gerar_exemplos.py            # desenha e mostra o que faria
python3 ferramentas/gerar_exemplos.py --gravar   # e aponta no opcoes.toml
```

Precisa de chromium e ImageMagick.
