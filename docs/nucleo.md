# modelo-init

Modelo para projetos no estilo do **d3bian-init**: um painel local, aberto no
navegador, que prepara e ajusta um Debian recém-instalado a partir de
**receitas** em TOML. Só Python da biblioteca padrão e HTML/JS puro, sem pip,
sem npm.

O que já vem pronto e é igual em todo projeto:

- motor de receitas (apt, arquivo, bloco, git, comando, script, copiar,
  autostart, processo, backup, xfconf), com `se`, `requer` e simulação
- reaplicação inteligente: mudou uma opção, só rodam as receitas afetadas por ela
- cópia de segurança antes de mexer, e `restaurar` para desfazer
- painel web em `127.0.0.1` com faixa de estado, verificações prévias e o
  **Terminal** no rodapé (etapas, barra de progresso, log, quadro de conclusão,
  retoma a tarefa ao recarregar a página)
- tela de **Ajustes** desenhada a partir de `opcoes.toml`
- tela de **Programas** com catálogo do repositório oficial
- linha de comando com os mesmos poderes da página
- **diário de alterações** e **Voltar ao que era antes**, com a opção de remover
  também os pacotes instalados

## Criar um projeto novo

```sh
cd ~/Documentos/Projetos/modelo_init
python3 criar.py ../meu_init --nome meu-init --descricao "Prepara um Debian para desenvolvimento."
```

O nome da pasta vira o pacote Python (use `_`); `--nome` é o nome do comando e
das pastas em `~/.config`, `~/.local/state` e `~/.local/share` (use `-`). A
porta sai do nome se não for dada, para dois painéis poderem ficar abertos
juntos. A identidade fica só no `__init__.py`.

## Rodar

```sh
cd ~/Documentos/Projetos
python3 -m meu_init              # pede a senha uma vez e abre o painel
python3 -m meu_init --help       # listar, aplicar, instalar, config, verificar, restaurar
python3 -m meu_init aplicar --simular
```

Para ter o comando no terminal:

```sh
cat > ~/.local/bin/meu-init <<'EOF'
#!/bin/sh
PYTHONPATH="$HOME/Documentos/Projetos" exec python3 -m meu_init "$@"
EOF
chmod +x ~/.local/bin/meu-init
```

## O que é de cada projeto e o que é comum

| Arquivo | Muda por projeto? | Para quê |
|---|---|---|
| `__init__.py` | **sim** | nome, descrição, versão, porta |
| `recursos/opcoes.toml` | **sim** | as opções da tela de Ajustes |
| `recursos/receitas/*.toml` | **sim** | o que o projeto faz na máquina |
| `recursos/arquivos/` | **sim** | modelos de arquivo que as receitas escrevem |
| `projeto.py` | **sim** | valores calculados para as receitas e verificações extras |
| `recursos/programas.json` | se quiser | catálogo da tela de Programas |
| `recursos/web/index.html` | se quiser | cartões da tela inicial |
| `motor.py`, `receitas.py`, `tarefa.py`, `estado.py`, `config.py`, `caminhos.py` | não | núcleo |
| `servidor.py`, `cli.py`, `sistema.py`, `programas.py` | não, a não ser que ganhe rota ou comando novo | núcleo |
| `recursos/web/comum.js`, `estilo.css`, `ajustes.html`, `programas.html` | não | telas reaproveitadas |
| `diario.py`, `desfazer.py` | não | diário de alterações e voltar ao que era antes |

Uma melhoria feita no núcleo de um projeto passa para os outros copiando os
arquivos da parte de baixo da tabela.

## Opções: `recursos/opcoes.toml`

```toml
[[opcao]]
chave = "editor"                       # vira @@editor@@ nas receitas
padrao = "nano"
valores = ["nano", "vim", "micro", "neovim"]   # até 3: botões; mais: lista
titulo = "Editor padrao"
ajuda = "O que abre no git commit"
grupo = "Terminal"                     # cartão onde aparece
nomes = { neovim = "Neovim" }          # rótulo na página (opcional)
livre = '[A-Za-z0-9._\-]{1,40}'        # aceita texto fora da lista (opcional)
exemplos = { vim = "editor-vim.jpg" }  # imagem em recursos/web/exemplos (opcional)
```

A lista de valores é também a validação: o servidor recusa o resto.

## Receitas: `recursos/receitas/NN-nome.toml`

```toml
[modulo]
id = "20"                  # ordem de execução, e como o terminal a chama
nome = "terminal"          # para --apenas e --pular
titulo = "Editor padrao e atalhos do terminal"
nucleo = true              # opcional: a máquina só conta como preparada com as do núcleo
requer = ["10"]            # opcional: só roda se estas já foram aplicadas
afetada_por = ["editor"]   # opções que fazem esta receita rodar de novo

[[passo]]
tipo = "apt"
se = "editor != nano"      # opcional: chave == valor, ou chave != valor
dizer = "instalando o editor"
pacotes = ["@@editor_pacote@@"]
```

Receita editada depois de aplicada conta como pendente e roda no próximo Aplicar.

### Desfazer: `[[desfazer]]`

O motor anota no diário (`~/.local/state/<nome>/diario.jsonl`) o que cada passo
mudou, e o **Voltar ao que era antes** desfaz de trás para frente:

| passo | anota | o desfazer |
|---|---|---|
| `arquivo`, `copiar`, `autostart` | criado ou alterado | criado sai; alterado volta da cópia de segurança |
| `bloco` | arquivo e marca | só o bloco sai; o resto do arquivo fica |
| `git` | clone novo | a pasta sai |
| `xfconf` | valor de antes | volta o valor, ou a propriedade some se não existia |
| `apt` | pacotes que faltavam | só com "remover também o que foi instalado" |

`comando` e `script` não são anotados: o motor não sabe o que fizeram. Para isso
a receita declara os próprios passos de desfazer, no mesmo formato dos passos, e
eles rodam antes do diário, da última receita para a primeira:

```toml
[[passo]]
tipo = "script"
corpo = '''sudo -n chsh -s /usr/bin/fish "$CTX_USUARIO"'''

[[desfazer]]
tipo = "script"
corpo = '''sudo -n chsh -s /bin/bash "$CTX_USUARIO"'''
```

Script que mexe em algo anota antes, com as funções que o motor põe no começo de
todo script. O desfazer usa o que elas guardaram:

```sh
d3_antes "$HOME/.themes/MeuTema"          # copia se existe; se não, marca como criado
d3_xfconf xfwm4 /general/theme string     # valor de agora e se existia
d3_gsettings org.gnome.desktop.interface gtk-theme
d3_dconf /org/gnome/shell/extensions/x/y
d3_processo plank                         # se já rodava antes de iniciar
d3_criado "$perfil_novo"                  # o que só se sabe depois de criado
d3_pacotes plank-reloaded                 # pacote que o script instalou
```

Para o que nem isso cobre (chsh, trocar a tela de login), a receita declara
`[[desfazer]]`.

Com **remover também o que foi instalado** (ou `restaurar --sim --apagar`), uma
etapa a mais desinstala os pacotes anotados e apaga as pastas do projeto. Antes,
a página mostra a lista: cada pacote passa por `apt-get -s remove`, e o que
levaria outros programas junto fica, assim como o pacote do shell do login.
Máquina instalada antes do diário: só as cópias de segurança voltam, e os pacotes
vêm do histórico do apt.

| `tipo` | Campos | Faz |
|---|---|---|
| `apt` | `pacotes` | instala o que falta; ignora o que o repositório não tem |
| `arquivo` | `destino`, `modelo` ou `conteudo`, `modo` | escreve arquivo, com `@@chave@@` resolvido |
| `bloco` | `destino`, `conteudo`, `marca`, `comentario = "#"` | põe ou troca um trecho marcado num arquivo existente |
| `comando` | `argumentos`, `root`, `tolera_falha` | roda um programa |
| `script` | `corpo`, `tolera_falha` | trecho de bash, com o contexto também em `$CTX_*` |
| `git` | `url`, `destino`, `ref` | clona ou atualiza no commit `ref` (40 hexadecimais, obrigatório), conferido e com a árvore limpa |
| `copiar` | `origem`, `destino`, `root`, `tolera_falha` | copia arquivo ou pasta; com `root`, passa por uma pasta temporária do root e fica `root:root` |
| `autostart` | `id`, `nome`, `comando`, `remover` | entrada em `~/.config/autostart` |
| `processo` | `nome`, `acao` (parar, iniciar, reiniciar), `argumentos` | programa da sessão gráfica |
| `backup` | `caminhos` | guarda cópia antes de mexer |
| `xfconf` | `canal`, `chave`, `valor`, `tipo_valor` | propriedade do XFCE |

O contexto tem todas as opções, mais `HOME`, `USUARIO`, `NOME`, `arquivos`,
`fontes`, `estado_dir`, `maquina_virtual` (`sim` ou `nao`) e o que
`projeto.contexto()` devolver.

Só a data do `.toml` marca a receita como pendente. Se mudar apenas um arquivo
de `recursos/arquivos` que ela usa, mexa também na receita (um comentário
basta), senão a mudança não chega às máquinas já preparadas.

### Armadilhas já encontradas

- **Nome de plugin do XFCE:** o id é o nome do `.desktop` em
  `/usr/share/xfce4/panel/plugins`, que nem sempre segue o nome do pacote
  (`xfce4-windowck-plugin` instala `wckbuttons` e `windowck-plugin`). Um id
  que não existe abre a janela "plugin não pode ser carregado". Confira com
  `[ -f .../$id.desktop ]` antes de pôr na barra.
- **`xfce4-panel --quit` ou `-r` com o painel parado:** abre a janela "Falha
  ao sair do painel", mesmo com a saída descartada. Pergunte antes com
  `pgrep -x xfce4-panel`.
- **Máquina virtual:** compositor com OpenGL (picom com `backend = "glx"` e
  `vsync`) deixa as janelas sem redesenhar; o texto digitado só aparece quando o
  foco muda. Use `se = "maquina_virtual == sim"` para trocar por `xrender` sem
  vsync.
- **Download sem retorno:** `git clone` e `fc-cache -f` de repositórios grandes
  não escrevem nada no terminal e parecem travados. Diga antes com `dizer` quanto
  vai baixar, e rode o `fc-cache` só na pasta nova.
- **Opção que depende de download:** uma galeria cujas imagens só chegam com a
  instalação fica vazia na primeira execução. Mostre as escolhas que não
  dependem delas e um aviso, em vez de esconder a opção.

## `projeto.py`

- `contexto(cfg)`: valores derivados das opções. Ex.: a opção `editor = neovim`
  vira `editor_pacote = neovim` e `editor_comando = nvim`.
- `verificacoes(add)`: checagens a mais, como exigir XFCE.
  `add(nome, ok, detalhe, critico=True, dica="")`; a `dica` é o que a faixa do
  topo mostra quando a checagem impede.

## Hardware na tela de Programas

O `hardware.py` lê `/sys` e `/proc`, sem root, e a tela de Programas abre com um
cartão do que achou. Um item do `programas.json` com o campo `hardware` só
aparece nesse cartão, e só se a máquina tiver aquele hardware:

```json
{"pkg": "blueman", "nome": "Bluetooth", "desc": "...", "hardware": "bluetooth", "papel": "necessario"}
{"pkg": "tlp", "nome": "TLP", "desc": "...", "hardware": ["bateria", "sem-power-profiles"], "papel": "extra"}
```

- `hardware`: uma marca, ou uma lista em que todas precisam valer. Marcas:
  `bluetooth`, `webcam`, `bateria`, `wifi`, `video-intel`, `video-amd`,
  `video-nvidia`, `cpu-intel` e `cpu-amd` (fora de VM), `termico-intel`,
  `leitor-digital`, `som-pulseaudio`, `som-pipewire`, `sem-power-profiles`,
  `uefi` e `firmware`.
- `firmware` vale quando um driver em uso pede aquele pacote
  (`FIRMWARE_POR_DRIVER` no `hardware.py`). Não se confere arquivo por arquivo:
  um módulo declara o firmware de todos os chips que suporta, e isso apontaria
  falta onde não há.
- `papel`: `necessario` vem marcado quando falta; `extra` fica só sugerido.

## Programa de fora do Debian com configuração

Um item do catálogo pode vir de repositório de terceiro, levar pacotes junto e
rodar um roteiro depois do apt. O Docker rootless usa os três:

```json
{"pkg": "docker-ce", "nome": "Docker (rootless)", "desc": "...",
 "fonte": "docker", "aviso": "o que será acrescentado ao apt",
 "junto": ["docker-ce-cli", "containerd.io", "docker-ce-rootless-extras", "uidmap"],
 "depois": "docker-rootless.sh"}
```

- `fonte`: nome de um `case` em `recursos/arquivos/fonte-externa.sh`, onde ficam
  a chave e a linha do apt. A página mostra o `aviso` e pede confirmação antes.
- `junto`: instalados no mesmo `apt-get install`; o servidor aceita porque vêm
  do catálogo, não da página.
- `depois`: nome de um arquivo em `recursos/arquivos`, rodado com `bash` como o
  usuário do painel. Passo de sistema dentro dele usa `sudo -n`.

## Telas

Toda página começa igual; o servidor troca `@@NOME@@`, `@@VERSAO@@` e
`@@DESCRICAO@@` ao entregar qualquer `.html`:

```html
<title>Minha tela - @@NOME@@</title>
<meta name="projeto" content="@@NOME@@" data-versao="@@VERSAO@@">
<link rel="stylesheet" href="estilo.css">
<script src="comum.js"></script>

<div class="estado"></div>
<a class="voltar" href="/"><span aria-hidden="true">&larr;</span> Voltar ao início</a>
<h1>Minha tela</h1>
```

Para uma tela nova: crie o `.html` em `recursos/web`, ponha um cartão no
`index.html` e, se ela precisar de dados ou ações próprias, acrescente a rota em
`servidor.py`, rodando o trabalho longo com `tarefa.funcao(rotulo, alvo)`.

O `comum.js` expõe o `Terminal` para acompanhar essas tarefas:

```js
Terminal.acompanhar({titulo, etapas: [{id, nome}], dica, aoTerminar: async codigo => ({bom, titulo, texto, itens})});
Terminal.retomar({titulo: rotulo => ..., etapas: rotulo => [...], aoTerminar});  // na carga da página
Terminal.aoMudar(ocupado => ...);   // travar botões enquanto roda
Terminal.ocupado();
Terminal.avisar(bom, titulo, texto, itens);   // quadro avulso
```

As etapas do terminal andam sozinhas com as linhas `==> id titulo` e
`concluido:` que o `receitas.executar` escreve, e a barra acompanha o apt pelas
linhas `pmstatus:`/`dlstatus:`.

## API do servidor

| Rota | Método | Devolve ou faz |
|---|---|---|
| `/api/projeto` | GET | nome, versão, host, ambiente |
| `/api/estado` | GET | config, opções, receitas, se está instalado |
| `/api/verificacoes` | GET | checagens e impedimentos |
| `/api/progresso?desde=N` | GET | linhas da tarefa atual |
| `/api/programas` | GET | catálogo com o que está instalado |
| `/api/aplicar` | POST | grava as opções e roda as receitas afetadas |
| `/api/instalar` | POST | roda todas as receitas |
| `/api/programas/instalar`, `/remover` | POST | só pacotes do catálogo |
| `/api/desfazer` | POST | volta ao que era antes; `{"apagar": true}` remove também o que foi instalado |
| `/api/desfazer/previa` | GET | o que o remover apagaria, sem mexer em nada |
| `/api/sair` | POST | encerra o painel |

## Cuidados que o modelo já tem

- O painel escuta só em `127.0.0.1`.
- A senha é digitada no terminal que abriu o painel, nunca na página.
- A página só instala o que está no `programas.json`; fonte de terceiro pede
  confirmação mostrando o que será acrescentado ao apt.
- Uma tarefa longa por vez.
