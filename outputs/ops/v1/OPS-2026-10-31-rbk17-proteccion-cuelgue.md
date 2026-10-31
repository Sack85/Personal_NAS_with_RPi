# OPS — Ejecución del RBK 17 (protección ante el cuelgue del disco del sistema)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-31 |
| **Última modificación** | 2026-10-31 |
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

Los pasos 1 a 8 se aplican en caliente. Los pasos 9 a 11 (apagado, cambio de adaptador y comprobaciones tras el arranque) esperan al adaptador USB 3: el cable va integrado en la caja, así que se necesita un adaptador USB-C hembra a USB-A macho de 5 Gbps o más.

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
| 10. Comprobaciones tras el arranque | Lectura | Agente | — | Pendiente | — |
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

## Incidencias

| # | Paso | Descripción | Acción |
|---|---|---|---|
| 1 | 9 | El cable de la caja Ugreen va integrado: no se puede cambiar el cable, solo el adaptador USB-C hembra → USB-A macho | Comprar un adaptador USB 3 (5 o 10 Gbps); pasos 9-11 pendientes |

## Estado final

Pendiente de los pasos 9 a 11. Desde las 06:51 están activos: el espejo de mensajes del kernel en el QVO, el reinicio automático ante tareas bloqueadas (120 s + 10 s) y el panic ante errores en la raíz.

## Cambios en la configuración

- SnapRAID: regla `exclude /.nas-kmsg/` (uuid 44f0d41c-…).
- `/etc/systemd/system/kmsg-espejo.service`, `/etc/logrotate.d/kmsg-espejo`, carpeta `.nas-kmsg` en el QVO.
- `/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`.
- Superbloque de la raíz: `Errors behavior: Panic`.

## Historial de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-10-31 | Operator Agent | Pasos 1 a 8 en caliente; 9 a 11 pendientes del adaptador |
