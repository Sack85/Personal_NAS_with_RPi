# RBK 06 — SnapRAID

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 06 — SnapRAID |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h |

## Objetivo

Crear el array SnapRAID `nas` con el WD Blue como paridad, D1 y D2 como datos y tres ficheros
content (d1, d2 y el SSD del sistema), con las exclusiones del HLD, el primer sync en vacío y la
programación diaria a las 23:30 con umbral de 50 borrados y scrub semanal del 12 % (HLD §5).

## Prerrequisitos

- [ ] RBK 05 completado: tres ext4 montados y tabla Rol → UUID → montaje
- [ ] Sesión iniciada por el usuario en la web de OMV

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
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 SnapRAID |

Esperado: Servicios → SnapRAID → Arrays → Crear `nas`. Discos: WD Blue = `parity` (paridad sí, datos no, content no); Toshiba = `d1` (datos sí, content sí); QVO = `d2` (datos sí, content sí); sistema de archivos raíz = `ssd` (solo content). Cada disco elegido por su UUID del RBK 05.

Si falla: si la raíz no aparece, comprueba que `openmediavault-sharerootfs` está instalado (RBK 04 paso 7).

### Paso 3: Añadir las exclusiones

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 SnapRAID |

Esperado: Reglas → Excluir: `*.unrecoverable`, `/lost+found/`, `/tmp/`, `.Trash-*/`, `.recycle/`, `/Imagenes/.immich-tmp/`. Guardado y aplicado.

Si falla: si OMV rechaza un patrón, anótalo y aplica el resto.

### Paso 4: Leer la configuración generada

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'cat /etc/snapraid/omv-snapraid-*.conf'
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

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync && sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'
```

Esperado: el sync termina con `Everything OK` y `status` dice `No error detected`.

Si falla: si sync falla por falta de espacio en la paridad, para y vuelve al arquitecto.

### Paso 6: Programar diff, sync y scrub

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 SnapRAID, §7, ADR-015 |

Esperado: en la programación del diff del plugin SnapRAID: diario a las 23:30; umbral de borrados 50 (no sincroniza y avisa por correo); scrub cada 7 días con 12 % de los bloques de más de 10 días; envío del informe por correo activado. Aplicado.

Si falla: si el plugin no permite fijar la hora, crea la tarea en Sistema → Tareas programadas a las 23:30 con el script de diff del plugin y anótalo en el OPS.

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

Esperado: una entrada a las 23:30 (`30 23 * * *` o un temporizador equivalente) y los valores 50, 12 y 10 en la configuración del diff.

Si falla: si la hora no es 23:30, vuelve al paso 6: las 23:00 y 23:05 son de Immich y AIO.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Estado del array | `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'` | No error detected |
| Content x3 | `ssh nas "grep -c '^content' /etc/snapraid/omv-snapraid-*.conf"` | 3 |
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
| El scrub del plugin va por días desde el último scrub (7) y no por día de la semana: el HLD pide domingo. Se acepta «cada 7 días tras el sync» o se crea una tarea aparte el domingo a las 23:30 | Persona 1 | Antes de aprobar este RBK |
| Nombre exacto de los menús de programación del plugin SnapRAID en OMV 8: confirmar en la primera ejecución y corregir el RBK | Runbook Agent | Ejecución del RBK 06 |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
