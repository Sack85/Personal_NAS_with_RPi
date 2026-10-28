# RBK 16 — Resiliencia: journal persistente, watchdog y aviso de sync

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 16 — Resiliencia |
| **Versión** | 3.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-28 |
| **Última modificación** | 2026-10-28 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h 30 min (incluye imagen del SSD y un reinicio) |

## Objetivo

Que un cuelgue como el del 2026-10-21 al 28 (ping OK, todos los puertos TCP rechazados, Tailscale
vivo; último sync de SnapRAID el 2026-10-20 23:37; reinicio forzado con el botón 30 s) **deje
logs** y **avise por correo** en menos de 48 h. Tres cambios (HLD §3, §5, §9, §11):

1. **Journal persistente en el SSD.** En este NAS no hay folder2ram: OMV 8 usa el plugin
   `openmediavault-writecache` 8.3.0, que monta `/var/log` como overlay en tmpfs y solo lo vuelca
   al SSD en un apagado limpio. Un cuelgue o un corte pierden todo: por eso `journalctl
   --list-boots` solo muestra el 2026-10-09 y el arranque actual. Se quita `/var/log` de las rutas
   de writecache (escritura directa en el SSD NVMe, que es lo que protege ADR-002) y se pone
   `journald_storage = persistent`, con `SystemMaxUse=500M` por la variable de OMV. El resto de
   rutas de writecache se conservan.
2. **Watchdog hardware.** Ya está activo: OMV fija `RuntimeWatchdogSec=14s` y systemd usa
   `/dev/watchdog0` (Broadcom BCM2835); `RebootWatchdogSec` efectivo = 2 min. El error del arranque
   `Failed to find module 'softdog'` sale de `/etc/modules-load.d/openmediavault-watchdog.conf`
   (generado por OMV con su valor por defecto `softdog`, que el kernel de la Pi no trae). Se corrige
   con `OMV_WATCHDOG_MODULE_NAME="bcm2835_wdt"` y `omv-salt deploy run watchdog` (sin editar el
   fichero generado) y se deja `RebootWatchdogSec=2min` explícito en un drop-in propio. 14 s y no
   15 s: el máximo del bcm2835 es ~15 s y OMV ya lo limita; 14 s deja margen.
   **Limitación:** el watchdog de systemd solo reinicia si el kernel o PID 1 se cuelgan. En el
   incidente el kernel respondía a ping y Tailscale seguía vivo, así que **probablemente no lo
   habría reiniciado**. Por eso el aviso del punto 3 y la pregunta abierta para el HLD.
3. **Aviso por correo si `snapraid.content` tiene más de 48 h.** Script
   `snapraid-content-vigila` con temporizador systemd diario a las 12:00 (fuera de la cadena de
   23:00-01:00, ADR-015), que lee `/snapraid.content` del SSD (no despierta los discos) y envía a
   `root` por el correo de OMV ya configurado (postfix con relay a Gmail; `root` está en
   `recipient_canonical`).

Ficheros en `state/config/`, enviados con `cat <fichero> | ssh nas "sudo tee <ruta> >/dev/null"`.

> Todas las órdenes son de **una línea** (`ssh nas "…"` o `ssh -t nas "…"`). Nunca pegues varias
> líneas seguidas tras `ssh nas`: si la sesión se corta en el reinicio, las líneas restantes se
> ejecutan en el PC. En los pasos con apagado o reinicio, **una orden cada vez**.

## Prerrequisitos

- [ ] NAS accesible con `ssh nas` tras el reinicio forzado del 2026-10-28
- [ ] Correo de OMV funcionando (RBK 04): ha llegado algún aviso de SMART o SnapRAID
- [ ] Copia actual de `config.txt` en `state/config/boot/firmware/config.txt` (la usa la recuperación sin pantalla)
- [ ] Lector USB-SATA/NVMe para el SSD, PC con Windows + WSL y espacio en `D:` para la imagen (~180 GB usados)
- [ ] Ficheros en el repo:
      `state/config/omv/writecache-setSettings.json`,
      `state/config/etc/systemd/system.conf.d/60-nas-watchdog.conf`,
      `state/config/usr/local/sbin/snapraid-content-vigila`,
      `state/config/etc/systemd/system/snapraid-content-vigila.service` y `.timer`
- [ ] No hace falta paridad al día para esta fase (no toca discos de datos ni paridad)

## Pasos

### Paso 1: Foto del estado actual

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, §5 |

Comando:

```bash
ssh nas "findmnt -n -o FSTYPE /var/log; journalctl --list-boots | tail -n 3; grep -h -v '^#' /etc/modules-load.d/openmediavault-watchdog.conf /etc/systemd/system.conf.d/openmediavault-watchdog.conf; systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec; cat /sys/class/watchdog/watchdog0/identity; stat -c '%y' /snapraid.content; sudo grep -c '^root' /etc/postfix/recipient_canonical"
```

Fuente: lectura en el NAS del 2026-10-28 (`/srv/salt/omv/deploy/writecache/default.sls`,
`/srv/salt/omv/deploy/watchdog/default.sls`, `/usr/sbin/omv-writecache`).

Esperado: `overlay`; dos arranques (2026-10-09 y el actual); `softdog`, `[Manager]`,
`RuntimeWatchdogSec=14s`; `RuntimeWatchdogUSec=14s`, `RebootWatchdogUSec=2min`;
`Broadcom BCM2835 Watchdog timer`; fecha de `snapraid.content` (2026-10-20 23:37 o posterior si
ya corrió el sync de esta noche); `1`. Guarda la salida en el OPS.

Si falla: si `/var/log` ya no es `overlay` o el módulo ya es `bcm2835_wdt`, alguien lo cambió:
para y avisa antes de seguir.

### Paso 2: Apagado limpio e imagen del SSD

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH y PC |
| **HLD** | §3, ADR-002 |

Comprobación previa: `state/config/boot/firmware/config.txt` existe en el repo (si no,
`/operator-plugin:snapshot-config` antes de apagar).

Comando (una sola orden; nunca desenchufar sin ella):

```bash
ssh nas "sudo poweroff"
```

Después, **con el LED verde apagado** (nunca mientras parpadee): desenchufar los 12 V, sacar el
SSD y conectarlo al PC. Imagen de sus particiones en `D:`:
- Windows: Win32 Disk Imager con «Read Only Allocated Partitions».
- O WSL (PowerShell como administrador): `wsl --mount \\.\PHYSICALDRIVEn --bare`; en WSL
  identificar el SSD con `lsblk -o NAME,SIZE,MODEL,SERIAL` (por modelo y serie, nunca por letra) y
  leerlo con `sudo dd if=/dev/sdX of=/mnt/d/nas-ssd-2026-10-28.img bs=4M status=progress conv=sparse`
  (solo lee el SSD; `of=` es un fichero en D:); después `wsl --unmount \\.\PHYSICALDRIVEn`.

Volver a poner el SSD en el puerto **USB-A azul** de la Pi (el USB-C de la Pi 5 es solo de
alimentación) y enchufar los 12 V.

Esperado: imagen en `D:`; tras encender, `ssh -o BatchMode=yes nas hostname` responde `nas` en
menos de 10 min.

Si falla: si la imagen falla o no cabe, no sigas: libera espacio y repite. Si la Pi no vuelve en
10 min con el LED verde quieto, ve a «Recuperación sin pantalla».

### Paso 3: Sacar `/var/log` de writecache y journal persistente

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §3, §11 |

Comprobación previa (la configuración actual coincide con la que se envía salvo `/var/log` y
`journald_storage`):

```bash
ssh nas "sudo omv-rpc -u admin WriteCache getSettings" | python3 -c "import json,sys; a=json.load(sys.stdin); a.pop('status',None); b=json.load(open('state/config/omv/writecache-setSettings.json')); print(sorted(k for k in a if a[k]!=b.get(k)))"
```

Esperado de la previa: `['journald_storage', 'paths']`.

Comando (orden `set` exacta con el JSON del repo, despliegue y comprobación):

```bash
cat state/config/omv/writecache-setSettings.json | ssh nas 'sudo omv-rpc -u admin WriteCache setSettings "$(cat)" >/dev/null && echo set-ok'
ssh nas "sudo omv-salt deploy run writecache"
ssh nas "sudo omv-rpc -u admin WriteCache getSettings | grep -o '/var/log = ' | wc -l; grep -c '^Storage=persistent$' /etc/systemd/journald.conf.d/50-writecache.conf; grep -c '^/var/log' /etc/omv-writecache/config.yaml; findmnt -n -o FSTYPE /var/log || echo 'ssd-directo'"
```

Fuente: `omv-rpc` y el datamodel `conf.service.writecache.json` leídos en el NAS
(`journald_storage` admite `auto`, `volatile`, `persistent`); `default.sls` de writecache (genera
`50-writecache.conf` y ejecuta `omv-writecache remount --reconfigure`).

Esperado: `set-ok`; el deploy termina con `Failed: 0`; luego `0` (ninguna ruta `/var/log` en
writecache, sin duplicados), `1`, `0` y `ssd-directo`. Si `findmnt` aún dice `overlay`, se aplica
en el reinicio del paso 7 (con `flush_on_shutdown` el contenido del overlay se vuelca al SSD al
apagar): anótalo y sigue.

Si falla: si `setSettings` da error de esquema, reenvía el JSON tal cual del repo (sobrescribe, no
duplica). Si el deploy falla, para: vuelta atrás con `writecache-setSettings.json` del git anterior
(ver «Vuelta atrás»).

### Paso 4: Límite del journal y módulo del watchdog por variables de OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, §11 |

Comprobación previa:

```bash
ssh nas "grep -c -E '^OMV_(WATCHDOG_MODULE_NAME|SYSTEMD_JOURNALD_SYSTEMMAXUSE)=' /etc/default/openmediavault"
```

Esperado de la previa: `0` (si da `1` o `2`, no añadas: edita la línea existente con
`sudo sed -i`).

Comando:

```bash
ssh nas "printf '%s\n' 'OMV_WATCHDOG_MODULE_NAME=\"bcm2835_wdt\"' 'OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE=\"500M\"' | sudo tee -a /etc/default/openmediavault >/dev/null"
ssh nas "sudo omv-salt deploy run watchdog systemd-journald"
ssh nas "grep -c '^OMV_WATCHDOG_MODULE_NAME=\"bcm2835_wdt\"$' /etc/default/openmediavault; grep -c '^OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE=\"500M\"$' /etc/default/openmediavault; grep -v '^#' /etc/modules-load.d/openmediavault-watchdog.conf; grep -h '^SystemMaxUse' /etc/systemd/journald.conf.d/*.conf; grep -h '^RuntimeWatchdogSec' /etc/systemd/system.conf.d/*.conf"
```

Fuente: `/srv/salt/omv/deploy/watchdog/default.sls` (`OMV_WATCHDOG_MODULE_NAME`, por defecto
`softdog`; en arm64 limita `RuntimeWatchdogSec` a 15 s) y la lista de variables de OMV en el NAS
(`OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE`). La línea `printf` no lleva `$` ni `#!`.

Esperado: deploy con `Failed: 0`; `1`, `1`, `bcm2835_wdt`, `SystemMaxUse=500M` (una sola línea),
`RuntimeWatchdogSec=14s`.

Si falla: si algún `grep -c` da `2`, borra la línea duplicada con
`ssh nas "sudo sed -i '<n>d' /etc/default/openmediavault"` tras localizarla con `grep -n`. Si el
state `systemd-journald` no existe, busca el nombre con `ssh nas "ls /srv/salt/omv/deploy"` y anótalo.

### Paso 5: Drop-in de `RebootWatchdogSec`

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §3 |

Comando:

```bash
cat state/config/etc/systemd/system.conf.d/60-nas-watchdog.conf | ssh nas "sudo tee /etc/systemd/system.conf.d/60-nas-watchdog.conf >/dev/null"
ssh nas "sudo systemctl daemon-reexec && systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec && grep -rh -c '^RebootWatchdogSec' /etc/systemd/system.conf.d/ | paste -sd+ | bc"
```

Fuente: `man systemd-system.conf` (`RuntimeWatchdogSec`, `RebootWatchdogSec`; `systemctl
daemon-reexec` vuelve a leer `system.conf`).

Esperado: `RuntimeWatchdogUSec=14s`, `RebootWatchdogUSec=2min`; `1` (una sola definición de
`RebootWatchdogSec`).

Si falla: si `bc` no existe, cuenta con `grep -rh '^RebootWatchdogSec' /etc/systemd/system.conf.d/ | wc -l`.

### Paso 6: Vigilancia de `snapraid.content` con aviso por correo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (desde el PC) y Móvil |
| **HLD** | §5, §9, ADR-015 |

Comando:

```bash
cat state/config/usr/local/sbin/snapraid-content-vigila | ssh nas "sudo tee /usr/local/sbin/snapraid-content-vigila >/dev/null && sudo chmod 755 /usr/local/sbin/snapraid-content-vigila"
cat state/config/etc/systemd/system/snapraid-content-vigila.service | ssh nas "sudo tee /etc/systemd/system/snapraid-content-vigila.service >/dev/null"
cat state/config/etc/systemd/system/snapraid-content-vigila.timer | ssh nas "sudo tee /etc/systemd/system/snapraid-content-vigila.timer >/dev/null"
ssh nas "sudo systemctl daemon-reload && sudo systemctl enable --now snapraid-content-vigila.timer && sudo /usr/local/sbin/snapraid-content-vigila --prueba && systemctl list-timers --no-legend snapraid-content-vigila.timer && journalctl -t snapraid-content-vigila -n 1 --no-pager"
```

Fuente: `man systemd.timer` (`OnCalendar`, `Persistent`), `man mail` (bsd-mailx 8.1.2 instalado),
correo de OMV del RBK 04.

Esperado: (la recepción del correo la confirma el usuario) el temporizador aparece con la próxima ejecución a las 12:00; `AVISO enviado: ultimo=…`
en el journal; el usuario recibe en minutos el correo «[NAS] SnapRAID sin sync desde hace N h»
(de prueba). Una ejecución normal sin `--prueba` registra `OK: ultimo=…` si el content tiene
menos de 48 h.

Si falla: si no llega el correo, `ssh nas "sudo journalctl -u postfix -n 20 --no-pager"` y revisa la
configuración de correo de OMV (RBK 04); el script no se modifica.

> Paso 7: **una orden cada vez**. No pegues nada más en esa terminal hasta ver el prompt del PC.

### Paso 7: Reinicio de verificación

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando (una sola orden de una línea):

```bash
ssh nas "sudo reboot"
```

Esperado: la sesión se corta (normal); en menos de 10 min `ssh -o BatchMode=yes nas hostname`
responde `nas`. **Nunca desenchufes mientras el LED verde parpadee.**

Si falla: si a los 10 min no responde y el LED verde está quieto, «Recuperación sin pantalla». Si
el LED parpadea, espera.

### Paso 8: Comprobar journal persistente y watchdog tras el reinicio

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, §11 |

Comando:

```bash
ssh nas "journalctl --list-boots | tail -n 3; findmnt -n -o FSTYPE /var/log || echo 'ssd-directo'; journalctl --header | grep -m1 'File path'; journalctl --disk-usage; journalctl -b -o short-monotonic | grep -E -c 'softdog'; journalctl -b | grep -m1 'hardware watchdog'; lsmod | grep -c bcm2835_wdt; systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec; systemctl --failed --no-legend | wc -l"
```

Esperado: `--list-boots` muestra el arranque anterior (el del paso 2/7) **y** el actual;
`ssd-directo`; ruta del journal en `/var/log/journal/…`; uso ≤ 500M; `0` líneas con `softdog`;
`Using hardware watchdog 'Broadcom BCM2835 Watchdog timer'`; `1` (o `0` si el driver está
compilado en el kernel: válido si la línea anterior aparece); `RuntimeWatchdogUSec=14s`,
`RebootWatchdogUSec=2min`; `0` servicios fallidos.

Si falla: si solo hay un arranque en la lista, `/var/log` sigue en overlay: revisa el paso 3 y
`sudo omv-writecache status`. Si hay servicios fallidos, anótalos en el OPS como incidencia.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Journal sobrevive reinicios | `ssh nas "journalctl --list-boots \| wc -l"` | ≥ 2 y crece en cada reinicio |
| `/var/log` en el SSD | `ssh nas "findmnt -n /var/log \|\| echo ssd-directo"` | ssd-directo |
| Sin softdog | `ssh nas "journalctl -b \| grep -c softdog"` | 0 |
| Watchdog hardware | `ssh nas "systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec"` | 14s y 2min |
| Temporizador de aviso | `ssh nas "systemctl is-enabled snapraid-content-vigila.timer"` | enabled |
| Correo de prueba | bandeja de entrada | recibido |
| SSH solo con clave | `ssh -o BatchMode=yes nas hostname` | nas |

## Recuperación sin pantalla

Usar si la Pi no vuelve a la red 10 minutos después del paso 2 o 7 y el LED verde está quieto.
Lo hace el usuario en el PC; el agente da los comandos.

1. Comprobar que el LED verde no parpadea; desenchufar los 12 V, sacar el SSD y conectarlo al PC.
2. Windows: abrir la unidad `bootfs` (p. ej. `E:`). Si pide formatear: `chkdsk E: /f` en consola de
   administrador tras confirmar la letra en el Explorador; nunca formatear.
3. Comparar `config.txt`: `Get-FileHash E:\config.txt` frente a
   `sha256sum state/config/boot/firmware/config.txt`; si difieren, restaurar desde el repo.
4. Leer el rootfs (PowerShell como administrador): `wsl --mount \\.\PHYSICALDRIVEn --partition 2`
   (`n` con `Get-Disk` por modelo y tamaño); como root con `wsl.exe -u root` bajo
   `/mnt/wsl/PHYSICALDRIVEnp2`. **Con este RBK aplicado, los logs del arranque fallido ya están en
   el SSD:** `journalctl -D /mnt/wsl/PHYSICALDRIVEnp2/var/log/journal --list-boots` y
   `journalctl -D … -b -1 -p warning`.
5. Para deshacer este RBK sin red: borrar `/mnt/wsl/PHYSICALDRIVEnp2/etc/systemd/system.conf.d/60-nas-watchdog.conf`
   (el drop-in de OMV queda como antes); el resto no impide arrancar.
6. Desmontar: `wsl.exe -u root umount /mnt/wsl/PHYSICALDRIVEnp2` y `sync`; luego
   `wsl --unmount \\.\PHYSICALDRIVEn`. Desconectar solo tras el desmontaje.
7. Si nada de lo anterior funciona: restaurar la imagen del paso 2 (lo hace el usuario; destructivo
   sobre el SSD, identificar el SSD por modelo y serie con `lsblk -o NAME,SIZE,MODEL,SERIAL`).

Esperado: la Pi vuelve a responder a `ssh nas`.

## Vuelta atrás

- Writecache: reenviar la configuración anterior (con `/var/log = flush` y
  `"journald_storage":"auto"`) con la misma orden del paso 3 y `omv-salt deploy run writecache`.
- Variables de OMV: borrar las dos líneas del paso 4 de `/etc/default/openmediavault` con
  `sudo sed -i '/^OMV_WATCHDOG_MODULE_NAME=/d;/^OMV_SYSTEMD_JOURNALD_SYSTEMMAXUSE=/d'` y
  `omv-salt deploy run watchdog systemd-journald`.
- Drop-in: `sudo rm /etc/systemd/system.conf.d/60-nas-watchdog.conf && sudo systemctl daemon-reexec`.
- Aviso: `sudo systemctl disable --now snapraid-content-vigila.timer` y borrar el script y las
  unidades.
- Caso extremo: imagen del SSD del paso 2.

## Evidencias

- Salida del paso 1 (estado previo) y del paso 8 (`--list-boots` con dos arranques) en el OPS.
- Ficheros versionados en `state/config/` (lista de prerrequisitos); tras ejecutar,
  `/operator-plugin:snapshot-config`.
- Asunto y hora del correo de prueba en el OPS (sin direcciones).
- `state/applied.yaml`: fase 16 aplicada.

## Preguntas abiertas para el HLD (update-hld)

1. **ADR nuevo «Resiliencia y observabilidad»**: el HLD v3 no recoge writecache (ADR-002 solo
   habla de SSD frente a SD) ni el watchdog. Hace falta un ADR que registre: `/var/log` fuera de
   writecache con journal persistente de 500M en el SSD (alternativa: mantener RAM y perder logs),
   watchdog `bcm2835_wdt` 14 s / 2 min por variables de OMV, y aviso de sync a 48 h.
2. **Cuelgue con kernel vivo** (caso del 2026-10-21): el watchdog de systemd no lo detecta. ¿Se
   añade un vigilante de servicios (p. ej. `WatchdogSec` en servicios críticos, o comprobación
   periódica de `sshd`/Samba que reinicie) o un aviso externo (otro equipo de la tailnet que
   compruebe el puerto 22)? Decisión del arquitecto antes de un RBK 16 v3.1.
3. ¿El umbral de 48 h y la hora 12:00 encajan con NRD §5 (RPO 24 h)? Con 48 h, un fallo del sync se
   avisa como tarde a mediodía del segundo día.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 3.0 | 2026-10-28 | Runbook Agent | Creación tras el cuelgue del 2026-10-21 al 28: journal persistente (writecache), watchdog bcm2835_wdt y aviso de sync a 48 h |
| 3.0 | 2026-10-28 | Runbook Agent | Estado cambiado a Aprobado |
