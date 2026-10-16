# NAS2RBPi — instrucciones para Claude Code

Sistema multiagéntico para montar desde cero y mantener un NAS doméstico: Raspberry Pi 5 +
Radxa Penta SATA HAT, Raspberry Pi OS Lite (Trixie), OpenMediaVault 8, SnapRAID + MergerFS,
Nextcloud AIO, restic, NUT y hd-idle. Estructura derivada de RDEWAI (ver NOTICE).
Idioma de los entregables y de las skills: español.

## Fuente de verdad

- `inputs/nrd/v1/guia-v2.md`: guía de instalación v2 (punto de partida del NRD).
- `registry.yaml`: plugins, entregables y entregables previos.
- La última versión **Aprobada** de cada entregable en `outputs/<abbr>/vN/` manda sobre la guía.
- `legacy/v1/`: guía de 2020 (RPi4 + NextcloudPi). Solo consulta; no se modifica.

## Cadena de roles

| Plugin | Entregable | Lee (Aprobado) |
|---|---|---|
| `requirements-plugin` | NRD — requisitos del NAS (`outputs/nrd/`) | `inputs/nrd/vN/` |
| `architect-plugin` | HLD — diseño y ADR (`outputs/hld/`) | NRD |
| `runbook-plugin` | RBK — un runbook por fase (`outputs/rbk/`) | HLD |
| `operator-plugin` | OPS — registro de ejecución (`outputs/ops/`), `state/` | RBK, UPD o DCP |
| `maintainer-plugin` | Inventario (`state/inventory/`), UPD y MNT (`outputs/upd/`, `outputs/mnt/`) | HLD |
| `storage-plugin` | Diagnóstico y DCP — cambio de discos (`outputs/dcp/`) | HLD |

Comandos: `/<plugin>:create-<abbr>`, `update-<abbr>`, `validate-<abbr>`, `approve-<abbr>`,
`apply-learnings`.

## Reglas de seguridad (todas las skills)

- Claude corre en el PC y llega al NAS con `ssh nas` (alias de `~/.ssh/config`).
- El guard `ssh_guard.py` permite lecturas, pide confirmación para cambios de estado y
  **bloquea** lo destructivo (mkfs, wipefs, parted, dd, `tune2fs -m`, `snapraid fix`,
  `restic forget/prune`, `rm -r`, EEPROM). Lo bloqueado se entrega al usuario como comando
  exacto, con la comprobación previa (`lsblk -o NAME,SIZE,MODEL,SERIAL`) y la esperada después.
- No se cambia nada en el NAS que no esté en un RBK, UPD o DCP **Aprobado**.
- Nunca se escriben contraseñas, frases de acceso de AIO, contraseñas de aplicación, claves de
  Tailscale ni IPs públicas en ficheros del repo: `secrets_guard.py` y pre-commit lo bloquean.
  Se escribe "en el gestor de contraseñas".
- Antes de cambiar discos, paridad o pool: `snapraid status` sin errores y backup restic al día.
- Contraseñas e inicios de sesión en la web de OMV, Nextcloud o el router los hace el usuario.

## Repo y git

- Una rama por plugin (`plugin/<rol>`), un commit al final de cada etapa, merge `--no-ff` a main.
  Sin push salvo petición expresa.
- Los scripts comunes viven en `shared/`; tras editarlos, `make sync` (las copias en los plugins
  no se editan a mano; `make check-sync` lo verifica).
- Nuevo plugin: skill `/create-role-plugin`.
- Tests: `uv run pytest`; lint: `make lint`; validar entregables: `make validate D=<abbr>`.
- Inventarios y copias de configuración del NAS: `state/inventory/`, `state/config/`;
  lo aplicado en `state/applied.yaml`. Comparar inventarios: `uv run python tools/inventory_diff.py`.

## Aprendizajes

<!-- AUTO-LEARNINGS:START (managed by .claude/hooks/sync_learnings_to_claude_md.py — do not edit by hand) -->
- `create-ops` (2026-10-09): Siempre dar los comandos de pasos con reinicio uno a uno y avisar de no pegar varias lineas tras ssh nas
- `create-rbk` (2026-10-09): Siempre antes de un paso que reinstale o reconfigure el sistema añade un paso de imagen del SSD tras 'sudo poweroff' y una sección de recuperación sin pantalla; nunca desenchufar con el LED verde parpadeando
- `update-hld` (2026-10-09): Siempre identificar discos por /dev/disk/by-id en el HLD y nunca por /dev/sdX
- `update-nrd` (2026-10-08): Siempre usa Irreemplazable, Reemplazable o Mixta (con la parte entre paréntesis) en la columna Criticidad, y cifras numéricas en Crecimiento
- `update-rbk` (2026-10-09): Siempre da los bloques de configuración con los valores ya puestos y añade un grep -c que compruebe que no quedan duplicados
- `update-rbk` (2026-10-09): Siempre indica el puerto físico exacto (USB-A azul) y advierte de que el USB-C de la Pi 5 es solo de alimentación
- `update-rbk` (2026-10-09): Siempre que un paso instale software que gestione sshd (OMV), añadir comprobación posterior con ssh -o BatchMode=yes nas hostname y sudo sshd -T | grep passwordauthentication
- `update-rbk` (2026-10-13): Siempre configura los plugins de OMV con omv-rpc por SSH (Agente) y usa la ruta exacta del fichero tras listarlo, nunca un comodín
- `update-rbk` (2026-10-13): Siempre que un paso de OMV se pueda hacer con omv-rpc, escríbelo como paso de Agente por SSH con la orden set exacta, el omv-salt deploy correspondiente y un getList que compruebe que no hay duplicados
- `update-rbk` (2026-10-16): Siempre que un fichero se cree con ssh nas "printf ... | sudo tee", escapa $ como \$ y escribe #! como \041 con printf %b para que la shell del PC no lo expanda
- `update-rbk` (2026-10-16): Siempre repite en script y servicio los mismos flags no por defecto usados en el primer tailscale up (--hostname=nas) y envía ficheros de configuración generados en el PC con cat fichero | ssh nas "sudo tee <ruta> >/dev/null" desde state/config/
<!-- AUTO-LEARNINGS:END -->

## Qué no hacer

<!-- AUTO-WHATNOT:START (managed by .claude/hooks/sync_learnings_to_claude_md.py — do not edit by hand) -->
- `create-rbk` (2026-10-09): Nunca escribas un bloque que abra 'ssh nas' y siga con comandos del NAS; usa una orden por línea 'ssh -t nas "…"' y avisa de no pegar varias líneas
- `update-rbk` (2026-10-09): Nunca uses /dev/sdX en un paso; identifica cada disco por /dev/disk/by-id/<bus>-<MODELO>_<SERIE> y compáralo por número de serie
<!-- AUTO-WHATNOT:END -->
