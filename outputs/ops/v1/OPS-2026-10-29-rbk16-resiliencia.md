# OPS — Ejecución del RBK 16 (resiliencia)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-29 |
| **Última modificación** | 2026-10-29 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v3 (3.0, Aprobado) — RBK-2026-10-28-16-resiliencia.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-28 22:20 |
| **Fin** | 2026-10-29 21:50 |

## Alcance

Esta ejecución responde al cuelgue del 21 al 28 de octubre. Hace cuatro cosas:

- guarda el journal en el SSD (fuera de writecache);
- cambia el módulo del watchdog a `bcm2835_wdt`;
- fija `RebootWatchdogSec=2min`;
- vigila `snapraid.content` y avisa por correo si pasan 48 h sin sync.

El reinicio del paso 7 sirvió también como paso 9 del UPD-2026-10-28.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 16 aprobado | Sí |
| Imagen del SSD | `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`, verificada (512 110 190 592 bytes) |
| Pasos destructivos | No |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Foto del estado actual | Lectura | Agente | 2026-10-28 22:20 | OK | E1 |
| 2. Apagado limpio e imagen del SSD | Cambio | Usuario | 2026-10-28 22:30 | OK | E2 |
| 3. Sacar /var/log de writecache y journal persistente | Cambio | Agente | 2026-10-29 21:30 | OK | E3 |
| 4. Variables de OMV: watchdog y límite del journal | Cambio | Agente | 2026-10-29 21:33 | OK | E4 |
| 5. Drop-in de RebootWatchdogSec | Cambio | Agente | 2026-10-29 21:36 | OK | E5 |
| 6. Vigilancia de snapraid.content | Cambio | Agente | 2026-10-29 21:38 | OK | E5 |
| 7. Reinicio de verificación | Cambio | Agente | 2026-10-29 21:43 | OK | E6 |
| 8. Journal persistente y watchdog tras el reinicio | Lectura | Agente | 2026-10-29 21:50 | OK | E6 |

## Evidencias

### E1 — Paso 1

```
/var/log en overlay; list-boots: solo 2026-10-09 y el arranque actual; softdog; RuntimeWatchdogSec=14s;
RebootWatchdogUSec=2min; Broadcom BCM2835 Watchdog timer; snapraid.content 2026-10-20 23:37; recipient_canonical root 1
/ ocupa 170 G (antes 9 G: Immich y Nextcloud)
```

### E2 — Paso 2

```
SSD del NAS conectado al PC (Windows disco 1, KXG50ZNV 512G NVMe TOSHIBA), wsl --mount --bare → /dev/sdd
dd if=/dev/sdd bs=4M | pigz -1 > /mnt/d/_nas_imagenes/nas-ssd-2026-10-28.img.gz (lo lanzó el usuario)
162 G comprimido; pigz -dc | wc -c = 512110190592 = tamaño del disco
```

### E3 — Paso 3

```
diferencias previas: ['journald_storage', 'paths']
WriteCache setSettings → set-ok; deploy writecache: Succeeded 15, Failed 0
/var/log en writecache: 0; Storage=persistent: 1; /var/log en config.yaml: 0; /var/log: ssd-directo
```

### E4 — Paso 4

```
previa: 0 variables; añadidas OMV_WATCHDOG_MODULE_NAME="bcm2835_wdt" y OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE="500M"
omv-salt stage run prepare + deploy watchdog systemd-journald: Succeeded 7, Failed 0
1, 1, bcm2835_wdt, SystemMaxUse=500M, RuntimeWatchdogSec=14s
```

### E5 — Pasos 5 y 6

```
60-nas-watchdog.conf; daemon-reexec → RuntimeWatchdogUSec=14s, RebootWatchdogUSec=2min; 1 definición
snapraid-content-vigila (script, service y timer desde state/config); timer: próxima ejecución 2026-10-30 12:00
--prueba → "AVISO enviado: ultimo=2026-10-28 23:30 edad=22h"
```

### E6 — Pasos 7 y 8

```
systemctl reboot → ssh tras ~40 s
list-boots: -2 (2026-10-28), -1 (2026-10-09…2026-10-29 20:48), 0 (2026-10-29 21:43) → el journal se conserva entre arranques
/var/log: ssd-directo; File path: /var/log/journal/…/system.journal; uso: 72M
softdog: 0; "Using hardware watchdog 'Broadcom BCM2835 Watchdog timer'"
RuntimeWatchdogUSec=14s, RebootWatchdogUSec=2min; 0 servicios fallidos (aparte de quota, conocido)
```

## Incidencias

| # | Paso | Descripción | Acción |
|---|---|---|---|
| 1 | 4 | Sin `omv-salt stage run prepare`, el pillar de OMV no ve las variables nuevas | Se ejecutó `stage run prepare` antes del deploy; añadir este paso al runbook |
| 2 | 6 | Falta que persona 1 confirme que llegó el correo de prueba | Preguntado |
| 3 | — | El paso 7 se usó también como reinicio del UPD-2026-10-28, que se aplicó entre los pasos 2 y 3 | Registrado en OPS-2026-10-29-upd-apt-immich |

## Estado final

| Comprobación | OK |
|---|---|
| El journal se conserva entre reinicios (`--list-boots` muestra el arranque anterior) | Sí |
| `/var/log` directo en el SSD y uso ≤ 500M | Sí (72M) |
| Watchdog hardware BCM2835, sin `softdog` | Sí |
| `RuntimeWatchdogUSec=14s`, `RebootWatchdogUSec=2min` | Sí |
| Temporizador `snapraid-content-vigila` activo | Sí |
| Ningún servicio fallido nuevo | Sí |

El journal se guarda en el SSD y se conserva entre reinicios (límite de 500M). El watchdog es el
hardware BCM2835 (14 s; 2 min al reiniciar). Hay aviso diario a las 12:00 si `snapraid.content`
pasa de 48 h sin actualizarse.

## Cambios en la configuración

- writecache: `/var/log` fuera; `journald_storage=persistent` (`state/config/omv/writecache-setSettings.json`).
- `/etc/default/openmediavault`: `OMV_WATCHDOG_MODULE_NAME`, `OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE`.
- `/etc/systemd/system.conf.d/60-nas-watchdog.conf`.
- `/usr/local/sbin/snapraid-content-vigila` y su service y timer.

## Historial de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-10-29 | Operator Agent | Ejecución completa del RBK 16 |
