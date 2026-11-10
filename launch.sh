#!/bin/bash
# Batocera Lindbergh — lança jogos Sega Lindbergh no Batocera 40 (que não tem suporte nativo)
# Chamado pelo EmulationStation: launch.sh /userdata/roms/lindbergh/<jogo>/<pasta>/<id>.game
#
# - Loader: lindbergh-loader v2.0 (lindbergh + lindbergh.so) com libsegaapi/libkswapapi da v2.0.14 (SDL2 + FAudio).
# - A SDL2 32 bits do Batocera 40 não tem X11 ("No available video device"): usa a SDL2 2.30 do Ubuntu 24.04 (v2.0/sdl2/lib).
# - Mesa/GL e demais libs 32 bits: do AppImage oficial do lindbergh-loader v2.1.4 (squashfs-root/usr/lib32).
# - Configuração de cada jogo: lindbergh.conf na pasta do executável (criado a partir de v2.0/lindbergh.conf.modelo).

LOADER="$(dirname "$(readlink -f "$0")")"
GAMEDIR="$(dirname "$1")"
cd "$GAMEDIR" || exit 1
LOG=/userdata/system/logs/lindbergh.log

export DISPLAY="${DISPLAY:-:0}"
export SDL_VIDEODRIVER=x11
export APP_IMG_ROOT="$LOADER/v2.0"     # o loader procura $APP_IMG_ROOT/usr/lib32/lindbergh.so
export LD_LIBRARY_PATH="$LOADER/v2.0/usr/lib32:$LOADER/v2.0/sdl2/lib:$LOADER/squashfs-root/usr/lib32:$LOADER/extra-libs:$LD_LIBRARY_PATH"

# Configuração padrão na primeira vez; sempre em tela cheia
[ -f lindbergh.conf ] || cp "$LOADER/v2.0/lindbergh.conf.modelo" lindbergh.conf
sed -i -E 's/^(\s*FULLSCREEN\s+).*/\11/' lindbergh.conf
mkdir -p /userdata/saves/lindbergh

# O .game pode trazer o nome do executável (ex.: vf5b, dsr, drive.elf). Linhas com # são ignoradas.
RUN="$LOADER/v2.0/lindbergh"
ELF="$(grep -v '^\s*#' "$1" 2>/dev/null | tr -d '\r' | awk 'NF{print $1; exit}')"
[ -n "$ELF" ] && [ -f "$ELF" ] && RUN="$RUN $ELF"

echo "=== INICIO $(date '+%F %T') $1 ===" >>"$LOG"
# 'script' dá um terminal ao jogo, assim a saída não se perde se ele travar
# Sair com HOTKEY+START ou SELECT+START: evmapy do Batocera com /userdata/system/configs/evmapy/lindbergh.keys
# ($2.. = %CONTROLLERSCONFIG% passado pelo ES; o fechar_jogo.sh mata o PID gravado abaixo)
ROM="$1"; shift
# Controles: mapeamento EVDEV gerado do es_input.cfg igual ao Batocera 43 (INPUT_MODE 2)
"$LOADER/controles_lindbergh.py" "$ROM" "$@" >>"$LOG" 2>&1
"$LOADER/evmapy_lindbergh.py" "$ROM" "$@" >>"$LOG" 2>&1
script -qefc "$RUN" /dev/null >>"$LOG" 2>&1 &
JOGO=$!
echo "$JOGO" >/var/run/lindbergh-jogo.pid
# EVDEV: manda a posição de repouso dos eixos (senão o volante começa todo virado)
"$LOADER/centraliza_eixos.py" "$GAMEDIR/lindbergh.conf" "$JOGO" >>"$LOG" 2>&1 &
wait "$JOGO"
CODIGO=$?
rm -f /var/run/lindbergh-jogo.pid
batocera-evmapy stop >/dev/null 2>&1
echo "=== JOGO SAIU: codigo $CODIGO em $(date +%T) ===" >>"$LOG"
