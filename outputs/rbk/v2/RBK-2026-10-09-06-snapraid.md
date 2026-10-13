# RBK 06 — SnapRAID

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 06 — SnapRAID |
| **Versión** | 2.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h |

## Objetivo

Crear el array SnapRAID `nas` con el WD Blue como paridad, D1 y D2 como datos y tres ficheros
content (d1, d2 y el SSD del sistema), con las exclusiones del HLD, el primer sync en vacío y la
programación diaria a las 23:30 con umbral de 50 borrados y scrub semanal del 12 % (HLD §5).

## Prerrequisitos

- [ ] RBK 05 completado (OPS-2026-10-13-rbk05 Aprobado); tabla Rol → UUID → montaje en `state/config/montajes.md`: parity `a31e93cf…`, d1 `1d82d7b3…`, d2 `56801884…`
- [ ] Web de OMV accesible en http://192.168.1.11:8000 (solo para consultar; la configuración se hace por SSH con `omv-rpc`, sin sesión web)

## Pasos

### Paso 1: Comprobar los montajes de los tres discos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'findmnt -rn -o SOURCE,TARGET | grep /srv/dev-disk-by-uuid'
```

Esperado: tres montajes `/srv/dev-disk-by-uuid-…` que coinciden con la tabla del RBK 05.

Si falla: si falta uno, para y vuelve al RBK 05.

### Paso 2: Crear el array y añadir los discos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc` del plugin SnapRAID; desviación aceptada en las fases 04-05) |
| **HLD** | §5 SnapRAID |

Comprobación previa (Lectura): obtener los `uuid` de las entradas de FsTab (mntentref) de parity, d1, d2 y la raíz (sharerootfs) y compararlos con `state/config/montajes.md`:

```bash
ssh -t nas "sudo omv-rpc -u admin FsTab getList '{\"start\":0,\"limit\":-1}'"
```

Comandos (una orden por línea; no pegues más de una línea tras `ssh nas`). Primero el array; anota el `uuid` que devuelve:

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid setArray '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"nas\"}'"
```

Después un `setDrive` por disco, con `arrayref` = uuid del array y `mntentref` = uuid de FsTab del disco:

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid setDrive '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"arrayref\":\"<uuid-array>\",\"mntentref\":\"<mntent-parity>\",\"name\":\"parity\",\"parity\":true,\"paritynum\":1,\"data\":false,\"content\":false}'"
```

- `d1`: `data true`, `content true`, `parity false`.
- `d2`: `data true`, `content true`, `parity false`.
- `ssd` (raíz vía sharerootfs): `content true`, `data false`, `parity false`.

Comprobación:

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid getDriveList '{\"start\":0,\"limit\":-1}'"
```

Esperado: un array `nas` y cuatro discos: `parity` (solo paridad, paritynum 1), `d1` y `d2` (datos + content), `ssd` (solo content); cada `mntentref` coincide con el UUID de `state/config/montajes.md`.

Si falla: si la raíz no aparece en FsTab, comprueba que `openmediavault-sharerootfs` está instalado (RBK 04 paso 7). Si `omv-rpc` rechaza un campo, lee la firma con `sudo omv-rpc -u admin SnapRaid getDrive` sobre un disco creado, anótalo en el OPS y para.

### Paso 3: Añadir las exclusiones

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |
| **HLD** | §5 SnapRAID |

Comando (uno por regla, `rtype 1` = excluir; una orden por línea):

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid setRule '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"arrayref\":\"<uuid-array>\",\"mntentref\":\"<mntent-d1>\",\"rule\":\"*.unrecoverable\",\"rtype\":1}'"
```

Las seis reglas: `*.unrecoverable`, `/lost+found/`, `/tmp/`, `.Trash-*/`, `.recycle/`, `/Imagenes/.immich-tmp/`.

Comprobación (sin duplicados):

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid getRuleList '{\"start\":0,\"limit\":-1}' | grep -o '\"rule\":\"[^\"]*\"' | sort | uniq -c"
```

Esperado: seis reglas `rtype 1`, cada una con recuento 1.

Si falla: si OMV rechaza un patrón, anótalo en el OPS y aplica el resto.

### Paso 4: Leer la configuración generada

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Antes, aplicar la configuración generada (Cambio) y listar los ficheros:

```bash
ssh -t nas "sudo omv-salt deploy run snapraid"
```

```bash
ssh nas 'ls -1 /etc/snapraid/'
```

Debe haber un solo `omv-snapraid-<uuid>.conf`. Si hay dos o más, para: no se usa comodín. Lee el fichero exacto:

```bash
ssh nas 'cat /etc/snapraid/omv-snapraid-<uuid>.conf'
```

Esperado: una línea `parity` en el montaje del WD Blue, tres `content` (d1, d2 y la raíz), `data d1` y `data d2` en sus montajes y las seis exclusiones. Anota en el OPS la ruta real del content del SSD.

Si falla: si la paridad apunta a un disco de datos, para y corrige el paso 2 antes del primer sync.

### Paso 5: Primer sync en vacío y estado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

Usa la ruta exacta anotada en el paso 4 (nunca comodín). Una orden por línea:

```bash
ssh -t nas "sudo snapraid -c /etc/snapraid/omv-snapraid-<uuid>.conf sync"
```

```bash
ssh -t nas "sudo snapraid -c /etc/snapraid/omv-snapraid-<uuid>.conf status"
```

Esperado: el sync termina con `Everything OK` y `status` dice `No error detected`.

Si falla: si sync falla por falta de espacio en la paridad, para y vuelve al arquitecto.

### Paso 6: Programar diff, sync y scrub

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |
| **HLD** | §5 SnapRAID, §7, ADR-015 |

Ajustes del plugin (valores ya puestos; el resto, por defecto):

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid setSettings '{\"percentscrub\":12,\"scrubfreq\":7,\"runscrub\":true,\"delthreshold\":50,\"updthreshold\":0,\"sendmail\":true,\"scrubpercent\":12,\"defaultarray\":\"<uuid-array>\"}'"
```

Comprueba el nombre real del script del diff antes de programarlo:

```bash
ssh nas 'ls -l /usr/sbin/omv-snapraid*'
```

Tarea programada de OMV a las 23:30 (si el script tiene otro nombre, usa el real):

```bash
ssh -t nas "sudo omv-rpc -u admin Cron set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"enable\":true,\"execution\":\"exactly\",\"minute\":[\"30\"],\"everynminute\":false,\"hour\":[\"23\"],\"everynhour\":false,\"dayofmonth\":[\"*\"],\"everyndayofmonth\":false,\"month\":[\"*\"],\"dayofweek\":[\"*\"],\"username\":\"root\",\"command\":\"/usr/sbin/omv-snapraid-diff\",\"sendemail\":true,\"comment\":\"SnapRAID diff/sync/scrub\"}'"
```

```bash
ssh -t nas "sudo omv-salt deploy run snapraid cron"
```

Esperado: `setSettings` y `Cron set` devuelven el objeto guardado; diario a las 23:30; umbral de borrados 50; scrub cada 7 días tras el sync con el 12 %; correo activado.

Si falla: si `omv-rpc` rechaza un campo, anótalo en el OPS y para; no se sigue con la web sin actualizar el RBK.

### Paso 7: Comprobar la programación

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas "sudo grep -rn -i snapraid /etc/cron.d /etc/crontab /var/spool/cron 2>/dev/null; sudo grep -rn -i -E 'threshold|scrub' /etc/snapraid/ 2>/dev/null"
```

Esperado: una entrada a las 23:30 (`30 23 * * *`) con el script real de diff del plugin, y los valores 50 y 12 en la configuración del diff. Comprueba que no hay duplicados: `ssh nas "sudo grep -rc '30 23' /etc/cron.d/openmediavault-userdefined"` devuelve 1.

Si falla: si la hora no es 23:30, vuelve al paso 6: las 23:00 y 23:05 son de Immich y AIO.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Estado del array | `ssh -t nas "sudo snapraid -c /etc/snapraid/omv-snapraid-<uuid>.conf status"` | No error detected |
| Content x3 | `ssh nas "grep -c '^content' /etc/snapraid/omv-snapraid-<uuid>.conf"` | 3 |
| Programación | `ssh nas "sudo grep -rn snapraid /etc/cron.d"` | entrada a las 23:30 |

## Vuelta atrás

Borrar el array en Servicios → SnapRAID devuelve los discos a su estado de ext4 sin paridad;
el fichero `snapraid.parity` del WD Blue y los content se pueden borrar después a mano (lo hace el
usuario). No hay datos en el pool todavía.

## Evidencias

- Copia de `/etc/snapraid/omv-snapraid-*.conf` en `state/config/`
- Salida de `snapraid status` en el OPS
- Captura 6.1 y 6.2 en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| Ruta del content del SSD: el HLD dice `/var/snapraid/`; el plugin puede usar otra ruta en la raíz. Se anota la real en el paso 4 y, si difiere, se informa al arquitecto | Runbook Agent | Ejecución del RBK 06 |
| Nombre real del script de diff del plugin (`/usr/sbin/omv-snapraid-diff` previsto): se confirma en el paso 6 y se anota en el OPS | Runbook Agent | Ejecución del RBK 06 |

Cerrada (2026-10-13, Persona 1): el scrub se acepta «cada 7 días tras el sync» en lugar del domingo.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-13 | Runbook Agent | Cambio menor (visto bueno del usuario): cita HLD v2 (2.1); prerrequisitos con OPS-2026-10-13-rbk05 y UUID de `state/config/montajes.md`; pasos 2, 3 y 6 los hace el Agente por SSH con `omv-rpc` (desviación aceptada en fases 04-05) en vez de la web; tarea Cron de OMV a las 23:30; sync con la conf exacta, sin comodín; cerrada la pregunta del scrub (cada 7 días tras el sync) |
| 2.1 | 2026-10-13 | Runbook Agent | Estado cambiado a Aprobado |
