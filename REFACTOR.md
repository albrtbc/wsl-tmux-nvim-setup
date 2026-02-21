---
feature: installer-refactor
phase: planning
status: draft
created: 2026-02-21
updated: 2026-02-21
author: albrtbc
---

# REFACTOR — Plan de mejora del instalador

## 1. Arquitectura actual

```
bin/install.sh          ← curl + bash entry point
  └─ auto_install/
       ├─ main.py       ← TUI curses (seleccion + ejecucion)
       ├─ components.json← registro de componentes
       └─ components/    ← 9 scripts bash independientes
```

**Flujo**: `curl install.sh | bash` → clona repo → copia a `~/bin` → lanza `main.py` →
el usuario selecciona componentes con curses → se ejecutan secuencialmente →
resumen OK/FAILED.

**Lo que funciona bien**:
- Anadir un componente = 1 script + 1 linea en JSON. Muy bajo friccion.
- Scripts standalone: se pueden ejecutar manualmente con `REPO_DIR=... bash install_X.sh`.
- Separacion limpia entre UI (main.py) y logica (shell scripts).
- Bootstrap de un solo comando.

---

## 2. Bugs pendientes (no arreglados todavia)

### 2.1 Sin orden de dependencias
`components.json` no declara dependencias. Si el usuario selecciona Neovim sin
Dependencies, falla (`nvim: command not found`). El orden depende de la posicion
en el array, pero el usuario puede deseleccionar Dependencies.

### 2.2 nerdfont-install.sh se descarga a si mismo
`install_nerdfonts.sh` hace `curl | sh` del script en GitHub raw en vez de usar
`$REPO_DIR/bin/nerdfont-install.sh`. Esto significa que usa la version publicada
en `main`, no la local. Si editas el script y no has hecho push, la version vieja
se ejecuta.

### 2.3 El alias gasbo se sobreescribe
`bin/install.sh` anade `alias gasbo=...` a `~/.bashrc`. Pero `install_dependencies.sh`
hace `cp "$REPO_DIR/.bashrc" ~/.bashrc"`, lo que sobreescribe el archivo completo
y elimina el alias recien anadido. El orden de ejecucion importa y no esta protegido.

### 2.4 Sin deteccion de "ya instalado"
Cada ejecucion reinstala todo desde cero. No hay `command -v lazygit` para saltarse
lo que ya esta presente. Esto hace que re-ejecutar sea lento e innecesario.

### 2.5 El TUI no hace scroll
Si hay mas componentes que filas en la terminal, `main.py` lanza `RuntimeError`.
Limite practico: ~15 componentes en una terminal estandar.

---

## 3. Mejoras propuestas

### Tier 1 — Quick wins (1-2 horas cada una)

#### T1.1 Declarar dependencias en components.json
```json
{
  "name": "Neovim",
  "script": "install_nvim.sh",
  "depends_on": ["Dependencies", "NerdFonts"]
}
```
En `main.py`, al confirmar la seleccion: auto-incluir las dependencias recursivamente
y ordenar topologicamente antes de ejecutar.

#### T1.2 Deteccion de "ya instalado"
Anadir campo `check_command` por componente:
```json
{
  "name": "Lazygit",
  "script": "install_lazygit.sh",
  "check_command": "lazygit --version"
}
```
Si `check_command` sale con exit 0, mostrar `[SKIP] Lazygit ya instalado` y no
ejecutar el script. Anadir flag `--force` para reinstalar de todas formas.

#### T1.3 Arreglar nerdfont-install.sh
Cambiar `install_nerdfonts.sh` para que ejecute `$REPO_DIR/bin/nerdfont-install.sh`
directamente en vez de hacer curl al raw de GitHub.

#### T1.4 Proteger .bashrc del overwrite
En `install_dependencies.sh`, en vez de `cp .bashrc ~/.bashrc`, hacer merge:
1. Copiar el `.bashrc` del repo.
2. Preservar las lineas que `install.sh` anadio (el alias gasbo, el PATH).
O mejor: mover el alias gasbo y el PATH al propio `.bashrc` del repo para que
siempre esten incluidos.

---

### Tier 2 — Modernizar el TUI (1 fin de semana)

#### T2.1 Reemplazar curses por questionary + rich

**questionary** para la seleccion interactiva (reemplaza las 75 lineas de curses):
```python
import questionary

selected = questionary.checkbox(
    "Selecciona componentes a instalar:",
    choices=[c["name"] for c in components]
).ask()
```

**rich** para el output durante la instalacion:
```python
from rich.console import Console
from rich.table import Table

console = Console()
console.print("[bold green][+][/] Lazygit instalado correctamente")

# Tabla resumen al final
table = Table(title="Resumen de instalacion")
table.add_column("Componente")
table.add_column("Estado")
table.add_row("Lazygit", "[green]OK[/green]")
table.add_row("Yazi", "[red]FAILED[/red]")
console.print(table)
```

**Ventajas sobre curses**:
- 2 lineas vs 75 para la seleccion.
- Sin problemas de `endwin()`, `stty`, tamano de terminal.
- Output con colores, spinners y tablas sin esfuerzo.
- `pip install questionary rich` — sin dependencias nativas.

**Impacto**: `install.sh` necesitaria hacer `pip install questionary rich` antes
de lanzar `main.py`. Alternativa: usar `pipx` o bundlear en un venv.

#### T2.2 Alternativa: gum (sin Python)

Si se quiere eliminar la dependencia de Python por completo, **gum**
(github.com/charmbracelet/gum) permite hacer prompts interactivos desde bash:

```bash
SELECTED=$(gum choose --no-limit "Dependencies" "Lazygit" "Yazi" "Neovim" "Tmux")
for component in $SELECTED; do
    gum spin --title "Instalando $component..." -- bash "install_${component,,}.sh"
done
```

**Ventajas**: Un solo binario Go, sin runtime de Python. Todo en bash.
**Desventajas**: Pierde la logica del JSON/TOML config. Mas dificil de mantener
si el numero de componentes crece.

---

### Tier 3 — Refactor completo con Textual (1-2 semanas)

#### T3.1 App Textual con dos paneles

Reescribir `main.py` como una app **Textual** (github.com/Textualize/textual):

```
+------------------------------------------+
|  wsl-tmux-nvim-setup installer     v2.0  |
+------------------+-----------------------+
| [ ] Dependencies |                       |
| [x] Lazygit      |  > Installing Tmux... |
| [x] Yazi         |  git clone tpm...     |
| [ ] NerdFonts    |  tmux start-server    |
| [x] Neovim       |  install_plugins.sh   |
| [x] Tmux         |  [OK] Tmux instalado  |
| [ ] Kitty        |                       |
| [ ] Synth Shell  |                       |
| [ ] Git Config   |                       |
+------------------+-----------------------+
|  [Instalar]  [Salir]                     |
+------------------------------------------+
```

- Panel izquierdo: checklist de componentes con descripciones.
- Panel derecho: log en vivo del subprocess stdout/stderr.
- Los componentes con dependencias no satisfechas se muestran grayed out.
- Al terminar, resumen con colores.

**Textual Web**: la misma app se puede servir en un navegador con
`textual-web serve main.py`. Zero codigo extra para la version web.

**Impacto**: rewrite completo de main.py (~200-300 lineas). Los scripts bash
no cambian nada.

#### T3.2 Migrar de JSON a TOML

Reemplazar `components.json` por `components.toml`:

```toml
[components.dependencies]
name = "Dependencies"
description = "Paquetes base: ripgrep, nodejs, neovim, tmux, etc."
script = "install_dependencies.sh"
depends_on = []
check_command = "nvim --version"
config_files = [
    { src = ".bashrc", dest = "~/.bashrc" },
]

[components.lazygit]
name = "Lazygit"
description = "TUI para git"
script = "install_lazygit.sh"
depends_on = ["dependencies"]
check_command = "lazygit --version"
config_files = [
    { src = "lazygit/config.yml", dest = "~/.config/lazygit/config.yml" },
]

[components.yazi]
name = "Yazi"
description = "File manager de terminal"
script = "install_yazi.sh"
depends_on = ["dependencies", "nerdfonts"]
check_command = "yazi --version"
config_files = [
    { src = "yazi/", dest = "~/.config/yazi/" },
]
```

**Ventajas sobre JSON**:
- Comentarios inline (JSON no los permite).
- Menos ruido sintactico (sin llaves ni comillas en keys).
- `tomllib` esta en stdlib de Python 3.11+.
- Separar la copia de config files del script: el orchestrador puede copiar los
  `config_files` declarativamente y el script solo se encarga de instalar el binario.

---

### Tier 4 — Adoptar un dotfile manager (largo plazo)

#### T4.1 Opcion A: chezmoi

Migrar a **chezmoi** (chezmoi.io) como capa de gestion de dotfiles:

- Cada script se convierte en `run_once_install_<tool>.sh` — chezmoi lo ejecuta
  una sola vez (trackea un hash del contenido).
- Los config files se gestionan con templates: `dot_config/yazi/yazi.toml.tmpl`.
- Cross-platform con variables `{{ .chezmoi.os }}`.
- `chezmoi diff` muestra que cambiaria. `chezmoi apply` lo aplica.

**Estructura resultante**:
```
~/.local/share/chezmoi/
  run_once_01_install_dependencies.sh
  run_once_02_install_lazygit.sh
  run_once_03_install_yazi.sh
  dot_bashrc.tmpl
  dot_tmux.conf
  dot_config/
    kitty/kitty.conf
    yazi/yazi.toml
    lazygit/config.yml
```

**Ventajas**: idempotencia automatica, `chezmoi update` desde cualquier maquina,
diff antes de aplicar, templates con condicionales.
**Desventajas**: curva de aprendizaje, pierde el TUI interactivo (chezmoi ejecuta
todo o nada, no seleccion individual).

#### T4.2 Opcion B: dotbot

**dotbot** (github.com/anishathalye/dotbot) es mas cercano a la arquitectura actual:

```yaml
# install.conf.yaml
- defaults:
    link:
      relink: true

- link:
    ~/.bashrc: .bashrc
    ~/.tmux.conf: .tmux.conf
    ~/.config/kitty/kitty.conf: kitty.conf
    ~/.config/lazygit/config.yml: lazygit/config.yml
    ~/.config/yazi/: yazi/

- shell:
    - [auto_install/components/install_dependencies.sh, Installing dependencies]
    - [auto_install/components/install_lazygit.sh, Installing lazygit]
    - [auto_install/components/install_yazi.sh, Installing yazi]
```

**Ventajas**: YAML declarativo, symlinks + scripts, muy cercano a lo que ya tienes.
**Desventajas**: sin TUI interactivo, sin deteccion de "ya instalado" nativo.

---

## 4. Recomendacion

| Prioridad | Que hacer | Esfuerzo | Impacto |
|-----------|-----------|----------|---------|
| **1** | T1.1 Dependencias en JSON | 1h | Elimina fallos por orden incorrecto |
| **2** | T1.2 Deteccion ya instalado | 1h | Re-ejecuciones rapidas |
| **3** | T1.3 Fix nerdfont local | 15min | Elimina descarga redundante |
| **4** | T1.4 Proteger .bashrc | 30min | Elimina bug de overwrite |
| **5** | T2.1 questionary + rich | 2-3h | TUI moderno sin rewrite total |
| **6** | T3.2 Migrar a TOML | 1-2h | Config legible y extensible |
| **7** | T3.1 App Textual | 1-2 semanas | Instalador profesional con logs en vivo |
| **8** | T4.x Dotfile manager | Evaluacion | Solo si se quiere gestion multi-maquina |

**Ruta sugerida**: Aplicar Tier 1 completo (bugs) → Tier 2.1 (questionary + rich) →
Tier 3.2 (TOML). Esto da un instalador moderno, extensible y robusto sin rewrite
total. Textual (Tier 3.1) solo si se quiere la experiencia premium con logs en vivo.

---

## 5. Dependencias nuevas por tier

| Tier | Dependencia | Instalacion |
|------|-------------|-------------|
| T1 | ninguna | — |
| T2.1 | `questionary`, `rich` | `pip install questionary rich` |
| T2.2 | `gum` | `go install github.com/charmbracelet/gum@latest` |
| T3.1 | `textual` | `pip install textual` |
| T3.2 | ninguna (Python 3.11+) | `tomllib` en stdlib |

---

## 6. Estructura objetivo (post Tier 1 + 2 + 3.2)

```
wsl-tmux-nvim-setup/
├── bin/
│   ├── install.sh              # bootstrap (+ pip install questionary rich)
│   └── nerdfont-install.sh
├── auto_install/
│   ├── main.py                 # questionary selector + rich output
│   ├── components.toml         # config declarativo con depends_on, check_command
│   └── components/
│       ├── install_dependencies.sh
│       ├── install_lazygit.sh
│       └── ...
├── configs/                    # dotfiles agrupados (opcional, mas limpio)
│   ├── .bashrc
│   ├── .tmux.conf
│   ├── kitty.conf
│   ├── lazygit/config.yml
│   └── yazi/
└── REFACTOR.md
```
