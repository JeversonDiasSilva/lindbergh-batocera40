#!/usr/bin/python3
# Gera o mapeamento EVDEV (INPUT_MODE 2) do lindbergh.conf a partir do es_input.cfg,
# DA MESMA MANEIRA que o Batocera 43.1 (configgen/generators/lindbergh/lindberghGenerator.py):
# as funções setup_joysticks_evdev e getMappingForJoystickOrWheel abaixo são cópia do v43.1,
# só com uma camada de adaptação para o controllersConfig do Batocera 40.
# Uso: controles_lindbergh.py ROM.game [%CONTROLLERSCONFIG% do ES: -p1index 0 -p1guid ... ]
from __future__ import annotations
import logging, sys
from pathlib import Path
from typing import Any, Literal

sys.path.insert(0, '/usr/lib/python3.11/site-packages/configgen')
import controllersConfig as controllers

logging.basicConfig(level=logging.DEBUG, format='controles lindbergh: %(message)s')
_logger = logging.getLogger('controles_lindbergh')
HOME = Path('/userdata/system')

class InvalidConfiguration(Exception): pass
class BatoceraException(Exception): pass

# ---- adaptação v40 -> v43 ----
class _Cfg:
    use_guns = False     # pistolas: não tratado aqui
    use_wheels = False   # volantes: o v43 só usa o mapa "wheel" com a opção use_wheels ligada
class _System:
    config = _Cfg()

class Pad:
    """Controller do v40 com a interface usada pelo gerador do v43."""
    def __init__(self, c):
        self.c = c
        self.inputs = c.inputs
        self.device_path = c.dev
        self.guid = c.guid
        self.name = c.realName

    # cópia de controller.py (v43.1)
    def get_mapping_axis_relaxed_values(self):
        import evdev
        cache_file = Path(HOME / ".sdl2" / f"{self.guid}_{self.name}.cache")
        if not cache_file.exists():
            return {}
        try:
            cache_content = cache_file.read_text(encoding="utf-8").splitlines()
            n = int(cache_content[0])
            relaxed_values = [int(cache_content[i]) for i in range(1, n+1)]
            caps = evdev.InputDevice(self.device_path).capabilities()
            code_values = {}
            i = 0
            for code, _ in caps[evdev.ecodes.EV_ABS]:
                if code < evdev.ecodes.ABS_HAT0X:
                    code_values[code] = relaxed_values[i]
                    i = i+1
        except Exception as e:
            _logger.debug("cache sdl2 ignorado: %s", e)
            return {}
        res = {}
        for x, input in self.inputs.items():
            if input.type == "axis":
                if (val := code_values.get(int(input.code))) is not None:
                    res[x] = { "centered":  val > -4000 and val < 4000, "reversed": val > 4000 }
                else:
                    res[x] = { "centered":  True, "reversed": False }
        return res

class Gerador:
    def __init__(self):
        self.conf = {}
    def setConf(self, conf, key, value):
        conf[key] = value

    def setup_joysticks_evdev(
        self,
        conf: dict[str, Any],
        system: Emulator,
        shortRomName: str,
        guns: Guns,
        wheels: DeviceInfoMapping,
        playersControllers: Controllers,
        /,
    ) -> None:
        # button that are common to all players
        noPlayerButton = {
            "TEST_BUTTON": True,
            "ANALOGUE_1":  True,
            "ANALOGUE_2":  True,
            "ANALOGUE_3":  True,
            "ANALOGUE_4":  True,
            "ANALOGUE_5":  True,
            "ANALOGUE_6":  True,
            "ANALOGUE_7":  True,
            "ANALOGUE_8":  True,
        }

        # configure joysticks if no gun configured for the user
        nplayer = 1
        continuePlayers = True
        for pad in playersControllers:
            # Handle two players / controllers only, don't do if already configured for guns
            if nplayer <= 2 and continuePlayers and not (system.config.use_guns and len(guns) >= nplayer):
                relaxValues = pad.get_mapping_axis_relaxed_values()

                ### choose the adapted mapping
                if system.config.use_wheels:
                    if pad.device_path in wheels:
                        lindberghCtrl = self.getMappingForJoystickOrWheel(shortRomName, "wheel", nplayer, pad, True)
                        _logger.debug("lindbergh wheel mapping for player %s", nplayer)
                    else:
                        lindberghCtrl = self.getMappingForJoystickOrWheel(shortRomName, "pad", nplayer, pad, False)
                        _logger.debug("lindbergh pad mapping for player %s (not a wheel device)", nplayer)
                elif system.config.use_guns:
                    lindberghCtrl = self.getMappingForJoystickOrWheel(shortRomName, "gun", nplayer, pad, False)
                    _logger.debug("lindbergh gun mapping for player %s", nplayer)
                else:
                    lindberghCtrl = self.getMappingForJoystickOrWheel(shortRomName, "pad", nplayer, pad, False)
                    _logger.debug("lindbergh pad mapping for player %s", nplayer)

                # some games must be configured for player 1 only (cause it uses some buttons of the player 2), so stop after player 1
                if nplayer == 1:
                    for input_name in lindberghCtrl:
                        if lindberghCtrl[input_name].endswith("_ON_PLAYER_2"):
                            continuePlayers = False

                # checker on buttons mapping (just to control we have no duplicates)
                x = {}
                for input_name in lindberghCtrl:
                    if lindberghCtrl[input_name] in x:
                        raise InvalidConfiguration(f"duplicate configuration key for {input_name} with value {lindberghCtrl[input_name]}")
                    x[lindberghCtrl[input_name]] = True

                ### configure each input
                controller_name = pad.device_path
                for input_name in lindberghCtrl:

                    # coin is only for player 1
                    if lindberghCtrl[input_name] == "COIN" and nplayer > 1:
                        continue

                    input_base_name = input_name
                    if input_name == "joystick1right":
                        input_base_name = "joystick1left"
                    if input_name == "joystick1down":
                        input_base_name = "joystick1up"
                    if input_name == "joystick2right":
                        input_base_name = "joystick2left"
                    if input_name == "joystick2down":
                        input_base_name = "joystick2up"

                    if input_base_name in pad.inputs and (pad.inputs[input_base_name].code is not None or pad.inputs[input_base_name].type == "hat"):
                        button_name = lindberghCtrl[input_name]

                        # some buttons of player1 are mapped on the player2...
                        player_input = nplayer
                        if button_name.endswith("_ON_PLAYER_2"):
                            button_name = button_name[:-12]
                            player_input = 2
                        ###

                        if pad.inputs[input_base_name].type == "button":
                            input_value = f"KEY:{pad.inputs[input_base_name].code}"
                            if button_name in noPlayerButton:
                                if nplayer == 1:
                                    self.setConf(conf, f"{button_name}", f"{controller_name}:{input_value}")
                            else:
                                if button_name.startswith("ANALOGUE_"):
                                    if nplayer == 1:
                                        self.setConf(conf, f"{button_name}", f"{controller_name}:{input_value}")
                                else:
                                    self.setConf(conf, f"PLAYER_{player_input}_{button_name}", f"{controller_name}:{input_value}")
                        elif pad.inputs[input_base_name].type == "axis":
                            if input_name in relaxValues and relaxValues[input_name]["reversed"]:
                                input_value = f"ABS_NEG:{pad.inputs[input_base_name].code}"
                            else:
                                input_value = f"ABS:{pad.inputs[input_base_name].code}"
                            if button_name.startswith("ANALOGUE_"):
                                if nplayer == 1:
                                    self.setConf(conf, f"{button_name}", f"{controller_name}:{input_value}")
                            else:
                                # here
                                minmax_value = "MAX"
                                if input_name == "joystick1left" or input_name == "joystick1up" or input_name == "joystick2left" or input_name == "joystick2up" or input_name == "left" or input_name == "up":
                                    minmax_value = "MIN"
                                # reversed axis
                                if input_name in relaxValues and relaxValues[input_name]["reversed"]:
                                    if minmax_value == "MAX":
                                        minmax_value = "MIN"
                                    else:
                                        minmax_value = "MAX"
                                # set
                                self.setConf(conf, f"PLAYER_{player_input}_{button_name}", f"{controller_name}:{input_value}:{minmax_value}")
                        elif pad.inputs[input_base_name].type == "hat":
                            if pad.inputs[input_base_name].value == "1" or pad.inputs[input_base_name].value == "4": # up or down
                                # 16 is the HAT0 code
                                input_value = f"ABS:{16+1+int(pad.inputs[input_base_name].id)*2}"
                            else:
                                input_value = f"ABS:{16+int(pad.inputs[input_base_name].id)*2}"
                            if button_name.startswith("ANALOGUE_"):
                                if nplayer == 1:
                                    self.setConf(conf, f"{button_name}", f"{controller_name}:{input_value}")
                            else:
                                if pad.inputs[input_base_name].value == "1" or pad.inputs[input_base_name].value == "8": # up or left
                                    input_value += ":MIN"
                                else:
                                    input_value += ":MAX"
                                self.setConf(conf, f"PLAYER_{player_input}_{button_name}", f"{controller_name}:{input_value}")
                        else:
                            raise BatoceraException(f"invalid input type: {pad.inputs[input_base_name].type}")
                nplayer += 1

    def getMappingForJoystickOrWheel(  # noqa: RET503
        self,
        shortRomName: str,
        deviceType: Literal['wheel', 'gun', 'pad'],
        nplayer: int,
        pad: Controller,
        isRealWheel: bool,
        /,
    ) -> dict[str, str]:
        lindberghCtrl_pad = {
            "a":              "BUTTON_2",
            "b":              "BUTTON_1",
            "x":              "BUTTON_4",
            "y":              "BUTTON_3",
            "start":          "BUTTON_START",
            "select":         "COIN",
            "up":             "BUTTON_UP",
            "down":           "BUTTON_DOWN",
            "left":           "BUTTON_LEFT",
            "right":          "BUTTON_RIGHT",
            "joystick1up":    "ANALOGUE_2",
            "joystick1left":  "ANALOGUE_1",
            "pageup":         "BUTTON_5",
            "pagedown":       "BUTTON_6",
            "l2":             "BUTTON_7",
            "r2":             "BUTTON_8",
            "l3":             "BUTTON_SERVICE"
        }

        lindberghCtrl_pad_driving = {
            "x":        "BUTTON_DOWN",              # view change
            "pageup":   "BUTTON_DOWN_ON_PLAYER_2",  # gear down
            "pagedown": "BUTTON_UP_ON_PLAYER_2",    # gear up
            "l2":       "ANALOGUE_3",               # brake
            "r2":       "ANALOGUE_2",               # gas
        }

        lindberghCtrl_pad_abc = {
            "a":  "BUTTON_1",   # gun trigger
            "b":  "BUTTON_2",   # missile
            "x":  "BUTTON_3",   # climax switch
            "r2": "ANALOGUE_3", # throttle
        }

        # the same mapping for a wheel or a pad for a wheel game should do the job
        lindberghCtrl_wheel = {
            "a":              "BUTTON_2",
            "b":              "BUTTON_1",
            "x":              "BUTTON_4",
            "y":              "BUTTON_3",
            "start":          "BUTTON_START",
            "select":         "COIN",
            "left":           "BUTTON_LEFT",
            "right":          "BUTTON_RIGHT",
            "joystick1left":  "ANALOGUE_1",
            "pageup":         "BUTTON_DOWN", # gear down
            "pagedown":       "BUTTON_UP",   # gear up
            "l2":             "ANALOGUE_3",
            "r2":             "ANALOGUE_2",
            "l3":             "BUTTON_SERVICE"
        }

        lindberghCtrl_gun = {
            "a":              "BUTTON_2",
            "b":              "BUTTON_1",
            "x":              "BUTTON_4",
            "y":              "BUTTON_3",
            "start":          "BUTTON_START",
            "select":         "COIN",
            "up":             "BUTTON_UP",
            "down":           "BUTTON_DOWN",
            "left":           "BUTTON_LEFT",
            "right":          "BUTTON_RIGHT",
            "joystick1up":    "ANALOGUE_2",
            "joystick1left":  "ANALOGUE_1",
            "pageup":         "BUTTON_5",
            "pagedown":       "BUTTON_6",
            "l2":             "BUTTON_7",
            "r2":             "BUTTON_8",
            "l3":             "BUTTON_SERVICE"
        }

        # mapping specific to games - wheel
        _logger.debug("lindberg mapping for game %s", shortRomName)

        if shortRomName == "hdkotr" or "harley" in shortRomName:
            lindberghCtrl_wheel["x"]  = "BUTTON_2"   # change view
            lindberghCtrl_wheel["l2"] = "ANALOGUE_4"
            lindberghCtrl_wheel["r2"] = "ANALOGUE_1"
            lindberghCtrl_wheel["joystick1left"] = "ANALOGUE_2"
            del lindberghCtrl_wheel["a"]
            del lindberghCtrl_wheel["y"]
            lindberghCtrl_wheel["pageup"]   = "BUTTON_4"
            lindberghCtrl_wheel["pagedown"] = "BUTTON_3"

        if shortRomName == "rtuned":
            lindberghCtrl_wheel["x"] = "BUTTON_DOWN"          # change view
            lindberghCtrl_wheel["a"] = "BUTTON_RIGHT"         # boost 1
            lindberghCtrl_wheel["y"] = "BUTTON_1_ON_PLAYER_2" # boost 2
            del lindberghCtrl_wheel["right"]

        if shortRomName.startswith("initiad"):
            lindberghCtrl_wheel["x"]    = "BUTTON_1"    # change view
            lindberghCtrl_wheel["up"]   = "BUTTON_UP"   # menu up
            lindberghCtrl_wheel["down"] = "BUTTON_DOWN" # menu down
            del lindberghCtrl_wheel["b"]

        if shortRomName.startswith("hummer"):
            lindberghCtrl_wheel["a"] = "BUTTON_DOWN_ON_PLAYER_2" # boost
            lindberghCtrl_wheel["x"] = "BUTTON_DOWN"             # change view
            del lindberghCtrl_wheel["pageup"]

        if shortRomName.startswith("segartv"):
            lindberghCtrl_wheel["a"] = "BUTTON_1_ON_PLAYER_2" # boost
            lindberghCtrl_wheel["x"] = "BUTTON_DOWN"          # change view
            del lindberghCtrl_wheel["pageup"]

        if shortRomName.startswith("outr"):
            lindberghCtrl_wheel["x"] = "BUTTON_DOWN" # view change

        # button up/down on player 2
        if shortRomName == "rtuned" or shortRomName.startswith(("segartv", "outr", "initiad")):
            lindberghCtrl_wheel["pageup"]   = "BUTTON_DOWN_ON_PLAYER_2"
            lindberghCtrl_wheel["pagedown"] = "BUTTON_UP_ON_PLAYER_2"

        # mapping specific to games - pad with dict for driving + ABC

        if shortRomName.startswith("outr"):
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["down"]

        if shortRomName.startswith("hummer"):
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            lindberghCtrl_pad["a"]        = "BUTTON_DOWN_ON_PLAYER_2" # boost
            lindberghCtrl_pad["pageup"]   = "BUTTON_5"
            lindberghCtrl_pad["pagedown"] = "BUTTON_6"
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["down"]

        if shortRomName.startswith("initiad"):
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            lindberghCtrl_pad["x"] = "BUTTON_1"                # view change (not BUTTON_DOWN)
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["b"]

        if shortRomName == "rtuned":
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            lindberghCtrl_pad["a"] = "BUTTON_RIGHT"            # boost
            lindberghCtrl_pad["y"] = "BUTTON_1_ON_PLAYER_2"    # boost 2
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["right"]
            del lindberghCtrl_pad["down"]

        if shortRomName.startswith("segartv"):
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            lindberghCtrl_pad["a"] = "BUTTON_1_ON_PLAYER_2"    # boost
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["down"]

        if shortRomName == "hdkotr" or "harley" in shortRomName:
            lindberghCtrl_pad.update(lindberghCtrl_pad_driving)
            lindberghCtrl_pad["joystick1left"] = "ANALOGUE_2"  # steer (swapped)
            lindberghCtrl_pad["r2"] = "ANALOGUE_1"             # gas (swapped)
            lindberghCtrl_pad["l2"] = "ANALOGUE_4"             # brake (swapped)
            lindberghCtrl_pad["x"]  = "BUTTON_2"               # view change
            lindberghCtrl_pad["pageup"]   = "BUTTON_4"         # gear down
            lindberghCtrl_pad["pagedown"] = "BUTTON_3"         # gear up
            del lindberghCtrl_pad["joystick1up"]
            del lindberghCtrl_pad["a"]
            del lindberghCtrl_pad["y"]

        if shortRomName.startswith("abcli"):
            lindberghCtrl_pad.update(lindberghCtrl_pad_abc)
            del lindberghCtrl_pad["l2"]
            del lindberghCtrl_pad["y"]
        ###

        # remap buttons if for non real wheel
        if deviceType == "wheel" and not isRealWheel:
            x = None
            y = None
            l = None  # noqa: E741
            r = None
            if "x" in lindberghCtrl_wheel:
                x = lindberghCtrl_wheel["x"]
                del lindberghCtrl_wheel["x"]
            if "y" in lindberghCtrl_wheel:
                y = lindberghCtrl_wheel["y"]
                del lindberghCtrl_wheel["y"]
            if "pageup" in lindberghCtrl_wheel:
                l = lindberghCtrl_wheel["pageup"]  # noqa: E741
                del lindberghCtrl_wheel["pageup"]
            if "pagedown" in lindberghCtrl_wheel:
                r = lindberghCtrl_wheel["pagedown"]
                del lindberghCtrl_wheel["pagedown"]
            if x is not None:
                lindberghCtrl_wheel["pageup"] = x # view     ## free x and y for gear up/down
            if y is not None:
                lindberghCtrl_wheel["b"]      = y # action 2 ## free x and y for gear up/down
            if r is not None:
                lindberghCtrl_wheel["x"]      = r
            if l is not None:
                lindberghCtrl_wheel["y"]      = l
        ####

        # pads without l2, but with l as a button, important for wheel
        if "l2" not in pad.inputs and "pageup" in pad.inputs and pad.inputs["pageup"].type == "button":
            lindberghCtrl_wheel["pageup"] = lindberghCtrl_wheel["l2"]
            del lindberghCtrl_wheel["l2"]
        # pads without r2, but with r as a button
        if "r2" not in pad.inputs and "pagedown" in pad.inputs and pad.inputs["pagedown"].type == "button":
            lindberghCtrl_wheel["pagedown"] = lindberghCtrl_wheel["r2"]
            del lindberghCtrl_wheel["r2"]

        # some pads have not analog axis, on some games, prefer the dpad
        if not shortRomName.startswith("vf5") and not shortRomName.startswith("vt"): # all but vf5 and vt3
            # pads without joystick1left, but with a hat
            if "joystick1left" not in pad.inputs and "left" in pad.inputs and (pad.inputs["left"].type == "hat" or pad.inputs["left"].type == "axis"):
                if "joystick1left" in lindberghCtrl_wheel:
                    lindberghCtrl_wheel["left"] = lindberghCtrl_wheel["joystick1left"]
                    if "right" in lindberghCtrl_wheel:
                        del lindberghCtrl_wheel["right"]
                    del lindberghCtrl_wheel["joystick1left"]
                if "joystick1left" in lindberghCtrl_pad:
                    lindberghCtrl_pad["left"] = lindberghCtrl_pad["joystick1left"]
                    if "right" in lindberghCtrl_pad:
                        del lindberghCtrl_pad["right"]
                    del lindberghCtrl_pad["joystick1left"]

            # pads without joystick1up, but with a hat
            if "joystick1up" not in pad.inputs and "up" in pad.inputs and (pad.inputs["up"].type == "hat" or pad.inputs["up"].type == "axis"):
                if "joystick1up" in lindberghCtrl_pad:
                    lindberghCtrl_pad["up"] = lindberghCtrl_pad["joystick1up"]
                    if "down" in lindberghCtrl_pad:
                        del lindberghCtrl_pad["down"]
                    del lindberghCtrl_pad["joystick1up"]
        ###

        # choose mapping
        if deviceType == "gun":
            # adjustment for player 2 gun
            for x in lindberghCtrl_gun:
                if lindberghCtrl_gun[x] == "ANALOGUE_1" and nplayer == 2:
                    lindberghCtrl_gun[x] = "ANALOGUE_3"
                if lindberghCtrl_gun[x] == "ANALOGUE_2" and nplayer == 2:
                    lindberghCtrl_gun[x] = "ANALOGUE_4"
            return lindberghCtrl_gun

        if deviceType == "wheel":
            return lindberghCtrl_wheel

        if deviceType == "pad":
            return lindberghCtrl_pad


# ---- main ----
def carregar_controles(args):
    cis = {}
    for i in range(0, len(args) - 1, 2):
        k, v = args[i], args[i + 1]
        if k.startswith('-p') and k[2:3].isdigit():
            cis.setdefault(int(k[2]), {})[k[3:]] = v
    lista = [cis[n] for n in sorted(cis) if cis[n].get('devicepath')]
    if not lista:   # lançado sem o ES: usa os controles conectados
        import evdev
        for cam in sorted(evdev.list_devices(), key=lambda p: int(p.rsplit('event', 1)[1])):
            d = evdev.InputDevice(cam)
            if evdev.ecodes.BTN_START in d.capabilities().get(evdev.ecodes.EV_KEY, []):
                i = d.info   # GUID SDL: bus, vendor, product, version (16 bits little-endian + 0000)
                guid = ''.join(f'{x & 0xff:02x}{x >> 8:02x}0000' for x in (i.bustype, i.vendor, i.product, i.version))
                lista.append({'index': str(len(lista)), 'guid': guid, 'name': d.name, 'devicepath': cam,
                              'nbbuttons': '0', 'nbhats': '0', 'nbaxes': '0'})
    for c in lista:
        for k in ('index', 'guid', 'name', 'devicepath', 'nbbuttons', 'nbhats', 'nbaxes'):
            c.setdefault(k, '')
    jog = controllers.loadControllerConfig(lista)
    return [Pad(jog[k]) for k in sorted(jog) if jog[k].dev]

INICIO = '# === CONTROLES GERADOS (igual Batocera 43) - nao editar abaixo ==='

def gravar(confpath, valores):
    linhas = confpath.read_text(errors='replace').splitlines()
    if INICIO in linhas:
        linhas = linhas[:linhas.index(INICIO)]
    while linhas and not linhas[-1].strip():
        linhas.pop()
    novas = []
    for l in linhas:
        chave = l.split()[0] if l.strip() and not l.lstrip().startswith('#') else ''
        if chave == 'INPUT_MODE':
            l = 'INPUT_MODE 2'
        elif chave.startswith(('PLAYER_', 'ANALOGUE_')) or chave == 'TEST_BUTTON':
            l = '# ' + l          # comenta como o v43 faz
        novas.append(l)
    if not any(l.split()[:1] == ['INPUT_MODE'] for l in novas):
        novas.append('INPUT_MODE 2')
    novas += ['', INICIO] + [f'{k} {v}' for k, v in valores.items()]
    confpath.write_text('\n'.join(novas) + '\n')

def main():
    rom = Path(sys.argv[1])
    confpath = rom.parent / 'lindbergh.conf'
    shortRomName = rom.stem.lower()
    pads = carregar_controles(sys.argv[2:])
    _logger.info("jogo=%s controles=%s", shortRomName, [(p.name, p.device_path) for p in pads])
    if not pads:
        _logger.info("nenhum controle: lindbergh.conf mantido como esta")
        return
    g = Gerador()
    g.setup_joysticks_evdev(g.conf, _System(), shortRomName, [], {}, pads)
    gravar(confpath, g.conf)
    for k, v in g.conf.items():
        _logger.info("  %s %s", k, v)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        _logger.error("falhou, lindbergh.conf mantido: %s", e)
