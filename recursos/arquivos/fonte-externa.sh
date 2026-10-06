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

if [ -f "$chaveiro" ] && [ -f "$lista" ]; then
  echo "a fonte $fonte ja estava configurada"
else
  # sem o gpg nao da para conferir de quem e a chave: entao nada entra no apt
  if ! command -v gpg >/dev/null; then
    echo "instalando o gpg, para conferir a chave"
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q -o Dpkg::Options::=--force-confdef \
      -o Dpkg::Options::=--force-confold --no-install-recommends gpg >/dev/null || true
  fi
  command -v gpg >/dev/null || { echo "gpg ausente: nao da para conferir a chave; nada foi acrescentado" >&2; exit 1; }

  echo "baixando a chave de $url_chave"
  tmp="$(mktemp)"
  gpg_casa="$(mktemp -d)"
  trap 'rm -rf "$tmp" "$gpg_casa"' EXIT
  curl -fsSL --max-time 40 "$url_chave" -o "$tmp"
  [ -s "$tmp" ] || { echo "a chave veio vazia" >&2; exit 1; }

  # a chave baixada tem de ser exatamente a do dono do repositorio, e so ela
  achadas="$(GNUPGHOME="$gpg_casa" gpg --show-keys --with-colons "$tmp" 2>/dev/null \
    | awk -F: '$1=="pub"{p=1;next} $1=="fpr"&&p{print $10;p=0}')"
  if [ "$achadas" != "$impressao" ]; then
    echo "a chave de $fonte nao confere (${achadas:-ilegivel}, esperava $impressao); nada foi acrescentado" >&2
    exit 1
  fi

  # guarda a chave em chaveiro proprio e amarra a fonte a ela com signed-by,
  # para que esta chave nao valide nenhum outro repositorio do sistema
  GNUPGHOME="$gpg_casa" gpg --dearmor --yes --output "$chaveiro" < "$tmp"
  chmod 0644 "$chaveiro"

  printf '%s\n' "$linha" > "$lista"
  chmod 0644 "$lista"
  echo "fonte adicionada em $lista"
fi

# o repositorio de fora so serve os pacotes para que foi acrescentado: nao pode
# trocar outros pacotes do Debian por versoes dele
printf 'Package: *\nPin: origin %s\nPin-Priority: 100\n\nPackage: %s\nPin: origin %s\nPin-Priority: 500\n' \
  "$origem" "$pacotes" "$origem" > "$preferencias"
chmod 0644 "$preferencias"

echo "atualizando o indice apenas desta fonte"
apt-get update -o Dir::Etc::sourcelist="$lista" \
               -o Dir::Etc::sourceparts="-" \
               -o APT::Get::List-Cleanup="0"
echo "pronto"
