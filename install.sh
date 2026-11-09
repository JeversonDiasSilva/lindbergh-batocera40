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
#   Por padrão também baixa e instala o OutRun 2 SP SDX da release (use --sem-jogo para pular):
#     curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/install.sh | bash -s -- --sem-jogo
set -euo pipefail

REPO="JeversonDiasSilva/lindbergh-batocera40"
VERSAO="v1.0"
SHA256="87294240f26f4d7c5b3ea76680c956b1716e9708b7a237eeea894959f75ca6c4"
PACOTE="lindbergh-loader-batocera40.squashfs"
URL="https://github.com/$REPO/releases/download/$VERSAO/$PACOTE"
JOGO_PACOTE="outrun2-sp-sdx-lindbergh.squashfs"
JOGO_SHA256="892287236a9fb394e02c182ac015a0037db2d8f95098f0d2d9ebd3d37e1219c1"
JOGO_URL="https://github.com/$REPO/releases/download/$VERSAO/$JOGO_PACOTE"

BASE="${LINDBERGH_ROOT:-/userdata/roms/lindbergh}"
LOADER="$BASE/lindbergh-loader"
JOGOS="$BASE"   # os jogos ficam direto em /userdata/roms/lindbergh/<jogo>
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

# Junta as entradas de um gamelist.xml em outro, sem apagar os jogos que já estão lá
mesclar_gamelist() {
  local novo="$1" destino="$2"
  if [ ! -f "$destino" ]; then cp "$novo" "$destino"; return; fi
  cp "$destino" "$destino.antes-$DATA.bak"
  python3 -I - "$novo" "$destino" <<'PY'
import sys, xml.etree.ElementTree as ET
novo, dest = ET.parse(sys.argv[1]).getroot(), ET.parse(sys.argv[2])
raiz = dest.getroot()
tem = {g.findtext('path') for g in raiz.findall('game')}
for g in novo.findall('game'):
    if g.findtext('path') not in tem:
        raiz.append(g)
dest.write(sys.argv[2], encoding='utf-8', xml_declaration=True)
PY
}

# Instalações antigas punham os jogos em /userdata/roms/lindbergh/lindbergh/<jogo>: passa para /userdata/roms/lindbergh/<jogo>
migrar_pasta_antiga() {
  local velha="$BASE/lindbergh"
  [ -d "$velha" ] || return 0
  msg "Movendo jogos de $velha para $JOGOS..."
  local item nome
  for item in "$velha"/* "$velha"/.[!.]*; do
    [ -e "$item" ] || continue
    nome="$(basename "$item")"
    if [ "$nome" = gamelist.xml ]; then
      mesclar_gamelist "$item" "$JOGOS/gamelist.xml" && rm -f "$item"
    elif [ -e "$JOGOS/$nome" ] && [ -d "$item" ] && [ -d "$JOGOS/$nome" ]; then
      cp -a -l -n "$item/." "$JOGOS/$nome/" && rm -rf "$item"    # ex.: images/ e videos/
    elif [ -e "$JOGOS/$nome" ]; then
      msg "AVISO: $JOGOS/$nome já existe; deixei $item onde estava"
    else
      mv "$item" "$JOGOS/"
    fi
  done
  rmdir "$velha" 2>/dev/null || msg "AVISO: sobrou coisa em $velha (confira e apague à mão)"
}

instalar_outrun() {
  # Baixa em /tmp (RAM); se não couber, usa /userdata/system
  local dir=/tmp
  [ "$(df -Pm /tmp | awk 'NR==2{print $4}')" -gt 1200 ] 2>/dev/null || dir=/userdata/system
  local arq="$dir/$JOGO_PACOTE"
  if [ -n "${LINDBERGH_JOGO_LOCAL:-}" ]; then   # pacote do jogo já baixado (sem internet)
    msg "Usando pacote do jogo local: $LINDBERGH_JOGO_LOCAL"
    cp "$LINDBERGH_JOGO_LOCAL" "$arq"
  else
    msg "Baixando o OutRun 2 SP SDX (~900 MB) para $dir..."
    rm -f "$arq"
    wget -q --show-progress -O "$arq" "$JOGO_URL" 2>&1 || wget -q -O "$arq" "$JOGO_URL" || { rm -f "$arq"; erro "falha ao baixar $JOGO_URL"; }
  fi
  msg "Conferindo SHA-256 do jogo..."
  echo "$JOGO_SHA256  $arq" | sha256sum -c --quiet - || { rm -f "$arq"; erro "download do jogo corrompido (SHA-256 não confere) — rode de novo"; }
  msg "Descompactando em $JOGOS..."
  # o pacote traz outr2sdx/, images/, videos/ e gamelist.xml na raiz (pacotes antigos: dentro de lindbergh/).
  # Extrai à parte e passa para $JOGOS com hardlinks (rápido, sem ocupar espaço em dobro),
  # juntando o gamelist.xml sem apagar os outros jogos.
  local tmpj="$BASE/.outrun-extraindo" raiz
  rm -rf "$tmpj"
  unsquashfs -q -n -d "$tmpj" "$arq" >/dev/null
  rm -f "$arq"
  raiz="$tmpj"; [ -d "$tmpj/lindbergh/outr2sdx" ] && raiz="$tmpj/lindbergh"
  mesclar_gamelist "$raiz/gamelist.xml" "$JOGOS/gamelist.xml"
  rm -f "$raiz/gamelist.xml"
  cp -a -l -f "$raiz/." "$JOGOS/"
  rm -rf "$tmpj"
  msg "Ajustando permissões..."
  chmod -R u+rwX,go+rX "$JOGOS/outr2sdx"
  chmod +x "$JOGOS/outr2sdx/Jennifer/Jennifer"
  find "$JOGOS/outr2sdx" -type f -size +1k -exec sh -c 'head -c4 "$1" | grep -q "ELF" && chmod +x "$1"' _ {} \;
  msg "OutRun 2 SP SDX instalado em $JOGOS/outr2sdx"
}

SEM_JOGO=0
if [ "${1:-}" = "--sem-jogo" ]; then SEM_JOGO=1; shift; fi

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
migrar_pasta_antiga
# _info.txt: como instalar jogos novos + lista de jogos suportados (sempre atualizado)
if [ -f "$JOGOS/_info.txt" ] && ! cmp -s "$LOADER/sistema/_info.txt" "$JOGOS/_info.txt"; then
  cp "$JOGOS/_info.txt" "$JOGOS/_info.txt.antes-$DATA.bak"
fi
cp "$LOADER/sistema/_info.txt" "$JOGOS/_info.txt"

mkdir -p "$(dirname "$ESCFG")"
[ -f "$ESCFG" ] && cp "$ESCFG" "$ESCFG.antes-$DATA.bak"
sed "s|/userdata/roms/lindbergh/lindbergh-loader/launch.sh|$LOADER/launch.sh|; s|<path>/userdata/roms/lindbergh\(/lindbergh\)\{0,1\}</path>|<path>$JOGOS</path>|" \
  "$LOADER/sistema/es_systems_lindbergh.cfg" > "$ESCFG"

# Sair do jogo com HOTKEY+START ou SELECT+START (evmapy do Batocera)
KEYS="${LINDBERGH_KEYS:-/userdata/system/configs/evmapy/lindbergh.keys}"
mkdir -p "$(dirname "$KEYS")"
[ -f "$KEYS" ] && cp "$KEYS" "$KEYS.antes-$DATA.bak"
sed "s|/userdata/roms/lindbergh/lindbergh-loader/|$LOADER/|g" "$LOADER/sistema/lindbergh.keys" > "$KEYS"

[ "$SEM_JOGO" = 1 ] || instalar_outrun

curl -s -m 5 http://127.0.0.1:1234/reloadgames >/dev/null 2>&1 || true

msg "Instalado! ($VERSAO)"
cat <<EOF

Próximos passos:
  1. Outros jogos: copie a pasta do jogo para $JOGOS/
     com verificação:  python3 -I $LOADER/ferramentas/copia_verificada.py /origem/outr2sdx $JOGOS/outr2sdx
  2. Cada jogo precisa de um arquivo <id>.game na pasta do executável (ex.: outr2sdx.game).
  3. Se o sistema "Sega Lindbergh" não aparecer, reinicie o EmulationStation
     (Menu > Sair > Reiniciar EmulationStation).

Sair do jogo: HOTKEY+START ou SELECT+START (botões do es_input.cfg de cada controle).

Log dos jogos: /userdata/system/logs/lindbergh.log
EOF
