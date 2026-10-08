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
- Inventarios y copias de configuración del NAS: `state/inventory/`, `state/config/`.

## Aprendizajes

<!-- AUTO-LEARNINGS:START (managed by .claude/hooks/sync_learnings_to_claude_md.py — do not edit by hand) -->
_Sin aprendizajes nuevos pendientes._
<!-- AUTO-LEARNINGS:END -->

## Qué no hacer

<!-- AUTO-WHATNOT:START (managed by .claude/hooks/sync_learnings_to_claude_md.py — do not edit by hand) -->
_Sin aprendizajes nuevos pendientes._
<!-- AUTO-WHATNOT:END -->
