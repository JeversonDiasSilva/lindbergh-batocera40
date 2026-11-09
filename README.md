# Sega Lindbergh no Batocera 40

Suporte a jogos **Sega Lindbergh** no **Batocera 40**, que não traz esse sistema de fábrica.

O instalador coloca o **lindbergh-loader v2.0** já ajustado para o Batocera 40, registra o sistema
**"Sega Lindbergh"** no EmulationStation e configura a saída do jogo pelo controle.

> ⚠️ **Nenhum jogo vem incluído.** Use cópias dos seus próprios jogos.

---

## 🚀 Instalação

No terminal do Batocera (pelo SSH ou em **F1 > Terminal**), rode:

```bash
curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/install.sh | bash
```

Depois **reinicie o EmulationStation** (Menu > Sair > Reiniciar EmulationStation) para o sistema
"Sega Lindbergh" aparecer.

O mesmo comando também serve para **atualizar**: a instalação anterior é guardada em
`/userdata/roms/lindbergh/lindbergh-loader.antes-<data>`.

### Instalar sem internet

Baixe o `install.sh` e o `lindbergh-loader-batocera40.squashfs` da
[página de releases](https://github.com/JeversonDiasSilva/lindbergh-batocera40/releases), coloque os dois
no Batocera e rode:

```bash
bash install.sh lindbergh-loader-batocera40.squashfs
```

O instalador confere o SHA-256 do pacote antes de instalar.

---

## 🎮 Adicionar os jogos

Copie a pasta de cada jogo para:

```
/userdata/roms/lindbergh/lindbergh/
```

Cada jogo precisa de um arquivo **`<id>.game`** na pasta do executável, por exemplo
`outr2sdx/Jennifer/outr2sdx.game`. A lista de IDs fica em `/userdata/roms/lindbergh/lindbergh/_info.txt`.

### Cópia verificada (recomendado para pendrive / HD USB)

Discos USB instáveis podem corromper arquivos na cópia, e o jogo fecha sozinho ao carregar a fase.
A cópia verificada lê cada arquivo até ter duas leituras iguais:

```bash
curl -fsSL https://raw.githubusercontent.com/JeversonDiasSilva/lindbergh-batocera40/main/install.sh | bash -s -- --jogo /caminho/do/outr2sdx
```

---

## 🕹️ Controles

| Ação | Botões |
|---|---|
| **Sair do jogo** | **SELECT + START** ou **HOTKEY + START** |

A saída funciona como nos outros sistemas do Batocera e usa os botões que você mapeou para cada controle
no EmulationStation. Na maioria dos controles o Hotkey é o próprio Select.

Os jogos já vêm em **free play**, sem precisar de ficha.

---

## 🏁 Jogos testados

| Jogo | Situação |
|---|---|
| OutRun 2 SP SDX (Rev A) | ✅ Corrida completa, controle Xbox, 1920x1080 sem bordas |
| R-Tuned: Ultimate Street Racing | ✅ Abre e chega à escolha de carro |

---

## 🔧 O que o pacote resolve no Batocera 40

- **Loader v2.0** (`lindbergh` + `lindbergh.so`), com `libsegaapi`/`libkswapapi` da v2.0.14 (áudio SDL2 + FAudio).
- **SDL2 2.30 com X11** (Ubuntu 24.04): a SDL2 32 bits do Batocera 40 vem sem X11, e o loader falha com
  `SDL could not initialize! No available video device`.
- **Mesa/GL 32 bits** do AppImage oficial do lindbergh-loader.
- **`lindbergh.conf` padrão**: 1920x1080, tela cheia, controle por SDL (`INPUT_MODE 0`), free play e
  `SKIP_OUTRUN_CABINET_CHECK 1`.
- **Saída por SELECT/HOTKEY + START** com o evmapy do próprio Batocera
  (`/userdata/system/configs/evmapy/lindbergh.keys`).

### Arquivos instalados

| Caminho | O que é |
|---|---|
| `/userdata/roms/lindbergh/lindbergh-loader/` | Loader, bibliotecas e scripts |
| `/userdata/roms/lindbergh/lindbergh/` | Pasta dos jogos |
| `/userdata/system/configs/emulationstation/es_systems_lindbergh.cfg` | Sistema no EmulationStation |
| `/userdata/system/configs/evmapy/lindbergh.keys` | Botões para sair do jogo |
| `/userdata/system/logs/lindbergh.log` | Log dos jogos |

---

## ❓ Problemas comuns

- **O jogo fecha ao carregar a corrida ou a fase**: quase sempre são arquivos corrompidos na cópia
  (USB instável). Copie de novo com a [cópia verificada](#cópia-verificada-recomendado-para-pendrive--hd-usb).
- **Tela cinza ou o jogo não abre**: veja o log em `/userdata/system/logs/lindbergh.log`.
- **O jogo pede ficha**: deixe `FREEPLAY 1` no `lindbergh.conf` da pasta do jogo.
- **O sistema não aparece no menu**: reinicie o EmulationStation e confira se existe pelo menos um
  arquivo `.game` dentro de `/userdata/roms/lindbergh/lindbergh/`.

---

## 📜 Créditos e licenças

- [lindbergh-loader](https://github.com/lindbergh-loader/lindbergh-loader), do Lindbergh Development Team
  (CC BY-NC-SA 4.0).
- SDL2, FAudio e demais bibliotecas: dos seus respectivos autores (ver `LICENCAS.md` no pacote).
- Adaptação para o Batocera 40: [JeversonDiasSilva](https://github.com/JeversonDiasSilva).

Projeto sem fins lucrativos e sem ligação com a SEGA. Todas as marcas pertencem aos seus donos.
