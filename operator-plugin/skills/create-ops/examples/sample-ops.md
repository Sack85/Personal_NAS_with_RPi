# OPS — Ejecución del RBK 05 (discos: revisión SMART y formateo)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.1 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-13 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v1 (1.0, Aprobado) — RBK-2026-10-12-05-discos.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-13 09:05 |
| **Fin** | 2026-10-13 13:40 |

## Alcance

Ejecución completa del RBK 05 sobre los tres discos SATA del HAT. El XG5 del sistema no se toca.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| NAS accesible por SSH | Sí, `uptime` 2 días |
| Datos de los discos viejos copiados | Confirmado por el usuario a las 09:02 |
| OMV accesible y sesión iniciada | Confirmado por el usuario |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Identificar los discos | Lectura | Agente | 09:06 | OK | E1 |
| 2. Leer SMART | Lectura | Agente | 09:08 | OK | E2 |
| 3. Test SMART largo | Cambio | Agente | 09:12 | OK | E3 |
| 4. Borrar los discos | Destructivo | Usuario | 12:30 | OK | E4 |
| 5. Crear y montar ext4 | Destructivo | Usuario | 12:50 | OK | E5 |
| 6. Anotar montajes | Lectura | Agente | 13:05 | OK | E6 |
| 7. Reservados a 0 en la paridad | Destructivo | Usuario | 13:20 | OK | E7 |

## Evidencias

### E1 — lsblk

```
NAME          SIZE MODEL              SERIAL
sda  1000204886016 WDC WD10EZEX-00W   WD-WCC6Y0XXXXXX
sdb  1000204886016 TOSHIBA MK1059GSM  Z0XXXXXXX
sdc  1000204886016 Samsung SSD 870 QVO S5XXXXXXXXXX
sdd   512110190592 TOSHIBA THNSN5512  USB
```

### E2 — SMART (atributos clave)

```
sda WD     5=0 9=21340 197=0 198=0 199=0
sdb TOSHIBA 5=0 9=9120 193=148230 197=0 198=0 199=0
sdc QVO    5=0 9=3100 177=98 241=21.4 TB
```

### E3 — Tests largos

```
sda Completed without error
sdb Completed without error
sdc Completed without error
```

### E4 — Discos borrados

```
lsblk: sda, sdb, sdc sin particiones (pegado por el usuario)
```

### E5 — Sistemas de archivos

```
3 x ext4 montados por OMV en /srv/dev-disk-by-uuid-…
```

### E6 — Montajes

```
Tabla Rol → disco → UUID → montaje guardada en state/config/montajes.md
```

### E7 — Reservados de la paridad

```
Reserved block count:     0
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 2 | Atributo 193 del Toshiba alto (148 230) | Anotado; no impide usarlo como dato | Vigilar en el informe mensual (MNT) |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| Tres discos montados | 3 | Sí |
| Paridad sin reserva | 0 | Sí |
| Tests largos sin error | 3 de 3 | Sí |

## Cambios en la configuración

- Tres sistemas de archivos ext4 nuevos montados por OMV.
- `state/config/montajes.md` creado con la tabla Rol → disco → UUID → montaje.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-13 | Operator Agent | Inicio de la ejecución |
| 1.1 | 2026-10-13 | Operator Agent | Ejecución completada |
