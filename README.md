# NAS con Raspberry Pi 5

Sistema multiagéntico (plugins de Claude Code) para montar desde cero, documentar y mantener un
NAS doméstico: Raspberry Pi 5 + Radxa Penta SATA HAT, Raspberry Pi OS Lite (Trixie),
OpenMediaVault 8, SnapRAID + MergerFS, Nextcloud AIO, restic, NUT y hd-idle.

Cada rol es un plugin con skills `create` / `update` / `validate` / `approve`; los entregables se
versionan en `outputs/<entregable>/vN/`, cada rol solo arranca si el entregable anterior está
**Aprobado**, y todo queda en git.

| Plugin | Entregable | Para qué |
|---|---|---|
| `requirements-plugin` | NRD | Qué necesita la familia del NAS |
| `architect-plugin` | HLD + ADR | Cómo se monta y por qué |
| `runbook-plugin` | RBK (uno por fase) | Pasos exactos de cada fase |
| `operator-plugin` | OPS | Ejecuta lo aprobado y deja registro |
| `maintainer-plugin` | Inventario, UPD, MNT | Actualizaciones y mantenimiento |
| `storage-plugin` | Diagnóstico, DCP | Discos que fallan, se cambian o se amplían |

```
NRD ─▶ HLD ─▶ RBK ─▶ OPS            (instalación)
         ├──▶ UPD ─▶ OPS            (actualizaciones)
         ├──▶ MNT                   (mantenimiento)
         └──▶ DCP ─▶ OPS ─▶ HLD     (discos)
```

## Seguridad

- Claude trabaja desde el PC y entra al NAS con `ssh nas`. Un guard revisa cada comando:
  **permite** lecturas, **pide confirmación** para cambios (apt, reinicios, sync…) y **bloquea**
  lo destructivo (formatear, borrar, `snapraid fix`, `restic forget`…), que siempre ejecutas tú
  con el comando exacto que te da el agente, tras comprobar el número de serie del disco.
- Nada se cambia en el NAS si no está en un documento aprobado.
- Ningún secreto llega a GitHub: un guard y pre-commit bloquean contraseñas, frases de acceso,
  claves e IP públicas. Los secretos van en tu gestor de contraseñas.

## Puesta en marcha

1. Dependencias (WSL o Linux con [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync && uv run pre-commit install
   uv run pytest
   ```
   Sin `make` instalado, los objetivos del Makefile equivalen a `uv run …` (ver `Makefile`).
2. Abre Claude Code en esta carpeta y acepta el marketplace del proyecto
   (`.claude/settings.json` lo declara y activa los seis plugins). O a mano:
   `/plugin marketplace add ./` y `/plugin install <plugin>@nas2rbpi-plugins`.
3. Cuando el NAS ya arranque (runbook 03), crea el alias `nas` con clave SSH (el agente no puede
   escribir contraseñas):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_nas
   ssh-copy-id -i ~/.ssh/id_ed25519_nas.pub tu_usuario@192.168.1.200
   cat >> ~/.ssh/config <<'EOF'
   Host nas
     HostName 192.168.1.200
     User tu_usuario
     IdentityFile ~/.ssh/id_ed25519_nas
   EOF
   ssh nas uptime
   ```
   Usa la IP de tu reserva DHCP. Si `sudo` te pide contraseña en el NAS, los comandos con `sudo`
   del agente fallarán: hazlos tú o ajusta sudo sabiendo lo que implica.

## Flujos

### Instalar desde cero

```
/requirements-plugin:create-nrd        →  /requirements-plugin:approve-nrd
/architect-plugin:create-hld           →  /architect-plugin:approve-hld
/runbook-plugin:create-rbk 01          →  /runbook-plugin:approve-rbk <RBK>
/operator-plugin:create-ops <RBK>      →  /operator-plugin:approve-ops <OPS>
… repetir runbook + ejecución por fase (01 a 14)
```

### Actualizar (mensual)

```
/maintainer-plugin:inventory
/maintainer-plugin:create-upd          →  /maintainer-plugin:approve-upd
/operator-plugin:create-ops <UPD>      →  /operator-plugin:approve-ops
/maintainer-plugin:inventory           (comprobar el resultado)
```

### Revisión periódica

`/maintainer-plugin:create-mnt mensual` (o `semanal`, `semestral`). Opcional: programarla con
`/schedule`.

### Un disco muere, falla o quieres uno más grande

```
/storage-plugin:diagnose-disk <disco>  (si ha muerto: desactiva YA el sync programado)
/storage-plugin:create-dcp             →  /storage-plugin:approve-dcp
/operator-plugin:create-ops <DCP>      →  /operator-plugin:approve-ops
/architect-plugin:update-hld           →  /architect-plugin:approve-hld
```

## Estructura

```
legacy/v1/            guía de 2020 (RPi4 + NextcloudPi); también en el tag v1-nextcloudpi
inputs/nrd/v1/        guía v2 (PDF y markdown)
<rol>-plugin/         plugins (skills, plantillas, validadores, evals, hooks)
shared/               scripts comunes; `uv run python tools/sync_shared.py` los copia a los plugins
outputs/<abbr>/vN/    entregables versionados
memory/<abbr>/        notas de sesión y cola de aprendizajes
state/                inventarios, copia de configuración y qué está aplicado
tools/                validar entregables, comparar inventarios, sincronizar shared/
tests/                tests de validadores, guard, hooks y convenciones
```

## Créditos

La estructura de plugins, skills, validadores y hooks deriva de
[Redefining Data Engineering with AI](https://github.com/RDEWAI/Redefining-DataEngineering-With-AI) (Apache 2.0).
Ver [NOTICE](NOTICE).
