#!/bin/bash
# Batocera Lindbergh — atualização dos controles (v1.1) para quem já tem o Lindbergh instalado
#   - controles iguais ao Batocera 43 (gerados do EmulationStation a cada jogo)
#   - volante centralizado (o carro não puxa mais para o lado)
# O jogo não é baixado nem alterado.
#
# Uso (no terminal do Batocera):
#   curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/atualizar.sh | bash
set -uo pipefail

URL="https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main"
LOADER="${LINDBERGH_LOADER:-/userdata/roms/lindbergh/lindbergh-loader}"
DATA="$(date +%Y%m%d-%H%M%S)"

# arquivo e SHA-256 esperado
ARQUIVOS="
controles_lindbergh.py e137bc34cffd073613b6146606445f7d558d65fad98edfe4f890441e871735c1
centraliza_eixos.py    fea31f3bc9050f9142d77324d43a7d8ee17908dea9787bbb40e38ea1361ba9e2
launch.sh              8a33ba8498ed96d7ccb2de529b3712abe8657883327449a9f86a8c0f00256c6b
"

msg()  { printf '\033[1;33m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m OK\033[0m %s\n' "$*"; }
erro() { printf '\033[1;31mERRO:\033[0m %s\n' "$*" >&2; exit 1; }

[ -f "$LOADER/v2.0/lindbergh" ] || erro "Lindbergh não encontrado em $LOADER — instale primeiro com o install.sh"
[ -f /var/run/lindbergh-jogo.pid ] && erro "tem um jogo Lindbergh aberto — feche o jogo e rode de novo"

TMP="$(mktemp -d /userdata/system/.lindbergh-atualiza.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT

msg "Baixando a atualização..."
echo "$ARQUIVOS" | while read -r nome sha; do
  [ -n "$nome" ] || continue
  baixou=0
  for tentativa in 1 2 3; do
    if curl -fsSL -o "$TMP/$nome" "$URL/$nome" && echo "$sha  $TMP/$nome" | sha256sum -c --quiet - 2>/dev/null; then
      baixou=1; break
    fi
    sleep 2
  done
  [ "$baixou" = 1 ] || { echo "falhou: $nome" > "$TMP/.erro"; break; }
  ok "$nome"
done
[ -f "$TMP/.erro" ] && erro "$(cat "$TMP/.erro") (download incompleto ou arquivo diferente no GitHub) — nada foi alterado"

msg "Guardando os arquivos atuais (*.antes-$DATA.bak)..."
echo "$ARQUIVOS" | while read -r nome sha; do
  [ -n "$nome" ] && [ -f "$LOADER/$nome" ] && cp -p "$LOADER/$nome" "$LOADER/$nome.antes-$DATA.bak"
done

msg "Instalando em $LOADER..."
echo "$ARQUIVOS" | while read -r nome sha; do
  [ -n "$nome" ] || continue
  cp "$TMP/$nome" "$LOADER/$nome" && chmod +x "$LOADER/$nome"
done

msg "Atualização instalada!"
cat <<EOF

Agora:
  1. Configure o controle no EmulationStation (as trocas feitas lá são respeitadas).
  2. Abra o jogo normalmente — os controles são gerados a cada vez que o jogo abre.

Para desfazer: os arquivos antigos ficaram em $LOADER/*.antes-$DATA.bak
EOF
