#!/usr/bin/env bash
# Habilita uma fonte de pacotes que nao e do Debian.
#
#   fonte-externa.sh microsoft-vscode
#
# Cada fonte e descrita aqui dentro, e nao vem de fora, para que o que o
# programa pode acrescentar ao seu apt esteja tudo em um arquivo so, legivel.
# Roda como root.
set -euo pipefail

fonte="${1:-}"

case "$fonte" in
  microsoft-vscode)
    url_chave="https://packages.microsoft.com/keys/microsoft.asc"
    chaveiro="/usr/share/keyrings/microsoft-vscode.gpg"
    lista="/etc/apt/sources.list.d/microsoft-vscode.list"
    linha="deb [arch=amd64,arm64,armhf signed-by=$chaveiro] https://packages.microsoft.com/repos/code stable main"
    # impressao digital publicada pela Microsoft para a chave de assinatura
    impressao="BC528686B50D79E339D3721CEB3E94ADBE1229CF"
    origem="packages.microsoft.com"
    pacotes="code"
    ;;
  docker)
    # o mesmo repositorio que o get.docker.com configura, sem rodar script de fora
    url_chave="https://download.docker.com/linux/debian/gpg"
    chaveiro="/usr/share/keyrings/docker.gpg"
    lista="/etc/apt/sources.list.d/docker.list"
    versao="$(. /etc/os-release && echo "$VERSION_CODENAME")"
    linha="deb [arch=$(dpkg --print-architecture) signed-by=$chaveiro] https://download.docker.com/linux/debian $versao stable"
    # impressao digital publicada pela Docker (docs.docker.com/engine/install/debian)
    impressao="9DC858229FC7DD38854AE2D88D81803C0EBFCD88"
    origem="download.docker.com"
    pacotes="docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras"
    ;;
  *)
    echo "fonte desconhecida: $fonte" >&2
    exit 2
    ;;
esac

preferencias="/etc/apt/preferences.d/$fonte"

# sem o gpg nao da para conferir de quem e a chave (nem a nova, nem a que ja
# estava): ele vem primeiro, e sem ele nada entra no apt
if ! command -v gpg >/dev/null; then
  echo "instalando o gpg, para conferir a chave"
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q -o Dpkg::Options::=--force-confdef \
    -o Dpkg::Options::=--force-confold --no-install-recommends gpg >/dev/null || true
fi
command -v gpg >/dev/null || { echo "gpg ausente: nao da para conferir a chave; nada foi acrescentado" >&2; exit 1; }

tmp="$(mktemp)"
binaria="$(mktemp)"
gpg_casa="$(mktemp -d)"
trap 'rm -rf "$tmp" "$binaria" "$gpg_casa"' EXIT

# impressoes das chaves principais do arquivo, uma por linha
impressoes_de() {
  GNUPGHOME="$gpg_casa" gpg --batch --show-keys --with-colons "$1" 2>/dev/null \
    | awk -F: '$1=="pub"{p=1;next} $1=="fpr"&&p{print $10;p=0}'
}

if [ -f "$chaveiro" ] && [ -f "$lista" ]; then
  # a que ja estava tambem precisa ser exatamente a esperada, e so ela
  achadas="$(impressoes_de "$chaveiro")"
  if [ "$achadas" != "$impressao" ]; then
    echo "a chave em $chaveiro nao e a esperada (${achadas:-ilegivel}); confira antes de continuar" >&2
    exit 1
  fi
  echo "a fonte $fonte ja estava configurada"
else
  echo "baixando a chave de $url_chave"
  curl -fsSL --max-time 40 "$url_chave" -o "$tmp"
  [ -s "$tmp" ] || { echo "a chave veio vazia" >&2; exit 1; }

  # a chave baixada tem de ser exatamente a do dono do repositorio, e so ela
  achadas="$(impressoes_de "$tmp")"
  if [ "$achadas" != "$impressao" ]; then
    echo "a chave de $fonte nao confere (${achadas:-ilegivel}, esperava $impressao); nada foi acrescentado" >&2
    exit 1
  fi

  # so a chave com a impressao esperada vai para o chaveiro: importa numa casa
  # do gpg temporaria e exporta por impressao, conferindo de novo o resultado
  GNUPGHOME="$gpg_casa" gpg --batch --quiet --import "$tmp" 2>/dev/null
  GNUPGHOME="$gpg_casa" gpg --batch --export "$impressao" > "$binaria"
  [ "$(impressoes_de "$binaria")" = "$impressao" ] \
    || { echo "a chave exportada de $fonte nao confere; nada foi acrescentado" >&2; exit 1; }

  # chaveiro proprio, amarrado a fonte com signed-by: esta chave nao valida
  # nenhum outro repositorio do sistema
  install -m 0644 "$binaria" "$chaveiro"
  printf '%s\n' "$linha" > "$tmp"
  install -m 0644 "$tmp" "$lista"
  echo "fonte adicionada em $lista"
fi

# o repositorio de fora so serve os pacotes para que foi acrescentado: nenhum
# outro pacote vem dele (-1), nem troca os do Debian
printf 'Package: *\nPin: origin %s\nPin-Priority: -1\n\nPackage: %s\nPin: origin %s\nPin-Priority: 500\n' \
  "$origem" "$pacotes" "$origem" > "$tmp"
install -m 0644 "$tmp" "$preferencias"

echo "atualizando o indice apenas desta fonte"
apt-get update -o Dir::Etc::sourcelist="$lista" \
               -o Dir::Etc::sourceparts="-" \
               -o APT::Get::List-Cleanup="0"
echo "pronto"
