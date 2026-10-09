# RBK 03 — Primer arranque y HAT

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 03 — Primer arranque y HAT |
| **Versión** | 2.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 2 h |

## Objetivo

Añadir las cuatro líneas del HAT a `config.txt`, arrancar la Pi desde el XG5 sin discos,
fijar la IP 192.168.1.11 con una reserva DHCP, crear el alias `ssh nas` en el PC, dar sudo sin
contraseña a `nas`, desactivar el SSH por contraseña, actualizar el sistema,
comprobar el JMB585 a PCIe Gen 3 y, al final, conectar los tres discos (HLD v2 §3, §4,
ADR-019 a ADR-022).

## Prerrequisitos

- [ ] RBK 02 completado: XG5 grabado y aún conectado al PC
- [ ] Acceso de administración al router (el usuario inicia sesión)

## Pasos

### Paso 1: Añadir las líneas del HAT a config.txt

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3 |

Comando:

```bash
dtparam=pciex1
dtparam=pciex1_gen=3
dtoverlay=pcie-32bit-dma-pi5
usb_max_current_enable=1
```

Abre la partición `bootfs` del XG5 en el PC, edita `config.txt` con un editor de texto plano, **guarda** y expulsa el disco. En Notepad++ la pestaña muestra `*` mientras el fichero no está guardado: no expulses hasta que desaparezca (OPS-2026-10-09-rbk01-03).

Esperado: las cuatro líneas al final de `config.txt`, después de la última línea `[all]`.

Si falla: si `config.txt` no termina en una sección `[all]`, añade `[all]` antes de las cuatro líneas. Si al reabrirlo faltan las líneas, no se guardó: repite y guarda.

### Paso 2: Arrancar sin discos y alimentado por el HAT

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2, §3 |

El XG5 va en un **USB-A azul (USB 3)**, nunca en el USB-C de la Pi: el USB-C es solo de alimentación y desde él no arranca (OPS-2026-10-09-rbk01-03).

Esperado: XG5 en un USB-A azul, Ethernet conectado, discos sin conectar, solo el conector de 12 V del HAT. LED verde de actividad y el equipo `nas` en la lista de clientes del router en 2 minutos.

Si falla: si no arranca, comprueba primero que el XG5 está en un USB-A azul y no en el USB-C; después conecta una pantalla HDMI y mira el gestor de arranque. Nunca conectes a la vez el USB-C de la Pi y el 12 V.

### Paso 3: Reserva DHCP para nas en el router

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Router |
| **HLD** | §4 |

Crea también ahora o en el proyecto de la Pi 4 la reserva para la futura Pi 4 de descargas (HLD §4).

Esperado: reserva DHCP de **192.168.1.11** para la MAC `d8:3a:dd:a4:c5:c3` (equipo `nas`; HLD v2 §4, ADR-019). Es la IP que ya dio la box; no se usa la .200 de la guía. Anota la reserva en el OPS.

Si falla: si la MAC de la lista de clientes no es `d8:3a:dd:a4:c5:c3`, para y anótalo (la Pi o el adaptador cambió). Si el router no permite reservas, anótalo como incidencia y pásalo al arquitecto (pregunta abierta del modelo del router).

### Paso 4: Primera conexión SSH y alias nas en el PC

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3, §8 |

Comando:

```bash
ls ~/.ssh/id_ed25519_nas || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_nas   # solo si no existe
ssh-copy-id -i ~/.ssh/id_ed25519_nas.pub nas@192.168.1.11
grep -c '^Host nas$' ~/.ssh/config     # debe dar 0 antes de añadir el bloque
```

Si el `grep` da 0, añade al final de `~/.ssh/config` del PC este bloque, tal cual (no hay nada que sustituir):

```
Host nas
  HostName 192.168.1.11
  User nas
  IdentityFile ~/.ssh/id_ed25519_nas
```

Si da 1 o más, no lo añadas: edita el bloque existente para que quede igual que este.

```bash
grep -c '^Host nas$' ~/.ssh/config     # debe dar 1
ssh nas hostname
```

Esperado: `grep -c '^Host nas$'` = 1 (un solo bloque, sin `<IP>` literal) y `ssh nas hostname` responde `nas` sin pedir contraseña.

Si falla: si pide contraseña, repite `ssh-copy-id` con `-i ~/.ssh/id_ed25519_nas.pub`. Si hay dos bloques `Host nas` o queda un `<IP>` literal, déjalo en un único bloque como el de arriba (OPS-2026-10-09-rbk01-03).

### Paso 5: Sudo sin contraseña para nas

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §8, ADR-020 |

Comprobación previa:

```bash
ssh nas 'sudo -n true && echo ya-sin-contraseña'
```

Si responde `ya-sin-contraseña`, salta este paso.

Comando (lo teclea el usuario; `sudo` pedirá la contraseña de `nas` del gestor de contraseñas):

```bash
ssh -t nas 'echo "nas ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/010-nas-nopasswd && sudo chmod 0440 /etc/sudoers.d/010-nas-nopasswd && sudo visudo -c'
```

Esperado: `visudo -c` termina con `/etc/sudoers.d/010-nas-nopasswd: parsed OK` y `ssh nas 'sudo -n true && echo ok'` responde `ok`.

Si falla: si `visudo -c` da error de sintaxis, borra el fichero en la misma sesión (`sudo rm /etc/sudoers.d/010-nas-nopasswd`) antes de cerrarla y repite; con un sudoers roto no se puede usar `sudo`.

### Paso 6: Desactivar el SSH por contraseña

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §8, ADR-020 |

Comprobación previa: el paso 4 terminó con `ssh nas hostname` = `nas` sin pedir contraseña. Si no, **no hagas este paso** (te quedarías fuera).

Comando:

```bash
ssh nas 'echo "PasswordAuthentication no" | sudo tee /etc/ssh/sshd_config.d/10-sin-contrasena.conf && sudo sshd -t && sudo systemctl reload ssh'
ssh nas hostname
ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password nas@192.168.1.11 true
```

Esperado: `sshd -t` sin salida; `ssh nas hostname` sigue respondiendo `nas`; el intento por contraseña termina en `Permission denied (publickey)`.

Si falla: si `ssh nas` deja de funcionar, conecta teclado y pantalla a la Pi, borra `/etc/ssh/sshd_config.d/10-sin-contrasena.conf` y `sudo systemctl reload ssh`; vuelve al paso 4. Mantén abierta una sesión SSH durante el paso.

### Paso 7: Comprobar sistema, zona horaria y config.txt

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas 'grep PRETTY_NAME /etc/os-release; uname -m; timedatectl; tail -n 6 /boot/firmware/config.txt'
```

Esperado: `Debian GNU/Linux 13 (trixie)`, `aarch64`, la zona horaria de casa en `timedatectl` (todas las tareas del HLD van en hora local) y las cuatro líneas al final de `config.txt`.

Si falla: si la zona horaria no es la de casa, se corrige en el paso 8 con `sudo timedatectl set-timezone <Zona>`; si faltan líneas en `config.txt`, apaga y vuelve al paso 1.

### Paso 8: Actualizar el sistema y reiniciar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3, §10 |

Comando:

```bash
ssh nas 'sudo apt update && sudo apt full-upgrade -y && sudo reboot'
```

Esperado: `apt` termina sin errores; la Pi vuelve a responder a `ssh nas` en 2 minutos.

Si falla: si `apt` falla por red, comprueba `ping -c 3 deb.debian.org` y repite.

### Paso 9: Comprobar el JMB585 a PCIe Gen 3

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas 'lspci | grep -i jmicron; sudo lspci -vv -d 197b: | grep LnkSta; vcgencmd get_throttled'
```

Esperado: una línea `JMicron Technology Corp. JMB58x` y `LnkSta: Speed 8GT/s`. `get_throttled` = `throttled=0x0`.

Si falla: si no aparece el JMB585, apaga, revisa el FFC (cara negra hacia fuera, pestillos) y vuelve a arrancar; si va a 5GT/s, revisa `dtparam=pciex1_gen=3` en `config.txt`.

### Paso 10: Leer la configuración de la EEPROM

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas 'vcgencmd bootloader_version; rpi-eeprom-config'
```

Esperado: versión del gestor de arranque y `BOOT_ORDER=0xf41` (valor por defecto; arranca bien por USB sin SD, HLD v2 ADR-021). Anota ambos en el OPS. `0xf41` es válido: el paso 11 es opcional.

Si falla: si el comando no existe, instala `rpi-eeprom` (Cambio) y repite.

### Paso 11: (Opcional) Orden de arranque con USB primero y PSU_MAX_CURRENT

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

**Opcional** (HLD v2 ADR-021): con `BOOT_ORDER=0xf41` y `usb_max_current_enable=1` la Pi ya
arranca desde el XG5. Por defecto este paso se salta y se anota «omitido (ADR-021)» en el OPS.

Comprobación previa:

```bash
ssh nas 'vcgencmd bootloader_version; rpi-eeprom-config'
```

Si ya está `BOOT_ORDER=0xf14` y `PSU_MAX_CURRENT=5000`, salta este paso. Fuente de `BOOT_ORDER`: documentación oficial de Raspberry Pi (Raspberry Pi bootloader configuration).

No uses `rpi-eeprom-config --apply` ni `--edit` arrancando desde USB: no se aplica porque el
SPI de la EEPROM no está disponible (`nospi10`, OPS-2026-10-09-rbk01-03). Método: tarjeta SD.

Comando:

```
En el PC, Raspberry Pi Imager → Dispositivo Raspberry Pi 5 → Sistema: Misc utility images →
Bootloader (Pi 5 family) → USB Boot → Almacenamiento: una tarjeta SD vacía → Escribir.
Apaga la Pi (ssh nas 'sudo poweroff'), inserta la SD, enciende y espera a que el LED verde
parpadee de forma continua (EEPROM escrita). Apaga, retira la SD y vuelve a encender.
```

Esperado: tras el arranque, `ssh nas 'rpi-eeprom-config'` muestra el `BOOT_ORDER` con USB primero; la Pi arranca desde el XG5. Si se omite el paso: `BOOT_ORDER=0xf41` sin cambios y `/boot/firmware/pieeprom.upd` (si quedó del intento anterior) borrado o anotado como pendiente.

Si falla: si la Pi no arranca tras el cambio, repite la SD de Imager → Bootloader (Pi 5 family) → USB Boot; si sigue sin arrancar, arranca con la imagen SD Card Boot y anótalo como incidencia.

### Paso 12: Conectar los tres discos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2 (bahías) |

Comando:

```bash
ssh nas 'sudo poweroff'
```

Espera a que se apague el LED verde, desenchufa el 12 V, conecta los discos y vuelve a enchufar.

Esperado: los tres discos conectados en las bahías 1, 3 y 4 según el RBK 01 y la Pi arrancada de nuevo.

Si falla: si la Pi no arranca con los discos, desconéctalos, arranca y revisa el adaptador de 12 V / 5 A.

### Paso 13: Comprobar los cuatro dispositivos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §2, §5 |

Comando:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN; ls -l /dev/disk/by-id/ | grep -v -- -part'
```

Esperado: cuatro dispositivos: el XG5 (~512 GB, `usb`) y tres `sata` de 1000204886016 bytes (ya verificado, HLD v2 §5) cuyos números de serie coinciden con la tabla del RBK 01. Anota en el OPS la ruta `/dev/disk/by-id/ata-…` de cada uno, no la letra `sdX`: las letras cambian entre arranques (ADR-022).

Si falla: si falta un disco, apaga, revisa la bahía y el FFC, y repite; si sigue faltando, `ssh nas 'sudo dmesg | grep -i ata'` y para.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| JMB585 a Gen 3 | `ssh nas 'sudo lspci -vv -d 197b: \| grep LnkSta'` | Speed 8GT/s |
| Sin throttling | `ssh nas vcgencmd get_throttled` | throttled=0x0 |
| Discos SATA | `ssh nas 'lsblk -d -o NAME,TRAN \| grep -c sata'` | 3 |
| Alias SSH | `ssh nas hostname` | nas |
| Sudo sin contraseña | `ssh nas sudo -n true && echo ok` | ok |
| SSH sin contraseña | `ssh -o PubkeyAuthentication=no -o PreferredAuthentications=password nas@192.168.1.11` | Permission denied (publickey) |

## Vuelta atrás

Las líneas de `config.txt` se quitan editando el fichero (con el XG5 en el PC si no arranca).
Si se desactivó el SSH por contraseña, se revierte borrando
`/etc/ssh/sshd_config.d/10-sin-contrasena.conf`; el sudo sin contraseña, borrando
`/etc/sudoers.d/010-nas-nopasswd`. La EEPROM se recupera con la imagen de recuperación del gestor de arranque de Raspberry Pi Imager
en una tarjeta SD. La reserva DHCP se borra en el router.

## Evidencias

- Salida de `lspci` y `LnkSta` en el OPS
- `BOOT_ORDER` (0xf41, o el nuevo si se hizo el paso opcional) en el OPS
- `grep -c '^Host nas$' ~/.ssh/config` = 1 y prueba de SSH por contraseña rechazada en el OPS
- `sudo visudo -c` correcto en el OPS
- Salida de `lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN` en el OPS
- Copia de `config.txt` en `state/config/` (`/operator-plugin:snapshot-config`)

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Modelo del router? La reserva DHCP ya está decidida (ADR-019); queda abierto si permite DNS local (pregunta abierta del HLD v2) | Persona 1 | 2026-10-31 |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 1.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: HLD v2 (2.0, Aprobado) y OPS-2026-10-09-rbk01-03. Paso 1: guardar `config.txt`. Paso 2: USB-A azul, nunca USB-C. Paso 3: IP 192.168.1.11 / MAC d8:3a:dd:a4:c5:c3 (ADR-019). Paso 4: bloque `Host nas` completo con IdentityFile y control de duplicados. Nuevos pasos 5 (sudo NOPASSWD, ADR-020) y 6 (SSH sin contraseña). Antiguos 5-11 pasan a 7-13. Paso 11 EEPROM opcional, 0xf41 válido, método SD Bootloader USB Boot, sin `--apply` desde USB (ADR-021). Paso 13 con `/dev/disk/by-id` (ADR-022) |
| 2.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
