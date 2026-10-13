# OPS — Ejecución del RBK 06 (SnapRAID)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-13 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v2 (2.1, Aprobado) — RBK-2026-10-09-06-snapraid.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-13 20:50 |
| **Fin** | 2026-10-13 21:30 |

> Registro a posteriori: la ejecución se hizo el 2026-10-13 y se registra sin re-ejecutar nada,
> a partir de `memory/ops/session-2026-10-13.md` (sección RBK 06) y de las copias en
> `state/config/etc/snapraid/` y `state/config/etc/snapraid-diff.conf`. Horas aproximadas.

## Alcance

Fase 06 completa: array SnapRAID `nas` (paridad WD, datos d1 y d2, tres content), exclusiones,
primer sync en vacío y programación diaria de diff/sync a las 23:30 con scrub semanal del 12 %.
Todos los pasos los hizo el Agente por SSH con `omv-rpc` (ningún paso Destructivo).

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 06 v2.1 aprobado | Sí |
| RBK 05 aplicado | Sí (`state/applied.yaml`, OPS-2026-10-13-rbk05 Aprobado) |
| `ssh nas` con clave | Sí |
| Pasos destructivos | No. Discos sin datos (pool vacío) |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Comprobar los montajes de los tres discos | Lectura | Agente | ~20:50 | OK | E1 |
| 2. Crear el array y añadir los discos | Cambio | Agente | ~20:55 | OK | E2 |
| 3. Añadir las exclusiones | Cambio | Agente | ~21:00 | OK | E3 |
| 4. Leer la configuración generada | Lectura | Agente | ~21:05 | OK | E4 |
| 5. Primer sync en vacío y estado | Cambio | Agente | ~21:10 | OK | E5 |
| 6. Programar diff, sync y scrub | Cambio | Agente | ~21:20 | OK | E6 |
| 7. Comprobar la programación | Lectura | Agente | ~21:30 | OK | E7 |

## Evidencias

### E1 — Paso 1: montajes

```
3 montajes /srv/dev-disk-by-uuid-* presentes (parity a31e93cf…, d1 1d82d7b3…, d2 56801884…)
mntentref leídos con: omv-confdbadm read conf.system.filesystem.mountpoint
  (FsTab getList no existe en OMV 8)
  raíz 79684322…, parity 1901249d…, d1 16149efb…, d2 96abea2b…
```

### E2 — Paso 2: array y discos (omv-rpc)

```
Array "nas" uuid 358857d2-7c5b-415d-a2e0-3997c6f6b385
parity -> paridad 1; d1, d2 -> data + content; ssd (raíz) -> solo content
```

### E3 — Paso 3: exclusiones

```
1.er intento: setRule rtype 1 -> creó reglas INCLUDE (rtype 1 = include, 0 = exclude)
Detectado al leer la conf antes del sync; reglas borradas y recreadas con rtype 0
Conf final: 0 líneas include
```

### E4 — Paso 4: configuración (copia en state/config/etc/snapraid/)

```
/etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf (+ enlace nas.conf)
parity  /srv/dev-disk-by-uuid-a31e93cf-…/snapraid.parity
content /srv/dev-disk-by-uuid-1d82d7b3-…/snapraid.content
content /srv/dev-disk-by-uuid-56801884-…/snapraid.content
content //snapraid.content          <- raíz del SSD, no /var/snapraid/ (incidencia 3)
data d1 /srv/dev-disk-by-uuid-1d82d7b3-…
data d2 /srv/dev-disk-by-uuid-56801884-…
exclude: *.unrecoverable, lost+found/, aquota.*, /tmp/, .content, *.bak, .Trash-*/,
         .recycle/, /Imagenes/.immich-tmp/ …
```

### E5 — Paso 5: sync y status

```
snapraid sync: Nothing to do; 3 content verificados
snapraid status: The array is empty
```

### E6 — Paso 6: programación (omv-rpc setSettings + Cron set)

```
percentscrub 12, scrubfreq 7, runscrub, delthreshold 50, sendmail, defaultarray
/etc/snapraid-diff.conf: RUN_SCRUB=true SCRUB_FREQUENCY_IN_DAYS=7 DEL_THRESHOLD=50 SCRUB_PERCENT=12
Tarea programada OMV: 30 23 * * * root /usr/sbin/omv-snapraid-diff (con correo)
```

### E7 — Paso 7: cron

```
/etc/cron.d/openmediavault-userdefined: 30 23 * * * ... omv-snapraid-diff
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 3 | Incidencia 1: `setRule` con `rtype 1` crea include, no exclude (`rtype 0` = exclude) | Detectado antes del sync; reglas borradas y recreadas con `rtype 0`; 0 include | RBK: indicar `rtype 0` (`/runbook-plugin:update-rbk RBK-2026-10-09-06-snapraid`) |
| 1 | Incidencia 2: `FsTab getList` no existe en OMV 8 | mntentref leídos con `omv-confdbadm read conf.system.filesystem.mountpoint` | RBK: cambiar el comando (`/runbook-plugin:update-rbk`) |
| 4 | Incidencia 3: el content del SSD queda en `//snapraid.content` (raíz del sistema), no en `/var/snapraid/` como dice el HLD | Aceptado tal cual (3 content verificados) | Arquitecto: `/architect-plugin:update-hld` |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| Estado del array | `status`: The array is empty, sin errores | Sí |
| Content x3 | 3 líneas `content` | Sí |
| Programación | `30 23 * * *` en `/etc/cron.d/openmediavault-userdefined` | Sí |

## Cambios en la configuración

- Array SnapRAID `nas`: `/etc/snapraid/omv-snapraid-358857d2-….conf` y enlace `nas.conf` (`state/config/etc/snapraid/`).
- `/etc/snapraid-diff.conf` (`state/config/etc/snapraid-diff.conf`).
- Tarea programada OMV a las 23:30 en `/etc/cron.d/openmediavault-userdefined`.
- Ficheros `snapraid.parity` en el WD y `snapraid.content` en d1, d2 y `/`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-13 | Operator Agent | Registro creado a posteriori |
| 1.1 | 2026-10-13 | Operator Agent | Pasos 1-7 registrados; Resultado Completado; En revisión |
| 1.2 | 2026-10-13 | Operator Agent | Ejecución cerrada y aprobada |
