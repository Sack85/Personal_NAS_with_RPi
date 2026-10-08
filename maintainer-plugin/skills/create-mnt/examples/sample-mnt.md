# MNT — Mensual 2026-12-01

| Campo | Valor |
|---|---|
| **Documento** | MNT |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-12-01 |
| **Última modificación** | 2026-12-01 |
| **Autor** | Maintainer Agent |
| **Entregable previo** | HLD v1 (1.0, Aprobado) — HLD-2026-10-10-nas-familiar.md |
| **Periodo** | Mensual |
| **Inventario** | state/inventory/2026-12-01.yaml |
| **Semáforo** | Rojo |

## Resumen

El NAS funciona y los backups están al día, pero D1 (Toshiba MK1059) ha empezado a reasignar
sectores (atributo 5 de 0 a 8) y tiene 2 sectores pendientes (197). Hay que planificar su
sustitución antes de que falle. Hay un kernel y OMV 8.1 pendientes: se aplazan hasta después del
cambio de disco.

## Checklist

| Tarea | Periodicidad | Resultado | Evidencia |
|---|---|---|---|
| Informe de SnapRAID: sync hecho y sin umbral superado | Semanal | OK | Último sync 2026-12-01 04:15, 0 errores |
| Backup diario de AIO terminado | Semanal | OK | 2026-12-01 03:22 correcto |
| Backup restic al Hitachi y guardado fuera de la habitación | Mensual | OK | 2026-11-02; siguiente antes del 2026-12-02 |
| Limpiar el filtro de polvo | Mensual | OK | Confirmado por el usuario |
| Actualizaciones de OMV y `lsblk` si cambió el kernel | Mensual | Aviso | Kernel 6.12.55 y OMV 8.1 pendientes; aplazados |
| SMART: atributos 5, 197, 198 y 193 | Mensual | Fallo | D1: 5 = 8 y 197 = 2 (antes 0) |

## Salud de discos

| Disco | Rol | Temp (°C) | 5 | 197 | 198 | 199 | 193 | Tendencia |
|---|---|---|---|---|---|---|---|---|
| WDC WD10EZEX | Paridad | 37 | 0 | 0 | 0 | 0 | 1 240 | Estable |
| TOSHIBA MK1059GSM | D1 | 41 | 8 | 2 | 0 | 0 | 154 900 | Crece (5 y 197); 193 sube 222/día |
| Samsung 870 QVO | D2 | 31 | 0 | — | — | 0 | — | Estable (177 = 97) |

## Temperatura y energía

CPU 53,5 °C, `get_throttled` = 0x0. D1 a 41 °C, por encima del objetivo de 40 °C: coincide con
más actividad de reubicación de sectores. SAI en `OL`.

## Espacio

Pool al 61 % (unos 1 100 GB de 1 800 GB útiles); crecimiento de 3 puntos en un mes, dentro de
lo previsto en el NRD.

## Backups

| Copia | Última | Estado |
|---|---|---|
| SnapRAID sync | 2026-12-01 04:15 | Correcto |
| Backup de AIO | 2026-12-01 03:22 | Correcto |
| restic al Hitachi | 2026-11-02 | Correcto; toca esta semana |
| Copia fuera de casa | 2026-11-02 | Correcto |

## Acciones

| Acción | Prioridad | Responsable | Fecha límite | Skill |
|---|---|---|---|---|
| Diagnosticar D1 y preparar su sustitución | Alta | Adulto 1 | 2026-12-05 | `/storage-plugin:diagnose-disk` |
| Backup restic al Hitachi antes de tocar discos | Alta | Adulto 1 | 2026-12-03 | `/operator-plugin:create-ops` (RBK 11) |
| Revisar el aire de la bahía de D1 (41 °C) y limpiar el filtro | Media | Adulto 1 | 2026-12-03 | — |
| APM 254 en D1 si sigue en servicio | Media | Adulto 1 | 2026-12-05 | `/storage-plugin:create-dcp` |
| Plan de actualización de kernel y OMV 8.1 tras el cambio de disco | Media | Adulto 1 | 2027-01-10 | `/maintainer-plugin:create-upd` |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-12-01 | Maintainer Agent | Creación |
