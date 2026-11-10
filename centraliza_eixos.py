#!/usr/bin/python3
# Centraliza os eixos analógicos no início do jogo (modo EVDEV).
# O loader v2.0 só atualiza um ANALOGUE_x quando chega um evento do eixo; até lá o canal fica em 0
# (no OutRun = volante todo virado). Com o analógico parado o kernel não manda evento nenhum.
# Aqui: espera o jogo abrir o controle e injeta no próprio /dev/input/eventN a posição atual de cada
# eixo mapeado como ANALOGUE_x (volante no centro, pedais soltos).
# Uso: centraliza_eixos.py lindbergh.conf PID_DO_JOGO
import os, re, sys, time
import evdev
from evdev import ecodes

conf, pid_raiz = sys.argv[1], int(sys.argv[2])

eixos = {}  # caminho -> [codigos]
for l in open(conf, errors='replace'):
    m = re.match(r'\s*ANALOGUE_\d+\s+(/dev/input/event\d+):ABS(?:_NEG)?:(\d+)\s*$', l)
    if m:
        eixos.setdefault(m.group(1), []).append(int(m.group(2)))
if not eixos:
    sys.exit(0)

def descendentes(raiz):
    filhos = {}
    for p in os.listdir('/proc'):
        if p.isdigit():
            try:
                ppid = int(open(f'/proc/{p}/stat').read().rsplit(')', 1)[1].split()[1])
                filhos.setdefault(ppid, []).append(int(p))
            except OSError:
                pass
    res, fila = [], [raiz]
    while fila:
        x = fila.pop()
        res.append(x)
        fila += filhos.get(x, [])
    return res

def aberto_pelo_jogo(caminho):
    alvo = os.path.realpath(caminho)
    for p in descendentes(pid_raiz):
        try:
            for fd in os.listdir(f'/proc/{p}/fd'):
                if os.path.realpath(f'/proc/{p}/fd/{fd}') == alvo:
                    return True
        except OSError:
            pass
    return False

fim = time.time() + 120
pendentes = dict(eixos)
while pendentes and time.time() < fim:
    if not os.path.exists(f'/proc/{pid_raiz}'):
        sys.exit(0)
    for caminho in list(pendentes):
        if aberto_pelo_jogo(caminho):
            time.sleep(1.5)  # deixa a thread do controle começar a ler
            try:
                d = evdev.InputDevice(caminho)
                for code in pendentes[caminho]:
                    info = d.absinfo(code)
                    atual = info.value
                    passo = max(2 * info.fuzz + 1, (info.max - info.min) // 100, 1)
                    desvio = atual + passo if atual + passo <= info.max else atual - passo
                    for v in (desvio, atual):
                        d.write(ecodes.EV_ABS, code, v)
                        d.write(ecodes.EV_SYN, ecodes.SYN_REPORT, 0)
                        time.sleep(0.05)
                    print(f'centraliza eixos: {caminho} ABS {code} = {atual} (min {info.min} max {info.max})', flush=True)
                d.close()
            except OSError as e:
                print(f'centraliza eixos: falhou em {caminho}: {e}', flush=True)
            del pendentes[caminho]
    time.sleep(0.5)
