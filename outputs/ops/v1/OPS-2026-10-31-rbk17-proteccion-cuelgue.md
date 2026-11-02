# OPS — Ejecución del RBK 17 (protección ante el cuelgue del disco del sistema)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-31 |
| **Última modificación** | 2026-11-02 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v3 (3.1, Aprobado) — RBK-2026-10-31-17-proteccion-cuelgue-disco-sistema.md |
| **Resultado** | En curso |
| **Inicio** | 2026-10-31 06:40 |
| **Fin** | — |

## Alcance

Respuesta al segundo cuelgue (2026-10-30, journal cortado a las 00:14:37). Se aplican cuatro protecciones:

- espejo de los mensajes del kernel en el QVO, excluido de SnapRAID;
- reinicio automático ante tareas bloqueadas (`hung_task_panic`, `panic=10`);
- raíz ext4 en `errors=panic`;
- constancia del enlace a 480M hasta que llegue el adaptador USB 3.

Los pasos 1 a 8 se aplican en caliente. Los pasos 9 a 11 (apagado, cambio de adaptador y comprobaciones tras el arranque) esperan al adaptador USB 3: el cable va integrado en la caja, así que se necesita un adaptador USB-C hembra a USB-A macho de 5 Gbps o más. Corrección del 2026-10-31 (incidencia 3): el cable de la caja es desmontable (USB-C ↔ USB-C), así que vale el cable USB-C → USB-A USB 3 directo del paso 9 del RBK.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 17 3.1 aprobado | Sí |
| Imagen del SSD (vuelta atrás extrema) | Sí: `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`, 173305146822 bytes |
| Hora fuera de 23:00-01:00 y SnapRAID parado | Sí: 06:45, 0 procesos |
| Pasos destructivos | No |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Detector de tareas bloqueadas y avisos anteriores | Lectura | Agente | 06:40 | OK | E1 |
| 2. Velocidad del enlace del SSD | Lectura | Agente | 06:41 | OK | E2 |
| 3. QVO, reglas de SnapRAID y carpetas compartidas | Lectura | Agente | 06:43 | OK | E3 |
| 4. Imagen del SSD (cubierta por la del 2026-10-28) | Lectura | Agente | 06:41 | OK | E2 |
| 5. Excluir /.nas-kmsg/ de SnapRAID | Cambio | Agente | 06:45 | OK | E4 |
| 6. Servicio kmsg-espejo y su rotación | Cambio | Agente | 06:47 | OK | E5 |
| 7. Reinicio automático ante tareas bloqueadas | Cambio | Agente | 06:49 | OK | E6 |
| 8. Raíz ext4 en panic ante errores | Cambio | Agente | 06:51 | OK | E7 |
| 9. Apagado y adaptador USB 3 | Cambio | Usuario | — | Pendiente | — |
| 10. Comprobaciones tras el arranque | Lectura | Agente | 16:02 | OK | E8 |
| 11. Verificación del enlace USB 3 | Lectura | Agente | — | Pendiente | — |

## Evidencias

### E1 — Paso 1

```
6.18.50+rpt-rpi-2712; existen hung_task_timeout_secs y hung_task_panic
120, 0, 90, 0; /etc/sysctl.d/99-openmediavault.conf:kernel.panic = 90
list-boots: 7 líneas; 5842 líneas de kernel; 0 "blocked for more than"
```

### E2 — Pasos 2 y 4

```
1-1 speed=480 usb= 2.10 driver=/sys/bus/usb/drivers/usb-storage
→ SSD a 480M (USB 2.0, usb-storage) por el adaptador: desviación del HLD §2/§5 (USB 3) hasta los pasos 9-11
imagen: 173305146822 bytes, Oct 28 22:17
```

### E3 — Paso 3

```
sdd Samsung SSD 870 QVO 1TB S5SVNG0N868475F → /srv/dev-disk-by-uuid-56801884-…; sin .nas-kmsg; 592G libres
6 reglas rtype 0; 4 carpetas compartidas (ninguna con .nas-kmsg); logrotate 3.22.0, util-linux 2.41.5; logrotate.timer enabled
conf-igual
```

### E4 — Paso 5

```
setRule → {"uuid":"44f0d41c-c991-48b6-8a8a-8ef608825f38","rule1":"\/.nas-kmsg\/","rtype":0}
deploy snapraid: Succeeded 7, Failed 0; recuento 1; diff: "> exclude /.nas-kmsg/"
state/config/etc/snapraid/omv-snapraid-358857d2-….conf actualizado
```

### E5 — Paso 6

```
previa 3; servicio enable --now → active
prueba /dev/kmsg → 1 línea en el QVO; 1 inicio; 750 root:root / 640 root:root; 1 ExecStart
logrotate -d: considering log …/.nas-kmsg/kmsg.log, sin errores
```

### E6 — Paso 7

```
previa: 0, 90; sysctl -p: hung_task_timeout_secs 120, hung_task_panic 1, panic 10
grep: 99-openmediavault.conf panic 90 + las tres claves en 99-zz-nas-cuelgue-disco.conf
```

### E7 — Paso 8

```
previa: /dev/sda2 = enlace by-id del XG5; fstab sin errors=; panic 10; clean, Continue, sin errores registrados
tune2fs -e panic → "Setting error behavior to 3"; mount -o remount,errors=panic /
después: clean, Errors behavior: Panic; sda2 errors=panic (SATA continue); fstab 0
```

### E8 — Paso 10 (tras el reinicio no planificado del 2026-10-31, sin el paso 9)

El RBK permite hacer el paso 10 tras un reinicio por otro motivo; el 9 y el 11 siguen pendientes
del cable.

```
list-boots: 0 b19d2d1c50074340943f5a5296ca241e Sat 2026-10-31 15:00:46 +04; kmsg-espejo active
RequiresMountsFor=/srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg
=== kmsg-espejo: inicio, arranque b19d2d1c50074340943f5a5296ca241e === (mismo ID); 2 líneas 2026-10-31T15:01:21,…+04:00
120, 1, 10, 0; systemd-sysctl: 0; fallidos sin quotaon: 3 (los tres systemd-quotacheck@, incidencia 4)
Filesystem state: clean; Errors behavior: Panic; sin FS Error count
sda2 errors=panic; sdb1, sdc1, sdd1 errors=continue; findmnt / → /dev/sda2
```

### E9 — Reinicio no planificado del 2026-10-31 («Tras un cuelgue» del RBK y diagnóstico en solo lectura)

```
list-boots: -1 5a933715b1b74d999e189429de44778a 2026-10-30 15:43:23 → 2026-10-31 14:58:24; 0 b19d2d1c… desde 15:00:46
journal -1: última entrada 14:58:24 "mergerfs[772]: running basic garbage collection" (cada 15 min); sin secuencia de apagado
kernel -1 (journal y espejo): última línea 06:47:06 "EXT4-fs (sda2): re-mounted 02f61d5e-…" (paso 8); kmsg-espejo activo desde 06:46:35, sin reinicios
espejo: línea 936 = esa línea de 06:47:06; línea 937 = "=== kmsg-espejo: inicio, arranque b19d2d1c… ==="; "Booting Linux" 15:00:34
→ 0 líneas del kernel entre 06:47:06 y el reinicio: ni "blocked for more than", ni reset USB, ni "I/O error", ni "EXT4-fs error"
/run/initramfs/fsck.log: rootfs: recovering journal; rootfs: clean, 743368/31044928 files
systemd-fsck: d1, d2 y parity "recovering journal" → clean; sda1 (FAT) "Dirty bit is set" → "Automatically removing dirty bit"
vcgencmd get_rsts → get_rsts=20; /proc/device-tree/chosen/bootloader/rsts 0x20; chosen/power/power_reset 0x0; usb_over_current_detected 0
15:53: 11 contenedores healthy; kmsg-espejo, hd-idle, docker, caddy, tailscaled, smbd y nginx active; throttled=0x0; 46,6 °C
```

`rsts` es el valor del registro PM_RSTS al arrancar (documentación de Raspberry Pi, propiedades
`/chosen/bootloader`). 0x20 es el bit HADWRF de ese registro (nombres de bits de barebox; no hay
documentación de `get_rsts`): reinicio completo por el watchdog del SoC. Es el camino tanto del
reinicio tras un panic (`kernel.panic = 10`) como del watchdog de systemd (14 s, RBK 16). El bit
de encendido (0x1000, HADPOR) no está. `power_reset` 0: el PMIC no registró sobretensión,
subtensión, temperatura ni watchdog.

### E10 — Enlace del SSD: velocidad y puertos USB 3 (solo lectura, 15:34-15:52 y 16:02)

```
lsusb -t: Bus 001 (480M) Port 001: Dev 002, Mass Storage, usb-storage, 480M; buses 002 y 004 (5000M) sin dispositivos
portsc (/sys/kernel/debug/usb/xhci): xhci-hcd.0 port01 "Powered Connected Enabled Link:U0 PortSpeed:3" (el SSD, High Speed)
  xhci-hcd.0 port02-03 y xhci-hcd.1 port01-03: "Powered Not-connected Disabled Link:RxDetect PortSpeed:0"
sda: read_ahead_kb 2048; timeout 30 s
ssh nas "date +%s%N; sudo head -c 536870912 /dev/disk/by-id/usb-KXG50ZNV_512G_NVMe_TOSHIB_01293805011E-0:0 | wc -c; date +%s%N"
→ 536870912 bytes en 13,2 s = 40,5 MB/s
16:02, bucle del paso 2: 1-1 speed=480 usb= 2.10 driver=…/usb-storage (paso 9 sin hacer)
```

40,5 MB/s es el techo práctico de USB 2 (480 Mbit/s). Por USB-C directo al PC, la misma caja leyó
~250-260 MB/s al hacer la imagen del 2026-10-28. Los puertos USB 3 de la Pi están encendidos y
esperando dispositivo (`RxDetect`), pero ninguno ve la caja: el SSD solo llega por las líneas USB 2.

### E11 — Caja del SSD (etiqueta y ficha)

```
etiqueta (foto del usuario, 2026-10-31): M.2 NVMe SSD Enclosure; Model: CM400; P/N: 10902; Input: 5.0V ⎓ 3.0A Max; Ugreen Group Limited
ficha: conector USB-C hembra, 10 Gbit/s (USB 3.2 Gen 2); incluye cable USB-C ↔ USB-C de 50 cm; sin cable ni adaptador USB-A
montaje actual (usuario): caja → cable USB-C ↔ USB-C → adaptador USB-C hembra → USB-A macho (lengüeta azul) → puerto azul de la Pi
```

Ficha consultada en fichas de tienda: «UGREEN UG-10902 USB-C Female to M.2 M-Key 10G Enclosure, C to
C cable 50cm» (https://www.proftech.co.ke/ugreen-ug-10902-usb-c-female-to-m-2-m-key-10g-enclosure-c-to-c-cable-50cm)
y «UGREEN USB-C Female to M.2 M-Key 10G Enclosure (UG-10902/CM400)» (https://rapidtech.co.ke/?p=53121).

### E12 — Segundo reinicio no planificado (2026-11-01 18:09)

```
journalctl --list-boots: -1 2026-10-31 15:00:46 → 2026-11-01 18:09:20; 0 desde 2026-11-01 18:15:31
journalctl -b -1 -n 25: última entrada 18:09:20 (apt-daily-upgrade, rutina); sin secuencia de apagado
kmsg.log, líneas por hora: 2026-10-30T15 927, 2026-10-31T06 8, 2026-10-31T15 897, 2026-11-01T18 921
  → ninguna entre el arranque del 2026-10-31 a las 15:00 y el del 2026-11-01 a las 18:15
vcgencmd get_rsts → 20
2026-11-02 06:18: up 12 h; 11 contenedores healthy; fallidos solo quotaon@ y systemd-quotacheck@; Ugreen Storage Device 480M
persona 1 (2026-11-02): nadie tocó la caja, el cable ni el adaptador
```

## Incidencias

| # | Paso | Descripción | Acción |
|---|---|---|---|
| 1 | 9 | El cable de la caja Ugreen va integrado: no se puede cambiar el cable, solo el adaptador USB-C hembra → USB-A macho | Comprar un adaptador USB 3 (5 o 10 Gbps); pasos 9-11 pendientes |
| 2 | — | Reinicio no planificado el 2026-10-31 entre las 14:58:24 (última entrada del journal) y las 15:00:34 (arranque del kernel). El NAS volvió solo (journal desde las 15:00:46) y a las 15:53 todos los servicios y contenedores estaban en marcha (E9). No fue un apagado limpio ni un corte de luz: no hay secuencia de apagado, se recuperaron los journals de ext4, la FAT tenía el dirty bit, `rsts` vale 0x20 (watchdog) y `power_reset` 0. Como en el cuelgue del 2026-10-30, no hay ningún mensaje del kernel: ni el journal ni el espejo tienen nada desde las 06:47:06. La raíz no registró errores (`clean` tras recuperar el journal) | Causa sin determinar: un panic del RBK 17 (su mensaje se pierde, pregunta 3 del RBK) y el watchdog hardware del RBK 16 (14 s) dejan el mismo `rsts`. Las protecciones funcionaron: el NAS volvió solo y con los ajustes del RBK 17 (paso 10, E8). Para el arquitecto (`/architect-plugin:update-hld`), preguntas 2 y 3 del RBK: con `ramoops-pi5` y `systemd-pstore`, un panic dejaría su mensaje y se distinguiría del watchdog. Si se repite: «Tras un cuelgue» del RBK. 2026-11-01: persona 1 confirma que movió la caja y el adaptador hacia las 15:00 para fotografiar la etiqueta: causa probable, desconexión del SSD por el contacto del adaptador; no se toca la caja con el NAS encendido hasta el paso 9 |
| 3 | 9 | Corrige la incidencia 1. La caja es una Ugreen CM400 (P/N 10902, en la etiqueta) con conector USB-C hembra y un cable USB-C ↔ USB-C de 50 cm desmontable (ficha, E11). El cable no va integrado: el montaje es caja → cable C-C → adaptador USB-C hembra → USB-A macho → puerto azul. El SSD lee a 40,5 MB/s, el techo de USB 2, y ningún puerto USB 3 ve la caja (`RxDetect`, E10). Por USB-C directo al PC leía ~250-260 MB/s, así que el límite está en el adaptador, como ya concluyó el diagnóstico del RBK 17 | Vale el paso 9 aprobado tal cual: un cable USB-C macho → USB-A macho USB 3.2 Gen 2, directo y sin adaptador (sustituye a la acción de la incidencia 1). Conservar el cable C-C y cambiar solo el adaptador por uno USB 3 sería una desviación del RBK: antes, `/runbook-plugin:update-rbk` y aprobarlo |
| 4 | 10 | El recuento de unidades fallidas sin `quotaon` del paso 10 da `3`, no `0`. Además de los tres `quotaon@` fallan los tres `systemd-quotacheck@` de los discos SATA («Cannot find filesystem to check or filesystem not mounted with quota option»). Solo se lanzan cuando un fsck corrige algo al arrancar (existe `/run/systemd/quotacheck`, de las 15:00); aquí fue el dirty bit de la FAT de arranque tras el reinicio sucio. Pasó igual en el arranque sucio del 2026-10-30 a las 15:23 (3) y no en el limpio de las 15:43 (0) | Anotado según el «Si falla» del paso 10; el resto del paso coincide (E8). Es un fallo conocido desde el 2026-10-09 e inofensivo (`memory/dcp/session-2026-10-15.md`). Para el RBK (`/runbook-plugin:update-rbk`): excluir también `quotacheck` en ese `grep -v -c` |
| 5 | — | Segundo reinicio no planificado, el 2026-11-01 entre las 18:09:20 (última entrada del journal, en mitad de tareas rutinarias) y las 18:15:18 (arranque del kernel). Persona 1 confirma que nadie tocó la caja, el cable ni el adaptador. Mismas señales que la incidencia 2: sin apagado limpio, `rsts` 0x20 y nada en el espejo del kernel desde el arranque del 2026-10-31 a las 15:00 (E12). El NAS volvió solo; el 2026-11-02 a las 06:18 tenía los 11 contenedores healthy y solo quota fallando | Causa sin determinar. Sospecha principal: el enlace del SSD por el adaptador USB 2, esta vez sin manipulación; el cable del paso 9 lo resuelve o lo descarta. En los tres reinicios (2026-10-30, 2026-10-31 y 2026-11-01) el espejo no ha registrado nada, así que no sirve de caja negra: refuerza la pregunta 3 del RBK (`ramoops-pi5` + `systemd-pstore`) para `/architect-plugin:update-hld` |

## Estado final

Pendiente de los pasos 9 y 11: el cable USB 3 (incidencia 3). Desde las 06:51 están activos: el espejo de mensajes del kernel en el QVO, el reinicio automático ante tareas bloqueadas (120 s + 10 s) y el panic ante errores en la raíz. Tras el reinicio no planificado del 2026-10-31 (incidencia 2), los tres siguen activos (paso 10, E8). Hubo un segundo reinicio no planificado el 2026-11-01 a las 18:09, sin intervención (incidencia 5). El SSD sigue a 480M, con 40,5 MB/s de lectura (E10).

## Cambios en la configuración

- SnapRAID: regla `exclude /.nas-kmsg/` (uuid 44f0d41c-…).
- `/etc/systemd/system/kmsg-espejo.service`, `/etc/logrotate.d/kmsg-espejo`, carpeta `.nas-kmsg` en el QVO.
- `/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`.
- Superbloque de la raíz: `Errors behavior: Panic`.

## Historial de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-10-31 | Operator Agent | Pasos 1 a 8 en caliente; 9 a 11 pendientes del adaptador |
| 1.1 | 2026-10-31 | Operator Agent | Reanudada en el paso 10, tras el reinicio no planificado del 2026-10-31 (~15:00): paso 10 OK (E8). Evidencias E9 a E11 (reinicio; enlace USB 2 a 40,5 MB/s con los puertos USB 3 en `RxDetect`; caja Ugreen CM400 10902) e incidencias 2 a 4 (reinicio; cable desmontable, que corrige la 1; quotacheck). Nota añadida al Alcance. Pasos 9 y 11 pendientes del cable |
| 1.2 | 2026-11-02 | Operator Agent | Evidencia E12 e incidencia 5: segundo reinicio no planificado (2026-11-01 18:09), sin intervención y sin nada en el espejo del kernel |
