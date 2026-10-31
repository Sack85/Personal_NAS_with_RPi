# RBK 17 — Protección ante el cuelgue del disco del sistema

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 17 — Protección ante el cuelgue del disco del sistema |
| **Versión** | 3.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-30 |
| **Última modificación** | 2026-10-31 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 50 min en caliente, sin reinicio (pasos 1 a 8) + 30 min cuando llegue el cable (pasos 9 a 11: apagado, cable y comprobaciones) |

## Objetivo

Segundo cuelgue el 2026-10-30 (`memory/ops/session-2026-10-13.md`, sección 2026-10-30): el
journal persistente del arranque anterior (RBK 16) se corta en seco a las 00:14:37 sin ningún
mensaje del kernel. A las 15:16 había ping y el nginx de OMV (:8000) respondía, pero SSH daba
«Connection reset» antes del banner (OpenSSH 10: falla `sshd-session` y entran las penalizaciones
`PerSourcePenalties`) y Caddy (:443) e Immich (:2283) estaban caídos. El watchdog hardware
(`RuntimeWatchdogSec=14s`, RBK 16) no saltó porque PID 1 seguía vivo.

Hipótesis: el disco del sistema (Toshiba XG5 en la caja Ugreen, puente Realtek RTL9210
`0bda:9210`) deja de responder; lo que ya está en memoria sigue vivo y lo que necesita leer o
escribir en el SSD se para o falla. Hoy el SSD enlaza a 480M (USB 2.0, driver `usb-storage`,
bcdUSB 2.10) porque el adaptador USB-C hembra → USB-A macho solo es USB 2 (probadas las dos
orientaciones); el usuario comprará un cable USB-C → USB-A USB 3.2 Gen 2 directo. SMART del XG5
sano (`-d sntrealtek`).

Cuatro medidas (HLD §2, §3, §5, ADR-002):

1. **Espejo de los mensajes del kernel en el QVO** (d2, SATA por PCIe, no se para): servicio
   `kmsg-espejo` con `dmesg -w --time-format iso` y `StandardOutput=append:` hacia
   `/srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log`. Depende del
   montaje del QVO (`RequiresMountsFor=`), rota con logrotate (semanal o al pasar de 10 MB, 8
   copias), queda excluido de SnapRAID con una regla propia (`/.nas-kmsg/`, `rtype 0`) y fuera de
   las carpetas compartidas. Ruta directa del QVO, nunca `/srv/mergerfs/pool`.
2. **Reinicio automático si el disco del sistema se bloquea**: `kernel.hung_task_timeout_secs=120`,
   `kernel.hung_task_panic=1` y `kernel.panic=10` en `/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`.
   Una tarea en estado D que no avanza en 120 s provoca un panic y el kernel reinicia a los 10 s:
   el NAS vuelve solo entre 2 y 4 min después del bloqueo (el detector revisa cada 120 s). No se
   provoca ningún panic de prueba.
3. **Reinicio automático si la raíz da errores de E/S** (decisión de persona 1 del 2026-10-30):
   `tune2fs -e panic` en la raíz ext4 del XG5
   (`/dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2`), cambio persistente
   en el superbloque (fstab no se toca), y `mount -o remount,errors=panic /` para que valga ya: el
   kernel solo lee el superbloque al montar. Un error que ext4 detecta en la raíz (metadatos o
   journal: lo que pasa si el puente se cae) provoca un panic y, con `kernel.panic=10`, el reinicio.
4. **Velocidad del enlace del SSD**: constancia de 480M hasta el cable nuevo; con el cable
   (pasos 9 a 11), 5000M y driver `uas`.

Comprobado en el NAS el 2026-10-30 en solo lectura (filas de la raíz y de e2fsprogs, el 2026-10-31):

| Dato | Valor | Consecuencia |
|---|---|---|
| Kernel | `6.18.50+rpt-rpi-2712` con `/proc/sys/kernel/hung_task_*` (detector compilado): `hung_task_timeout_secs` 120, `hung_task_panic` 0, `hung_task_detect_count` 0 | El paso 7 se puede aplicar |
| Avisos previos | 0 `blocked for more than` en 5 842 líneas del kernel de los 6 arranques guardados (2026-10-09 a hoy, incluido el apt del UPD-2026-10-28 escrito a 480M) | Sin indicios de reinicios falsos |
| `kernel.panic` | 90, de `/etc/sysctl.d/99-openmediavault.conf` (fichero del paquete `openmediavault`; el estado salt `sysctl` de OMV no tiene variable para él) | El fichero nuevo se llama `99-zz-…` para ordenarse después y prevalecer |
| Raíz ext4 del SSD | `/dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2` → el dispositivo de `/`; UUID `02f61d5e-92cb-4f9c-a781-099d97795020`; `Filesystem state: clean`, `Errors behavior: Continue`, sin `FS Error count`; en uso `errors=continue` (`/proc/fs/ext4/*/options`); fstab `defaults,noatime` (0 líneas con `errors=`); `cmdline.txt` sin `rootflags` | Si el SSD desaparece con errores de E/S no hay panic: el paso 8 la pasa a `panic` |
| e2fsprogs y fsck de la raíz | `e2fsprogs 1.47.2`; `CONFIG_BLK_DEV_WRITE_MOUNTED=y`; el initramfs pasa `fsck -y` a la raíz en cada arranque (`/run/initramfs/fsck.log`: `rootfs: clean` el 2026-10-30); OMV no fija `errors=` ni usa `tune2fs` | `tune2fs -e` se aplica con la raíz montada; tras un panic de ext4, e2fsck repara al arrancar |
| WSL del PC (recuperación) | Ubuntu 24.04 con e2fsprogs 1.47.0 (entiende `orphan_file`, que usa la raíz); WSL 2.3.24 con `wsl --mount … --options` | Desde el PC se puede volver la raíz a `continue` |
| Escritura en el QVO | `vm.dirty_expire_centisecs` 3000 y `vm.dirty_writeback_centisecs` 500 | Una línea del espejo llega al QVO en ≤ 35 s |
| SnapRAID | 6 reglas, todas `rtype 0` (exclude); `/tmp/` ya está excluida | Regla propia: una carpeta `tmp` para logs que hay que conservar confunde |
| Rotación | logrotate 3.22.0; `logrotate.timer` diario (00:00 + hasta 1 h) | Configuración en `/etc/logrotate.d/` |

**Límite (para el HLD):** el paso 7 cubre el bloqueo con tareas en estado D 120 s; el paso 8, los
errores de E/S que ext4 detecta en la raíz. Si el puente se cae, el siguiente commit del journal
falla, el journal queda abortado y ext4 hace panic; los síntomas del 2026-10-30 (puertos cerrados, SSH cortado al
momento) encajan igual de bien con un bloqueo que con este caso. Un error al escribir solo datos de
un fichero queda en aviso (`I/O error … writing to inode`) sin panic, y los servicios caídos con el
disco sano no reinician nada (pregunta abierta 2). Con los dos panic, el mensaje del panic y las
últimas ~35 s del espejo se pierden (pregunta 3).

Ficheros en `state/config/`, enviados con `cat <fichero> | ssh nas "sudo tee <ruta> >/dev/null"`.
Los pasos 1 a 8 se aplican en caliente, sin reinicio. Los pasos 9 a 11 se hacen cuando llegue el
cable: su apagado es el reinicio de verificación (decisión de persona 1 del 2026-10-30, no hay
reinicio aparte); hasta entonces el OPS queda Parcial.
`grep -c` devuelve el código de salida 1 cuando cuenta 0: si el esperado es `0`, es correcto.

> Todas las órdenes son de **una línea** (`ssh nas "…"`). Nunca pegues varias líneas seguidas
> tras `ssh nas`: si la sesión se corta en un apagado o reinicio, las líneas restantes se
> ejecutan en el PC. En el paso 9, **una orden cada vez**.

## Prerrequisitos

- [ ] NAS accesible: `ssh -o BatchMode=yes nas hostname` responde `nas`
- [ ] RBK 16 ejecutado (OPS-2026-10-29-rbk16-resiliencia): journal persistente, `journalctl --list-boots` con al menos 2 arranques
- [ ] Fuera de la ventana 23:00-01:00 (volcado de Immich 23:00, SnapRAID diff + sync 23:30, tareas de Immich 00:00, logrotate 00:00-01:00): el paso 5 despliega la configuración de SnapRAID
- [ ] No hace falta paridad al día: no se tocan discos de datos, paridad ni pool (la regla nueva excluye una carpeta que aún no existe)
- [ ] Imagen del SSD del 2026-10-28 en `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`, verificada (`512110190592` bytes, OPS-2026-10-29-rbk16-resiliencia): es la vuelta atrás del caso extremo; no se hace imagen nueva (decisión de persona 1 del 2026-10-30; paso 4)
- [ ] Para la recuperación sin pantalla: la caja Ugreen con su cable para conectar el SSD al PC y Windows + WSL con e2fsprogs 1.47 o posterior
- [ ] Copia actual de `config.txt` en `state/config/boot/firmware/config.txt` (la usa la recuperación sin pantalla)
- [ ] Ficheros en el repo:
      `state/config/etc/systemd/system/kmsg-espejo.service`,
      `state/config/etc/logrotate.d/kmsg-espejo`,
      `state/config/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`
- [ ] Pasos 9 a 11: cable USB-C macho → USB-A macho marcado USB 3.2 Gen 2 (10 Gbit/s), directo, sin adaptadores

## Pasos

### Paso 1: Detector de tareas bloqueadas y avisos anteriores

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, ADR-002 |

Comando:

```bash
ssh nas "uname -r; ls /proc/sys/kernel/hung_task_timeout_secs /proc/sys/kernel/hung_task_panic; cat /proc/sys/kernel/hung_task_timeout_secs /proc/sys/kernel/hung_task_panic /proc/sys/kernel/panic /proc/sys/kernel/hung_task_detect_count; grep -H '^kernel.panic' /etc/sysctl.d/*.conf"
ssh nas "journalctl --list-boots --no-pager | wc -l; journalctl _TRANSPORT=kernel -q --no-pager | wc -l; journalctl _TRANSPORT=kernel -q --no-pager | grep -c 'blocked for more than'"
```

`journalctl -k` implica `-b` (solo el arranque actual, `man journalctl`): para recorrer todos los
arranques guardados se filtra por `_TRANSPORT=kernel`.

Fuente: `Documentation/admin-guide/sysctl/kernel.rst` de Linux 6.18 (`hung_task_timeout_secs`,
`hung_task_panic` 0/1, `hung_task_detect_count`, `panic`); `man journalctl` del NAS. Ejecutado en
solo lectura el 2026-10-30 con estos mismos resultados.

Esperado: `6.18.50+rpt-rpi-2712` (o posterior); las dos rutas; `120`, `0`, `90`, `0`;
`/etc/sysctl.d/99-openmediavault.conf:kernel.panic = 90`. Después: `7` o más (cabecera + 6
arranques el 2026-10-30), `5842` o más, y `0`. Guarda la salida en el OPS.

Si falla: si `ls` dice `No such file or directory`, el kernel no tiene el detector: para y no
apliques el paso 7 (update-hld). Si el último número es 1 o más, **para**: con
`hung_task_panic=1` esos avisos habrían sido reinicios. Anota en el OPS qué tarea y cuándo con
`ssh nas "journalctl _TRANSPORT=kernel -q --no-pager -o short-iso | grep -A 3 'blocked for more than'"`
y vuelve al arquitecto (subir el umbral o no aplicar el panic). Si otro fichero fija
`kernel.panic`, anótalo: el del paso 7 tiene que ordenarse después de él.

### Paso 2: Velocidad del enlace del SSD (constancia hasta el cable nuevo)

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §2, §5, ADR-002 |

Comando:

```bash
ssh nas 'for d in /sys/bus/usb/devices/*; do test "$(cat $d/idVendor 2>/dev/null):$(cat $d/idProduct 2>/dev/null)" = 0bda:9210 && echo "${d##*/} speed=$(cat $d/speed) usb=$(cat $d/version) driver=$(readlink -f $d/${d##*/}:1.0/driver)"; done; journalctl -k -b --no-pager -q | grep -E "usb [0-9]+-[0-9]+: new .*USB device|scsi host[0-9]+: (uas|usb-storage)"; cat /sys/bus/usb/devices/1-1/speed; readlink -f /dev/disk/by-id/usb-KXG50ZNV_512G_NVMe_TOSHIB_01293805011E-0:0'
```

`lsusb` no está instalado: se lee `/sys/bus/usb/devices`. El bucle busca el puente por
`0bda:9210` porque con el cable nuevo cambiará de bus (`1-1` está en el bus USB 2; el USB 3 del
mismo controlador es el bus 2).

Fuente: sysfs de USB (`speed`, `version`, enlace `driver` del interfaz `:1.0`) y mensajes de
enumeración del kernel, leídos en el NAS el 2026-10-30.

Esperado: `1-1 speed=480 usb= 2.10 driver=/sys/bus/usb/drivers/usb-storage`;
`usb 1-1: new high-speed USB device number 2 using xhci-hcd` y `scsi host0: usb-storage 1-1:1.0`;
`480`; una ruta `/dev/sd…` (hoy `/dev/sda`: solo confirma que el enlace by-id existe; la letra no
se usa en ningún paso). Anota en el OPS: «SSD a 480M (USB 2.0, usb-storage) por el adaptador;
desviación del HLD §2/§5 (USB 3) hasta los pasos 9 a 11».

Si falla: si ya sale `speed=5000`, el adaptador ya no está: anótalo; en el paso 9 no hay cable que
cambiar (queda solo el reinicio de verificación, sin esperar a ningún cable) y después van el 10 y
el 11. Si el bucle no imprime nada, la caja no es la del diagnóstico: para y avisa.

### Paso 3: QVO, reglas de SnapRAID y carpetas compartidas

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §5, §6 |

Comando:

```bash
ssh nas "lsblk -o NAME,MODEL,SERIAL,MOUNTPOINTS | grep -B1 56801884; ls -A /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde; df -h /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde"
ssh nas "sudo omv-confdbadm read conf.service.snapraid.rule | grep -o '\"rule1\": \"[^\"]*\", \"rtype\": [01]'; sudo omv-confdbadm read conf.system.sharedfolder | grep -o '\"reldirpath\": \"[^\"]*\"'; ls /etc/snapraid/; dpkg-query -W util-linux logrotate; systemctl is-enabled logrotate.timer"
ssh nas "cat /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf" | diff - state/config/etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf && echo conf-igual
```

Fuente: lectura en el NAS el 2026-10-30 (mismos resultados que el esperado).

Esperado:
- `Samsung SSD 870 QVO 1TB  S5SVNG0N868475F` y debajo `└─sd…1  /srv/dev-disk-by-uuid-56801884-…`
  (el QVO, por modelo y serie); `Archivo`, `Documentos`, `Imagenes`, `lost+found`,
  `snapraid.content`, `snapraid.content.2026-10-15.bak`, `snapraid.content.lock` (sin
  `.nas-kmsg`); `Avail` 593G el 2026-10-30.
- Seis reglas, todas `"rtype": 0`: `*.unrecoverable`, `/lost+found/`, `/tmp/`, `.Trash-*/`,
  `.recycle/`, `/Imagenes/.immich-tmp/`. Cuatro `reldirpath`: `Documentos/persona1/`,
  `Documentos/persona2/`, `Imagenes/`, `Archivo/` (ninguna contiene `.nas-kmsg`).
  `nas.conf` y `omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf`; `logrotate 3.22.0-…` y
  `util-linux 2.41.5-…`; `enabled`.
- `conf-igual`: la copia del repo es la configuración activa (el paso 5 compara contra ella).

Si falla: si el modelo o la serie de la línea de `56801884` no son los del QVO, para. Si
`.nas-kmsg` ya existe, no borres nada: anota su contenido y avisa. Si alguna regla tiene
`"rtype": 1`, para: es un `include`, que limita SnapRAID a esa ruta (incidencia del RBK 06). Si
`diff` muestra diferencias, la copia del repo está atrasada: `/operator-plugin:snapshot-config` y
repite este paso antes del 5.

### Paso 4: Imagen del SSD (cubierta por la del 2026-10-28)

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | PC (WSL) |
| **HLD** | §3, ADR-002 |

No se hace imagen nueva ni apagado (decisión de persona 1 del 2026-10-30): la vuelta atrás del caso
extremo es la imagen del 2026-10-28, verificada entonces con `pigz -dc | wc -c` = `512110190592`
(OPS-2026-10-29-rbk16-resiliencia, E2). En `D:` quedan unos 140 GB y otra imagen ocupa ~173 GB: no
cabe. Restaurarla devuelve el SSD (sistema, Docker y bases de datos de Nextcloud e Immich) al
2026-10-28: deshace también el RBK 16, el UPD-2026-10-28 (con Nextcloud 34.0.5) y este RBK, que
habría que volver a aplicar. Este paso solo comprueba que la imagen sigue en su sitio.

Comando:

```bash
ls -l /mnt/d/_nas_imagenes/nas-ssd-2026-10-28.img.gz
```

Fuente: OPS-2026-10-29-rbk16-resiliencia (E2: `dd | pigz -1`, verificada con `pigz -dc | wc -c`);
leído en el PC el 2026-10-31 con este mismo resultado.

Esperado: `173305146822` bytes, fecha `Oct 28 22:17`.

Si falla: si el fichero no está o su tamaño es otro, para: sin imagen no hay vuelta atrás del caso
extremo. Decide el usuario (otra imagen exige 180 GB libres en `D:` y el procedimiento del RBK 16,
paso 2).

### Paso 5: Excluir `/.nas-kmsg/` de SnapRAID

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §5 SnapRAID |

Comprobación previa (fuera de 23:00-01:00 y sin SnapRAID en marcha):

```bash
ssh nas "date +%H:%M; ps -C snapraid --no-headers | wc -l"
```

Esperado de la previa: una hora fuera de 23:00-01:00 y `0`.

Comando (orden `set` exacta, despliegue y comprobaciones):

```bash
ssh nas "sudo omv-rpc -u admin SnapRaid setRule '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"rule1\":\"/.nas-kmsg/\",\"rtype\":0}'"
ssh nas "sudo omv-salt deploy run snapraid"
ssh nas "sudo omv-confdbadm read conf.service.snapraid.rule | grep -o '\"rule1\": \"/.nas-kmsg/\", \"rtype\": 0' | wc -l"
ssh nas "cat /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf" | diff state/config/etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf -
```

Fuente: `/usr/share/openmediavault/datamodels/rpc.snapraid.json` (`rpc.snapraid.setrule`: `uuid`,
`rule1`, `rtype` 0-1; `deleteRule`: `uuid`) y `/srv/salt/omv/deploy/snapraid/files/etc-snapraid_conf.j2`
(`rtype` 1 → `include`, 0 → `exclude`), leídos en el NAS el 2026-10-30; manual de SnapRAID
(`/RUTA/DIR/` selecciona ese directorio desde la raíz de cada disco y SnapRAID no entra en él).
Los campos `rule`, `arrayref` y `mntentref` del RBK 06 v2 no existen en este plugin.

Esperado: `setRule` devuelve un JSON con `rule1` `/.nas-kmsg/` (puede salir como
`\/.nas-kmsg\/`), `rtype` 0 y un `uuid` nuevo: anótalo en el OPS (es el de la vuelta atrás). El
despliegue termina con `Failed: 0`. Después `1` (sin duplicados) y el `diff` muestra una sola
línea añadida, `> exclude /.nas-kmsg/` (ningún `include`).

Si falla: si `setRule` da error, anota el mensaje y para. Si el recuento es `2`, borra la regla
sobrante con `ssh nas "sudo omv-rpc -u admin SnapRaid deleteRule '{\"uuid\":\"<uuid sobrante>\"}'"`
y vuelve a desplegar. Si el `diff` muestra un `include` u otras líneas, deshaz ya (vuelta atrás de
SnapRAID) antes de las 23:30 y para.

### Paso 6: Servicio `kmsg-espejo` y su rotación

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §5, §6 |

Comprobación previa:

```bash
ssh nas "ls -d /etc/systemd/system/kmsg-espejo.service /etc/logrotate.d/kmsg-espejo /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg 2>&1 | grep -c 'No such file'"
```

Esperado de la previa: `3` (no existe nada todavía).

Comando:

```bash
ssh nas "sudo install -d -o root -g root -m 0750 /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg"
cat state/config/etc/systemd/system/kmsg-espejo.service | ssh nas "sudo tee /etc/systemd/system/kmsg-espejo.service >/dev/null"
cat state/config/etc/logrotate.d/kmsg-espejo | ssh nas "sudo tee /etc/logrotate.d/kmsg-espejo >/dev/null"
ssh nas "sudo systemd-analyze verify /etc/systemd/system/kmsg-espejo.service; sudo systemctl daemon-reload && sudo systemctl enable --now kmsg-espejo.service && systemctl is-active kmsg-espejo.service"
ssh nas "echo 'kmsg-espejo: prueba RBK 17' | sudo tee /dev/kmsg >/dev/null"
ssh nas "sudo grep -c 'kmsg-espejo: prueba RBK 17' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log; sudo grep -c '=== kmsg-espejo: inicio' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log; sudo stat -c '%a %U:%G' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log; grep -c '^ExecStart=' /etc/systemd/system/kmsg-espejo.service; grep -l nas-kmsg /etc/logrotate.d/*"
ssh nas "sudo logrotate -d /etc/logrotate.d/kmsg-espejo 2>&1 | grep -E 'considering log|error'"
```

Fuente: `man systemd.exec` del NAS (`StandardOutput=append:ruta` abre en modo añadir y crea el
fichero si no existe; `UMask=`), `man systemd.unit` (`RequiresMountsFor=` añade `Requires=` y
`After=` de los montajes de la ruta; `%b` = ID del arranque), `dmesg --help` de util-linux 2.41.5
(`-w`, `--time-format iso`), `sys-utils/dmesg.c` de util-linux 2.41 (en modo follow hace
`setlinebuf(stdout)`: cada línea llega al fichero al momento), `man logrotate` 3.22
(`copytruncate`, `maxsize`, `rotate`, `delaycompress`). Una línea escrita por root en `/dev/kmsg`
entra en el búfer del kernel (prueba de extremo a extremo). La sintaxis de la unidad y de
logrotate se comprobó en el PC con `systemd-analyze verify` y `logrotate -d`.

Esperado: `verify` sin líneas que nombren `kmsg-espejo.service`; `Created symlink …
multi-user.target.wants/kmsg-espejo.service …` y `active`. Después `1` (la línea de prueba llegó
al QVO), `1` (un solo inicio), `750 root:root` (carpeta) y `640 root:root` (fichero), `1` (un solo
`ExecStart=`), `/etc/logrotate.d/kmsg-espejo` (ninguna otra regla rota ese fichero). Por último
`considering log /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log` y
ninguna línea con `error`.

Si falla: si `verify` se queja de la unidad, corrige el fichero en el repo y reenvíalo (sobrescribe,
no duplica). Si no queda `active`: `ssh nas "journalctl -u kmsg-espejo -n 20 --no-pager"`
(«Failed to set up standard output» = falta la carpeta: repite la primera línea). Si la prueba da
`0`, repite una vez la línea de los `grep`; si sigue en `0`, para. Si el fichero sale `644`, no es
un fallo (la carpeta `750` ya impide leerlo a otros usuarios): anótalo. Si logrotate dice
`insecure permissions`, la carpeta tiene que ser `750 root:root`.

### Paso 7: Reinicio automático ante tareas bloqueadas (sysctl)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §3, ADR-002 |

Comprobación previa (además, el paso 1 dio `0` avisos `blocked for more than` y el detector existe):

```bash
ssh nas "ls /etc/sysctl.d/; cat /proc/sys/kernel/hung_task_panic /proc/sys/kernel/panic"
```

Esperado de la previa: `90-caddy-nonlocal.conf`, `98-rpi.conf`, `99-openmediavault-mdadm.conf`,
`99-openmediavault.conf`, `README.sysctl` (sin `99-zz-nas-cuelgue-disco.conf`); `0`, `90`.

Comando:

```bash
cat state/config/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf | ssh nas "sudo tee /etc/sysctl.d/99-zz-nas-cuelgue-disco.conf >/dev/null"
ssh nas "sudo /usr/sbin/sysctl -p /etc/sysctl.d/99-zz-nas-cuelgue-disco.conf"
ssh nas "/usr/sbin/sysctl kernel.hung_task_timeout_secs kernel.hung_task_panic kernel.panic; grep -H -E '^kernel\.(panic|hung_task_panic|hung_task_timeout_secs) ' /etc/sysctl.d/*.conf /run/sysctl.d/*.conf /usr/lib/sysctl.d/*.conf"
```

Fuente: `Documentation/admin-guide/sysctl/kernel.rst` de Linux 6.18 (`hung_task_panic` 1 = panic
inmediato; `panic` positivo = reinicio tras ese número de segundos); `man sysctl.d` del NAS (gana el
fichero con el nombre lexicográficamente mayor, esté en el directorio que esté);
`dpkg-query -S /etc/sysctl.d/99-openmediavault.conf` → `openmediavault` (fichero del paquete: no
se edita); `/srv/salt/omv/deploy/sysctl/` solo genera `99-openmediavault-mdadm.conf` y
`99-openmediavault-nonrot.conf`, sin variable para `kernel.panic`. `sysctl` está en `/usr/sbin`,
fuera del PATH por SSH. Por qué 10 s: tras un panic systemd deja de alimentar el watchdog (14 s,
RBK 16) y el hardware reiniciaría igualmente; con 10 s reinicia el propio kernel antes y sin
depender del watchdog.

Esperado: `sysctl -p` imprime `kernel.hung_task_timeout_secs = 120`, `kernel.hung_task_panic = 1`
y `kernel.panic = 10`; la lectura repite los tres valores; `grep` da cuatro líneas:
`/etc/sysctl.d/99-openmediavault.conf:kernel.panic = 90` y las tres de
`/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf` (cada clave una sola vez en nuestro fichero). No se
provoca ningún panic de prueba.

Si falla: si `sysctl -p` dice `cannot stat /proc/sys/kernel/hung_task_panic`, el kernel no tiene
el detector: `ssh nas "sudo rm /etc/sysctl.d/99-zz-nas-cuelgue-disco.conf"` y para. Si `grep`
muestra otro fichero con estas claves, anótalo: en el paso 10 se comprueba cuál gana al arrancar.

### Paso 8: Raíz ext4 del SSD en `panic` ante errores

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §3, §5, ADR-002 |

Comprobación previa (la raíz es el XG5 por modelo y serie, está limpia y sin errores registrados, y
el paso 7 ya dejó `kernel.panic` en 10):

```bash
ssh nas "findmnt -n -o SOURCE,FSTYPE,OPTIONS /; readlink -f /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2; grep -c 'errors=' /etc/fstab; grep -H -o 'errors=[a-z-]*' /proc/fs/ext4/*/options; cat /proc/sys/kernel/panic"
ssh nas "sudo tune2fs -l /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2 | grep -E '^(Filesystem UUID|Filesystem state|Errors behavior|FS Error count|First error|Last error)'"
```

Esperado de la previa: `/dev/sda2 ext4 rw,noatime` y la misma ruta `/dev/sda2` (el enlace by-id del
XG5, serie `78EB616DKAWP`, es el dispositivo de `/`; la letra solo sirve para comparar las dos
líneas); `0` (fstab no pone `errors=`); una línea por cada ext4 montada, todas `errors=continue`
(la de la raíz y las de los discos SATA); `10`. Después
`Filesystem UUID: 02f61d5e-92cb-4f9c-a781-099d97795020`, `Filesystem state: clean` y
`Errors behavior: Continue`, sin líneas `FS Error count`, `First error` ni `Last error`.

Comando:

```bash
ssh nas "sudo tune2fs -e panic /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2"
ssh nas "sudo mount -o remount,errors=panic /"
ssh nas "sudo tune2fs -l /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2 | grep -E '^(Filesystem state|Errors behavior|FS Error count)'; grep -H -o 'errors=[a-z-]*' /proc/fs/ext4/*/options; findmnt -n -o SOURCE /; grep -c 'errors=' /etc/fstab"
```

`tune2fs -e panic` cambia el comportamiento por defecto guardado en el superbloque: es persistente
y no toca fstab. El kernel solo lo lee al montar, así que la raíz montada seguiría con
`errors=continue` hasta el arranque del paso 9; `mount -o remount,errors=panic /` lo aplica ya,
también sin tocar fstab (tras el arranque del paso 9 sale del superbloque). Desde ese momento, un
error que ext4 detecta en la raíz (lectura de metadatos o journal abortado) provoca
`EXT4-fs (device sda2): panic forced after error` y, con `kernel.panic = 10`, el reinicio. No se
provoca ningún panic de prueba.

**Riesgo que se acepta (bucle de reinicios):** si la raíz tuviera errores que vuelven en cada
arranque y que el `fsck -y` del initramfs no arregla (p. ej. un SSD o un puente que fallan
siempre), cada arranque acabaría en panic y reinicio a los 10 s, sin llegar a dar servicio. Para
salir: «Recuperación sin pantalla», puntos 4 y 5 (montar la raíz en el PC con `errors=continue` y
`tune2fs -e continue`). Con `continue` el NAS vuelve a arrancar aunque haya errores y se puede
diagnosticar (`/storage-plugin:diagnose-disk`) o restaurar la imagen del paso 4. Como el panic es
inmediato, ni el journal ni el espejo guardan ese último error (pregunta 3).

Fuente: `man tune2fs` del NAS (e2fsprogs 1.47.2: `-e continue|remount-ro|panic`; «a file system
error will cause e2fsck to check the file system on the next boot») y `man ext4` (`errors=`: el
valor por defecto está en el superbloque y se cambia con `tune2fs`);
`Documentation/admin-guide/ext4.rst` de Linux 6.18 (las opciones `errors=` de montaje prevalecen
sobre el superbloque); `fs/ext4/super.c` de rpi-6.18.y (`ext4_set_def_opts` lee `s_errors` solo al
montar; `errors=` se acepta al remontar y `ext4_apply_options` lo aplica; con `errors=panic`,
`ext4_handle_error` llama a `panic()` salvo durante un apagado; `/proc/fs/ext4/<dev>/options`
muestra siempre el `errors=` en uso) y `fs/ext4/ext4_jbd2.c` (journal abortado → `ext4_abort`);
`misc/tune2fs.c` de e2fsprogs 1.47.2 (`Setting error behavior to %d`: 3 = panic, 1 = continue);
`/boot/config-6.18.50+rpt-rpi-2712` (`CONFIG_BLK_DEV_WRITE_MOUNTED=y`: se puede escribir el
superbloque con la raíz montada); `/srv/salt/omv/setup/fstab/default.sls` (OMV solo añade
`noatime,nodiratime` a la línea de `/` si el SSD es no rotacional; ningún estado de OMV pone
`errors=` ni usa `tune2fs`). Leídos el 2026-10-31; la previa se ejecutó en solo lectura con este
resultado.

Esperado: `tune2fs 1.47.2 (1-Jan-2025)` y `Setting error behavior to 3`; el remontaje no imprime
nada. Después `Filesystem state: clean` y `Errors behavior: Panic` (sin `FS Error count`); la línea
de la raíz (el dispositivo que da `findmnt`, hoy `sda2`) con `errors=panic` y las de los discos SATA
con `errors=continue`; la ruta de la raíz; `0` (fstab sin tocar).

Si falla: si en la previa `/` y el enlace by-id no dan la misma ruta, para: no es la raíz. Si sale
`FS Error count`, `First error`, `Last error` o un estado distinto de `clean`, para: la raíz ya tiene
errores registrados y con `panic` podrían acabar en un bucle de reinicios; experto en discos
(`/storage-plugin:diagnose-disk`). Si `tune2fs -e` da un error, anótalo y para: no ha cambiado nada.
Si el remontaje falla o la raíz sigue con `errors=continue`, anota el mensaje y sigue: el superbloque
ya dice `Panic` y valdrá desde el arranque del paso 9 (se comprueba en el 10). Si después aparecen
reinicios no deseados: «Vuelta atrás», raíz.

> Paso 9: **una orden cada vez**. No pegues nada más en esa terminal hasta ver el prompt del PC.

### Paso 9: Apagado de verificación y cable USB 3 directo (cuando llegue)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH y Físico |
| **HLD** | §2, §3, §5, ADR-002 |

Este apagado es también el reinicio de verificación de los pasos 6, 7 y 8 (decisión de persona 1
del 2026-10-30: no hay reinicio aparte). Hasta que llegue el cable, los cambios funcionan en
caliente y los pasos 9 a 11 quedan pendientes (OPS Parcial). Si el paso 2 ya dio `speed=5000`, no
hay cable que cambiar: en lugar del apagado, `ssh nas "sudo reboot"`, y después los pasos 10 y 11.

Comprobación previa: cable USB-C macho → USB-A macho marcado USB 3.2 Gen 2 (10 Gbit/s), sin
adaptadores; fuera de 23:00-01:00 y sin SnapRAID en marcha:

```bash
ssh nas "date +%H:%M; ps -C snapraid --no-headers | wc -l"
```

Comando (una sola orden):

```bash
ssh nas "sudo poweroff"
```

Después, **con el LED verde apagado** (nunca mientras parpadee): desenchufar los 12 V; quitar el
adaptador USB-C hembra → USB-A macho y el cable que lleva; conectar el cable nuevo, el USB-C en la
caja Ugreen y el USB-A en un puerto **USB-A azul** de la Pi (los negros son USB 2; el USB-C de la
Pi 5 es solo de alimentación); enchufar los 12 V.

Esperado: en la previa, una hora fuera de 23:00-01:00 y `0`; la sesión se corta (normal); en menos
de 10 min `ssh -o BatchMode=yes nas hostname` responde `nas`.

Si falla: si no vuelve en 10 min con el LED verde quieto, desenchufa los 12 V (LED quieto), vuelve
a poner el adaptador anterior (arrancaba con él) y enchufa; si sigue sin volver, «Recuperación
sin pantalla». Si el NAS vuelve y se cae solo una y otra vez (cada pocos minutos), es el panic del
paso 7 o del 8 en cada arranque: «Recuperación sin pantalla», puntos 4 y 5.

### Paso 10: Comprobar el espejo, el sysctl y la raíz tras el arranque

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, §5 |

Tras el arranque del paso 9. Si antes del cable el NAS se reinicia por otro motivo (UPD, corte de
luz), este paso se puede hacer tras ese arranque; el 9 y el 11 siguen pendientes del cable.

Comando:

```bash
ssh nas "journalctl --list-boots --no-pager | tail -n 1; systemctl is-active kmsg-espejo.service; systemctl show -p RequiresMountsFor kmsg-espejo.service; sudo grep '=== kmsg-espejo: inicio' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log | tail -n 1; sudo tail -n 2 /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log"
ssh nas "cat /proc/sys/kernel/hung_task_timeout_secs /proc/sys/kernel/hung_task_panic /proc/sys/kernel/panic /proc/sys/kernel/hung_task_detect_count; journalctl -b -u systemd-sysctl --no-pager -q | grep -c -i -E 'fail|could not|couldn'; systemctl list-units --state=failed --no-legend | grep -v -c quotaon"
ssh nas "sudo tune2fs -l /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2 | grep -E '^(Filesystem state|Errors behavior|FS Error count)'; grep -H -o 'errors=[a-z-]*' /proc/fs/ext4/*/options; findmnt -n -o SOURCE /"
```

Fuente: `man systemd.unit` (`%b`), `man sysctl.d`; los valores se leen de `/proc/sys` (lo mismo que
`sysctl -n`, sin confirmación del guard). Raíz: las fuentes del paso 8 (tras arrancar, el `errors=`
en uso sale del superbloque, sin remontaje).

Esperado: la última línea de `--list-boots` es el arranque actual (anota su ID); `active`;
`RequiresMountsFor=/srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg`; la
última marca es `=== kmsg-espejo: inicio, arranque <ID> ===` con **el mismo ID** (32 caracteres
hexadecimales, sin guiones); dos líneas del kernel con fecha ISO de hoy (`2026-…T…+04:00`);
`120`, `1`, `10`, `0`; `0`; `0` (solo fallan las tres `quotaon@…` ya conocidas). Raíz:
`Filesystem state: clean` y `Errors behavior: Panic`, sin `FS Error count`; la línea del
dispositivo de `/` (el que da `findmnt`) con `errors=panic` y las de los discos SATA con
`errors=continue`.

Si falla: si la última marca no es la del arranque actual, el servicio no arrancó tras montar el
QVO: `ssh nas "journalctl -b -u kmsg-espejo --no-pager"` y
`ssh nas "systemctl show -p After kmsg-espejo.service"`. Si `kernel.panic` vuelve a ser `90`,
otro fichero se aplica después del nuestro:
`ssh nas "ls /etc/sysctl.d/ /run/sysctl.d/ /usr/lib/sysctl.d/"`, anótalo y vuelve al arquitecto.
Si hay otro servicio fallido, anótalo en el OPS como incidencia. Si `Errors behavior` es
`Continue`, el cambio del paso 8 no persistió: anótalo y repite el paso 8. Si es `Panic` pero la
raíz sale con `errors=continue`, algo la monta con esa opción
(`ssh nas "grep -c 'errors=' /etc/fstab; cat /proc/cmdline"`): anótalo y vuelve al arquitecto. Si
con el cable nuevo no existe el enlace `ata-…-part2`, usa
`/dev/disk/by-id/usb-KXG50ZNV_512G_NVMe_TOSHIB_01293805011E-0:0-part2` (el mismo SSD por la serie de
la caja) y anótalo.

### Paso 11: Comprobar enlace USB 3 y driver `uas` (cuando llegue el cable)

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §2, §5, ADR-002 |

Comando:

```bash
ssh nas 'for d in /sys/bus/usb/devices/*; do test "$(cat $d/idVendor 2>/dev/null):$(cat $d/idProduct 2>/dev/null)" = 0bda:9210 && echo "${d##*/} speed=$(cat $d/speed) usb=$(cat $d/version) driver=$(readlink -f $d/${d##*/}:1.0/driver)"; done; journalctl -k -b --no-pager -q | grep -E "usb [0-9]+-[0-9]+: new .*USB device|scsi host[0-9]+: (uas|usb-storage)"; readlink -f /dev/disk/by-id/usb-KXG50ZNV_512G_NVMe_TOSHIB_01293805011E-0:0; cat /proc/sys/vm/dirty_expire_centisecs; ls /etc/sysctl.d/; systemctl is-active kmsg-espejo.service'
```

Fuente: el mismo bucle del paso 2; los dos buses USB 3 de la Pi 5 (`usb2` y `usb4`) anuncian
`speed` 5000 en sysfs (leído el 2026-10-30).

Esperado: `2-1 speed=5000 usb= 3.x driver=/sys/bus/usb/drivers/uas` (o `4-1` en el otro puerto
azul; 5000 es el máximo de los USB 3 de la Pi 5: 10000 no puede salir en este equipo);
`usb 2-1: new SuperSpeed USB device …` y `scsi hostN: uas`; una ruta `/dev/sd…`; `3000`; la lista
de `/etc/sysctl.d/` sin `99-openmediavault-nonrot.conf`; `active`. Anota en el OPS «SSD a 5000M
con uas desde AAAA-MM-DD».

Si falla: si sale `speed=480`, el cable o el puerto no son USB 3: comprueba que es un puerto azul
y la marca del cable, y repite el paso 9 con el otro puerto azul; si sigue en 480, anótalo para el
HLD. Si sale `speed=5000` con `usb-storage`, funciona sin UAS: anótalo. Si en los días siguientes el
espejo muestra `uas_eh_abort_handler` o reinicios del puente, anótalo para el HLD (pregunta 1).
Si aparece `99-openmediavault-nonrot.conf` o el valor no es `3000`, pregunta 6.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Espejo activo | `ssh nas "systemctl is-active kmsg-espejo.service"` | active |
| Ligado al montaje del QVO | `ssh nas "systemctl show -p RequiresMountsFor kmsg-espejo.service"` | `RequiresMountsFor=/srv/dev-disk-by-uuid-56801884-…/.nas-kmsg` |
| Escribe en el arranque actual | `ssh nas "sudo grep '=== kmsg-espejo: inicio' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log \| tail -n 1"` | el ID del último arranque de `journalctl --list-boots` |
| Rotación acotada | `ssh nas "sudo logrotate -d /etc/logrotate.d/kmsg-espejo 2>&1 \| grep -c error"` | 0 |
| Fuera de SnapRAID | `ssh nas "grep -c '^exclude /.nas-kmsg/$' /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf"` | 1 |
| Sin include en SnapRAID | `ssh nas "grep -c '^include' /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf"` | 0 |
| Panic ante tareas bloqueadas | `ssh nas "/usr/sbin/sysctl kernel.hung_task_timeout_secs kernel.hung_task_panic kernel.panic"` | 120, 1, 10 |
| Ninguna tarea bloqueada | `ssh nas "cat /proc/sys/kernel/hung_task_detect_count"` | 0 |
| Raíz en panic ante errores | `ssh nas "sudo tune2fs -l /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2 \| grep 'Errors behavior'; grep -H -o 'errors=[a-z-]*' /proc/fs/ext4/*/options; findmnt -n -o SOURCE /"` | `Panic`; el dispositivo de `/` con `errors=panic`, los discos SATA con `errors=continue` |
| Enlace del SSD | `ssh nas "cat /sys/bus/usb/devices/1-1/speed"` | 480 hasta el cable; con el cable, el bucle del paso 11: 5000 y uas |
| SSH solo con clave | `ssh -o BatchMode=yes nas hostname` | nas |

## Tras un cuelgue: leer el espejo

Después de un reinicio solo (panic) o con el botón, lo primero (el agente, en solo lectura):

```bash
ssh nas "journalctl --list-boots --no-pager | tail -n 3; sudo grep -n '=== kmsg-espejo: inicio' /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log | tail -n 2"
ssh nas "sudo head -n <N> /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log | tail -n 81"
ssh nas "sudo grep '^rootfs' /run/initramfs/fsck.log"
```

`<N>` es el número de línea de la última marca (el arranque actual): salen las 80 últimas líneas
del arranque colgado y la marca. Si la última marca está en la línea 1, logrotate rotó entre medias:
repite con `kmsg.log.1`. La tercera orden dice qué encontró el `fsck -y` del initramfs en la raíz al
arrancar: `rootfs: clean, …` si nada; tras un panic de ext4 (paso 8) saldrán las reparaciones. Qué
buscar:

- `reset high-speed USB device`, `I/O error`, `timing out command`, `offline device`,
  `EXT4-fs error`: el puente o el SSD fallaron. Desde el paso 8, un error de ext4 en la raíz
  reinicia el NAS a los 10 s y puede no llegar al espejo (pregunta 3). Si el NAS se quedó colgado
  sin reiniciarse solo, el fallo no bloqueó tareas 120 s ni dio un error que ext4 detectase en la
  raíz (pregunta abierta 2).
- `blocked for more than` no saldrá: el panic es inmediato y no da tiempo a copiarlo (pregunta 3).
- Errores `ataN` de un disco de datos justo antes del reinicio: el bloqueo vino de ese disco.
  Experto en discos (`/storage-plugin:diagnose-disk`) y, mientras, vuelta atrás del sysctl para no
  entrar en un bucle de reinicios.

Pueden faltar las últimas ~35 s (aún en memoria al colgarse). Las horas ISO se calculan al arrancar
el servicio: si el reloj se corrigió después (solo pasa si el RTC de la Pi pierde la hora, p. ej.
al quitar los 12 V), guíate por el orden de las líneas. Copia lo relevante en el OPS del incidente.

## Recuperación sin pantalla

Usar si la Pi no vuelve a la red 10 minutos después del paso 9 con el LED verde quieto, o si
vuelve y se reinicia sola una y otra vez (panic del paso 7 o del 8 en cada arranque: bucle de
reinicios). Lo hace el usuario en el PC; el agente da los comandos.

1. Comprobar que el LED verde no parpadea; desenchufar los 12 V, sacar el SSD en su caja y
   conectarlo al PC con el cable de la caja.
2. Windows: abrir la unidad `bootfs` (p. ej. `E:`). Si pide formatear: `chkdsk E: /f` en consola de
   administrador tras confirmar la letra en el Explorador; nunca formatear.
3. Comparar `config.txt`: `Get-FileHash E:\config.txt` frente a
   `sha256sum state/config/boot/firmware/config.txt`; si difieren, restaurar desde el repo.
4. Leer el rootfs (PowerShell como administrador):
   `wsl --mount \\.\PHYSICALDRIVEn --partition 2 --options "errors=continue"`
   (`n` con `Get-Disk` por modelo `KXG50ZNV` y tamaño; `errors=continue` porque desde el paso 8 la
   raíz pide `panic` y un error de ext4 tiraría el kernel de WSL); queda en `/mnt/wsl/PHYSICALDRIVEnp2`. Logs
   del arranque fallido: `wsl.exe -u root journalctl -D /mnt/wsl/PHYSICALDRIVEnp2/var/log/journal --list-boots`
   y `… -b -1 -p warning`. El espejo está en el QVO: se lee en el NAS cuando vuelva.
5. Deshacer este RBK sin red:
   `wsl.exe -u root rm /mnt/wsl/PHYSICALDRIVEnp2/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`
   (quita el panic: corta un bucle de reinicios) y, para no arrancar el espejo,
   `wsl.exe -u root rm /mnt/wsl/PHYSICALDRIVEnp2/etc/systemd/system/multi-user.target.wants/kmsg-espejo.service`.
   La raíz, a `continue` (corta el bucle del paso 8), en WSL (terminal de Ubuntu) y por el UUID de
   la raíz del NAS, que solo puede ser ese SSD:
   `sudo tune2fs -e continue UUID=02f61d5e-92cb-4f9c-a781-099d97795020` → `Setting error behavior to 1`;
   comprobar con `sudo tune2fs -l UUID=02f61d5e-92cb-4f9c-a781-099d97795020 | grep 'Errors behavior'`
   → `Continue`.
6. Desmontar: `wsl.exe -u root umount /mnt/wsl/PHYSICALDRIVEnp2` y `sync`; luego
   `wsl --unmount \\.\PHYSICALDRIVEn`. Desconectar solo tras el desmontaje.
7. Volver a poner el SSD en el puerto **USB-A azul** de la Pi (el USB-C de la Pi 5 es solo de
   alimentación) y enchufar los 12 V.
8. Si nada de lo anterior funciona: restaurar la imagen del 2026-10-28
   (`D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`, paso 4; deshace también el RBK 16, el
   UPD-2026-10-28 y este RBK) (lo hace el usuario; destructivo sobre el SSD: identificarlo por
   modelo y serie con `lsblk -o NAME,SIZE,MODEL,SERIAL`).

Esperado: la Pi vuelve a responder a `ssh nas`.

## Vuelta atrás

- **Sysctl** (lo primero si aparecen reinicios no deseados):
  `ssh nas "sudo rm /etc/sysctl.d/99-zz-nas-cuelgue-disco.conf && sudo /usr/sbin/sysctl -w kernel.hung_task_panic=0 kernel.panic=90"`.
  Queda como antes: 120 s es el valor del kernel y `kernel.panic = 90` lo vuelve a poner el fichero
  de OMV en cada arranque. Comprobar con `ssh nas "cat /proc/sys/kernel/hung_task_panic /proc/sys/kernel/panic"`
  → `0` y `90`.
- **Raíz** (paso 8; también ante reinicios no deseados):
  `ssh nas "sudo tune2fs -e continue /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2"`
  (`Setting error behavior to 1`) y `ssh nas "sudo mount -o remount,errors=continue /"`. Comprobar
  con `ssh nas "sudo tune2fs -l /dev/disk/by-id/ata-KXG50ZNV512G_NVMe_TOSHIBA_512GB_78EB616DKAWP-part2 | grep 'Errors behavior'"`
  → `Continue` y `ssh nas "grep -H -o 'errors=[a-z-]*' /proc/fs/ext4/*/options"` → todas
  `errors=continue`. Sin red (bucle de reinicios): «Recuperación sin pantalla», puntos 4 y 5.
- **Espejo**: `ssh nas "sudo systemctl disable --now kmsg-espejo.service"` y
  `ssh nas "sudo rm /etc/systemd/system/kmsg-espejo.service /etc/logrotate.d/kmsg-espejo && sudo systemctl daemon-reload"`.
  Los logs de `.nas-kmsg` se conservan (son el diagnóstico); para quitarlos,
  `ssh nas "sudo rm /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg/kmsg.log*"` y
  `ssh nas "sudo rmdir /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/.nas-kmsg"`.
- **SnapRAID** (después de quitar la carpeta; si no, el sync siguiente la metería en la paridad):
  `ssh nas "sudo omv-rpc -u admin SnapRaid deleteRule '{\"uuid\":\"<uuid del paso 5>\"}'"`,
  `ssh nas "sudo omv-salt deploy run snapraid"` y el `diff` del paso 3 vuelve a dar `conf-igual`.
- **Cable**: el adaptador anterior sigue funcionando (480M).
- **Caso extremo**: la imagen del 2026-10-28 del paso 4 («Recuperación sin pantalla», punto 8).

## Evidencias

- Salida de los pasos 1, 2 (480M), 3 y 4 (imagen del 2026-10-28 en su sitio) en el OPS, antes de
  cambiar nada.
- `uuid` de la regla nueva y `diff` del paso 5; prueba del paso 6; valores del paso 7; previa y
  comprobación del paso 8 (`Errors behavior` antes y después, `errors=` de `/proc/fs/ext4`);
  comprobaciones del paso 10 tras el arranque del 9; enlace del paso 11 con el cable nuevo.
- Ficheros versionados: `state/config/etc/systemd/system/kmsg-espejo.service`,
  `state/config/etc/logrotate.d/kmsg-espejo`, `state/config/etc/sysctl.d/99-zz-nas-cuelgue-disco.conf`;
  tras ejecutar, `/operator-plugin:snapshot-config` para la copia de la configuración de SnapRAID
  con la línea nueva.
- `state/applied.yaml`: fase 17 (lo hace `approve-ops`); el OPS queda Parcial hasta los pasos 9 a 11.
- Tras cada cuelgue: las líneas del espejo («Tras un cuelgue») en el OPS o en la nota del incidente.

## Preguntas abiertas para el HLD (update-hld)

1. **ADR del disco del sistema.** HLD §2 y §5 dicen «caja USB 3», pero el enlace real es 480M
   (USB 2, `usb-storage`) por un adaptador. Propuesta: exigir cable USB-C → USB-A USB 3 directo,
   sin adaptadores, y comprobar `speed` 5000 y `uas` (bucle del paso 11) en cada UPD y MNT. Si con
   `uas` aparecen `uas_eh_abort_handler` o reinicios del puente en el espejo, decidir si se fuerza
   `usb-storage` para el `0bda:9210` con el parámetro `usb-storage.quirks` del kernel (RBK aparte).
2. **Relación con la comprobación diaria de servicios** (decisión de persona 1 del 2026-10-28:
   comprobar SSH, Nextcloud e Immich una vez al día, reiniciar y avisar). Este RBK la complementa,
   no la sustituye. Cubre el bloqueo del SSD con tareas en estado D 120 s o más (reinicio en 2-4
   min) y, desde la versión 3.1 (paso 8, decisión de persona 1 del 2026-10-30), el SSD que
   desaparece con errores de E/S que ext4 detecta en la raíz (`Errors behavior: Panic`). No cubre:
   (a) un error al escribir solo datos de un fichero (queda en aviso, sin panic); (b) servicios
   caídos con el disco sano. Un vigilante que se lanza desde el SSD no puede ejecutarse si el SSD
   ya no responde: no puede ser el único mecanismo. El espejo del próximo incidente dirá cuál de
   los casos fue, salvo las últimas ~35 s (pregunta 3).
3. **El mensaje del panic se pierde** (el de las tareas bloqueadas del paso 7 y el
   `EXT4-fs … panic forced after error` del paso 8): ni el journal (en el SSD) ni el espejo lo
   reciben, porque el panic es inmediato. Opción: `dtoverlay=ramoops-pi5` (está en `/boot/firmware/overlays`) con
   `systemd-pstore` (ya activo) para conservarlo tras el reinicio; toca `config.txt`: RBK aparte.
4. **Efecto lateral**: un disco de datos que falle con reintentos ATA de más de 120 s también
   reiniciará el NAS (posible bucle a las 23:30, con el sync). ¿Se acepta, o se sube
   `hung_task_timeout_secs` (p. ej. 300 s, más lento ante un cuelgue del SSD)?
5. **Reflejar en el HLD**: exclusión `/.nas-kmsg/` en §5 SnapRAID; servicio `kmsg-espejo` y su
   rotación en §6 «Otros»; `99-zz-nas-cuelgue-disco.conf` (prevalece sobre `kernel.panic = 90` de
   OMV) en §3; raíz ext4 con `Errors behavior: Panic` en el superbloque (sin `errors=` en fstab), su
   riesgo de bucle de reinicios y la salida con `tune2fs -e continue` desde el PC en §3 y §5.
6. Con el cable nuevo el SSD puede declararse no rotacional; entonces el estado salt `sysctl` de OMV
   (`nonrot.sls`) pondría en su siguiente despliegue `vm.dirty_expire_centisecs` y
   `vm.dirty_writeback_centisecs` a 12000 y `vm.laptop_mode` a 5, y el espejo tardaría hasta ~2 min
   en llegar al QVO. Se evita con las variables `OMV_SYSCTL_VM_*` de `nonrot.sls` en
   `/etc/default/openmediavault` (decisión del arquitecto).

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 3.0 | 2026-10-30 | Runbook Agent | Creación tras el segundo cuelgue (2026-10-30): espejo de los mensajes del kernel en el QVO, panic ante tareas bloqueadas con reinicio a 10 s, constancia del enlace del SSD a 480M y verificación con el cable USB 3 |
| 3.1 | 2026-10-31 | Runbook Agent | Decisiones de persona 1 del 2026-10-30 antes de aprobar. (a) Paso 8 nuevo: raíz ext4 del XG5 a `panic` con `tune2fs -e panic` (superbloque, sin tocar fstab) y `mount -o remount,errors=panic /`, porque el kernel solo lee el superbloque al montar (`fs/ext4/super.c`); previa (raíz por by-id, `clean`, sin errores registrados), comprobación con `tune2fs -l` y `/proc/fs/ext4/*/options`, riesgo de bucle de reinicios y su salida (montaje en WSL con `errors=continue` y `tune2fs -e continue UUID=…`), vuelta atrás y comprobación tras el arranque (paso 10). (b) Sin imagen nueva: el paso 4 solo comprueba la imagen verificada del 2026-10-28, vuelta atrás del caso extremo. El reinicio de verificación es el apagado del cambio de cable: desaparece el reinicio aparte (antiguo paso 8) y el cable pasa al paso 9 y las comprobaciones tras el arranque al 10 (antes 10 y 9). Límite, «Tras un cuelgue» (`fsck.log`), verificación final y preguntas 2, 3 y 5 al día |
| 3.1 | 2026-10-31 | Runbook Agent | Estado cambiado a Aprobado (persona 1: «a) Ampliar la protección OK; b OK», 2026-10-30/31; el remontaje `errors=panic` del paso 8 es la forma de que (a) valga ya, dentro de lo aprobado) |
