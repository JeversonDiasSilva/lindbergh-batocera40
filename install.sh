#!/bin/bash
# Batocera Lindbergh — instalador para Batocera 40
#
#   Instalar/atualizar o suporte a Sega Lindbergh:
#     curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/install.sh | bash
#   Instalar a partir de um pacote já baixado:
#     bash install.sh /caminho/lindbergh-loader-batocera40.squashfs
#   Copiar um jogo (com verificação de leitura, para discos/USB instáveis):
#     curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/install.sh | bash -s -- --jogo /caminho/do/outr2sdx
#
# Os jogos NÃO fazem parte deste pacote: copie a pasta do seu próprio jogo.
set -euo pipefail

REPO="JeversonDiasSilva/lindbergh-batocera40"
VERSAO="v1.0"
SHA256="aaaf40292f427cd96b36da428c1882cc6584f4dbe13467695399ffbd3ced3f77"
PACOTE="lindbergh-loader-batocera40.squashfs"
URL="https://github.com/$REPO/releases/download/$VERSAO/$PACOTE"

BASE="${LINDBERGH_ROOT:-/userdata/roms/lindbergh}"
LOADER="$BASE/lindbergh-loader"
JOGOS="$BASE/lindbergh"
ESCFG="${LINDBERGH_ESCFG:-/userdata/system/configs/emulationstation/es_systems_lindbergh.cfg}"
DATA="$(date +%Y%m%d-%H%M%S)"

msg() { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
erro() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

copiar_jogo() {
  local origem="${1%/}"
  [ -d "$origem" ] || erro "pasta não encontrada: $origem"
  [ -x "$LOADER/ferramentas/copia_verificada.py" ] || erro "instale o loader primeiro (rode o install.sh sem --jogo)"
  local nome; nome="$(basename "$origem")"
  [ -e "$JOGOS/$nome" ] && erro "já existe $JOGOS/$nome (mova ou apague antes)"
  msg "Copiando $nome com verificação (cada arquivo é lido até 2 leituras iguais)..."
  python3 -I "$LOADER/ferramentas/copia_verificada.py" "$origem" "$JOGOS/$nome"
  local games; games="$(find "$JOGOS/$nome" -name '*.game' | head -1)"
  [ -n "$games" ] || msg "AVISO: nenhum arquivo .game encontrado — o EmulationStation só lista jogos com .game"
  curl -s -m 5 http://127.0.0.1:1234/reloadgames >/dev/null 2>&1 || true
  msg "Pronto: $JOGOS/$nome"
}

if [ "${1:-}" = "--jogo" ]; then
  copiar_jogo "${2:-}"
  exit 0
fi

command -v unsquashfs >/dev/null || erro "unsquashfs não encontrado"
[ -d /userdata ] || erro "isto foi feito para o Batocera (/userdata não existe)"
grep -q '^40' /usr/share/batocera/batocera.version 2>/dev/null || \
  msg "AVISO: testado no Batocera 40; versão atual: $(cat /usr/share/batocera/batocera.version 2>/dev/null || echo desconhecida)"

TMP="$(mktemp -d /userdata/system/.lindbergh-install.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

if [ -n "${1:-}" ] && [ -f "$1" ]; then
  msg "Usando pacote local: $1"
  cp "$1" "$TMP/$PACOTE"
else
  msg "Baixando $PACOTE ($VERSAO)..."
  curl -fL --retry 3 -o "$TMP/$PACOTE" "$URL"
fi

msg "Conferindo SHA-256..."
echo "$SHA256  $TMP/$PACOTE" | sha256sum -c --quiet - || erro "pacote corrompido ou de outra versão (SHA-256 não confere) — baixe de novo"

if [ -e "$LOADER" ]; then
  msg "Guardando instalação anterior em $LOADER.antes-$DATA"
  mv "$LOADER" "$LOADER.antes-$DATA"
fi
mkdir -p "$BASE"
msg "Extraindo para $LOADER..."
unsquashfs -q -n -d "$LOADER" "$TMP/$PACOTE" >/dev/null

mkdir -p "$JOGOS" /userdata/saves/lindbergh /userdata/system/logs
[ -f "$JOGOS/_info.txt" ] || cp "$LOADER/sistema/_info.txt" "$JOGOS/_info.txt"

mkdir -p "$(dirname "$ESCFG")"
[ -f "$ESCFG" ] && cp "$ESCFG" "$ESCFG.antes-$DATA.bak"
sed "s|/userdata/roms/lindbergh/lindbergh-loader/launch.sh|$LOADER/launch.sh|; s|<path>/userdata/roms/lindbergh/lindbergh</path>|<path>$JOGOS</path>|" \
  "$LOADER/sistema/es_systems_lindbergh.cfg" > "$ESCFG"

# Sair do jogo com HOTKEY+START ou SELECT+START (evmapy do Batocera)
KEYS="${LINDBERGH_KEYS:-/userdata/system/configs/evmapy/lindbergh.keys}"
mkdir -p "$(dirname "$KEYS")"
[ -f "$KEYS" ] && cp "$KEYS" "$KEYS.antes-$DATA.bak"
sed "s|/userdata/roms/lindbergh/lindbergh-loader/|$LOADER/|g" "$LOADER/sistema/lindbergh.keys" > "$KEYS"

curl -s -m 5 http://127.0.0.1:1234/reloadgames >/dev/null 2>&1 || true

msg "Instalado! ($VERSAO)"
cat <<EOF

Próximos passos:
  1. Copie a pasta do jogo para $JOGOS/
     com verificação:  python3 -I $LOADER/ferramentas/copia_verificada.py /origem/outr2sdx $JOGOS/outr2sdx
  2. Cada jogo precisa de um arquivo <id>.game na pasta do executável (ex.: outr2sdx.game).
  3. Se o sistema "Sega Lindbergh" não aparecer, reinicie o EmulationStation
     (Menu > Sair > Reiniciar EmulationStation).

Sair do jogo: HOTKEY+START ou SELECT+START (botões do es_input.cfg de cada controle).

Log dos jogos: /userdata/system/logs/lindbergh.log
EOF
