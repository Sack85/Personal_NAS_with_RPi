---
name: inventory
description: >
  Hace el inventario del NAS en solo lectura por SSH: versiones (sistema, kernel, EEPROM,
  OpenMediaVault y plugins, SnapRAID, MergerFS, restic, hd-idle, NUT, Docker, contenedores de
  Nextcloud AIO), actualizaciones pendientes y salud (enlace PCIe, throttling, temperaturas,
  SMART sin despertar discos, SnapRAID, espacio del pool, últimos backups). Lo guarda en
  state/inventory/AAAA-MM-DD.yaml y lo compara con el anterior con tools/inventory_diff.py.
  También llamado: estado del NAS, versiones instaladas, chequeo de salud.
  Úsala cuando el usuario pida:
  - Hacer inventario o ver el estado del NAS
  - Saber qué versiones hay instaladas o qué actualizaciones hay pendientes
  - Revisar la salud de los discos o las temperaturas
  - Antes de preparar un plan de actualización o un informe de mantenimiento
  - Comprobar el NAS después de una actualización
argument-hint: ""
allowed-tools: Read, Write, Bash, Glob, AskUserQuestion
---

# Inventario del NAS

Eres el mantenedor del NAS. Tomas una foto fiel de versiones y salud sin cambiar nada y sin
despertar discos que estén durmiendo.

## Paso 1: Acceso

```bash
ssh -o ConnectTimeout=5 nas true || echo "NAS no accesible"
```

Si no responde, para.

## Paso 2: Recoger (todo en solo lectura; el guard lo permite)

```bash
# Sistema
ssh nas 'cat /etc/os-release | grep PRETTY_NAME; uname -r; uptime; sudo rpi-eeprom-update'
# Paquetes
ssh nas "dpkg-query -W -f='\${Package} \${Version}\n' openmediavault 'openmediavault-*' snapraid mergerfs restic hd-idle nut docker-ce 2>/dev/null"
# Contenedores
ssh nas "docker ps --format '{{.Names}} {{.Image}} {{.Status}}'"
ssh nas "docker inspect --format '{{.Config.Image}} {{index .Config.Labels \"org.opencontainers.image.version\"}}' nextcloud-aio-mastercontainer"
# Salud
ssh nas 'sudo lspci -vv -d 197b: | grep LnkSta; vcgencmd get_throttled; vcgencmd measure_temp'
ssh nas 'df -h /srv/mergerfs/pool; sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status | tail -8'
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL'
ssh nas 'for d in /dev/sd?; do sudo hdparm -C "$d"; sudo smartctl -n standby -i -A "$d"; done'
ssh nas 'docker logs --tail 20 nextcloud-aio-borgbackup 2>&1'
```

- `smartctl -n standby` no despierta un disco parado: si está en reposo, deja `smart: {}` y
  `estado: standby` para ese disco (no lo despiertes para el inventario).
- **Actualizaciones pendientes**: necesitan refrescar la lista de paquetes, que es un cambio
  menor; el guard pedirá permiso:
  ```bash
  ssh nas 'sudo apt-get update -qq && apt list --upgradable 2>/dev/null'
  ```
- Último restic: el Hitachi está desconectado; tómalo del último OPS de restic
  (`grep -l restic outputs/ops/v*/*.md`) o pregúntalo con `AskUserQuestion`.

## Paso 3: Escribir el inventario

`state/inventory/AAAA-MM-DD.yaml` con exactamente el formato de
[examples/inventory-2026-11-01.yaml](examples/inventory-2026-11-01.yaml): `fecha`, `sistema`,
`paquetes`, `contenedores`, `pendientes` (paquete, actual, nueva), `salud` (pcie_enlace,
throttled, temp_cpu_c, pool_uso_pct, snapraid, backup_aio, restic_ultimo, discos con rol,
modelo, serie, temp_c y smart con los atributos 5, 193, 197, 198, 199 y, en SSD, 177/241).

El rol de cada disco sale de la tabla de almacenamiento del HLD aprobado (por número de serie).
Nada de contraseñas ni IP pública.

## Paso 4: Comparar

```bash
PREV=$(ls state/inventory/*.yaml | sort | tail -2 | head -1)
uv run python tools/inventory_diff.py "$PREV" state/inventory/AAAA-MM-DD.yaml
```

Si es el primer inventario, pásale solo el actual. Resume al usuario: CRITICAL primero.

## Paso 5: Siguiente paso recomendado

- Alertas CRITICAL de discos → `/storage-plugin:diagnose-disk <disco>` antes que nada.
- Enlace PCIe distinto de 8GT/s o errores de SnapRAID → no actualizar; revisar primero.
- Actualizaciones pendientes → `/maintainer-plugin:create-upd`.
- Toca informe periódico → `/maintainer-plugin:create-mnt <periodo>`.

## Paso 6: Traza

Propón el commit (`git add state/inventory/ && git commit -m "Inventario AAAA-MM-DD"`). Nunca push.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "inventory", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/upd/learnings-queue.jsonl
```

## Aprendizajes y correcciones

> **Meta-reglas para añadir aprendizajes:**
> 1. Cada aprendizaje es una directiva absoluta ("Siempre X", "Nunca Y").
> 2. Primero el problema y luego la solución.
> 3. Con un comando o ejemplo concreto.
> 4. Una regla por viñeta.
> 5. Si dos se contradicen, borra la antigua.
> 6. Máximo 20 por skill.

### Aprendizajes activos

_Ninguno todavía._
