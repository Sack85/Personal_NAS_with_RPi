# RBK 03 — Primer arranque y HAT

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 03 — Primer arranque y HAT |
| **Versión** | 1.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 2 h |

## Objetivo

Añadir las cuatro líneas del HAT a `config.txt`, arrancar la Pi desde el XG5 sin discos,
fijar la IP con una reserva DHCP, crear el alias `ssh nas` en el PC, actualizar el sistema,
comprobar el JMB585 a PCIe Gen 3 y, al final, conectar los tres discos (HLD §3, §4).

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

Abre la partición `bootfs` del XG5 en el PC, edita `config.txt` con un editor de texto plano, guarda y expulsa el disco.

Esperado: las cuatro líneas al final de `config.txt`, después de la última línea `[all]`.

Si falla: si `config.txt` no termina en una sección `[all]`, añade `[all]` antes de las cuatro líneas.

### Paso 2: Arrancar sin discos y alimentado por el HAT

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2, §3 |

Esperado: XG5 en un USB 3 (azul), Ethernet conectado, discos sin conectar, solo el conector de 12 V del HAT. LED verde de actividad y el equipo `nas` en la lista de clientes del router en 2 minutos.

Si falla: si no arranca, conecta una pantalla HDMI y mira el gestor de arranque. Nunca conectes a la vez el USB-C de la Pi y el 12 V.

### Paso 3: Reserva DHCP para nas en el router

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Router |
| **HLD** | §4 |

Crea también ahora o en el proyecto de la Pi 4 la reserva para la futura Pi 4 de descargas (HLD §4).

Esperado: reserva DHCP para la MAC de `nas` con una IP fija de la LAN (por ejemplo 192.168.1.200). Anota la IP en el OPS.

Si falla: si el router no permite reservas, anótalo como incidencia y pásalo al arquitecto (pregunta abierta del modelo del router).

### Paso 4: Primera conexión SSH y alias nas en el PC

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3, §8 |

Comando:

```bash
ssh-keygen -t ed25519            # solo si el PC no tiene clave
ssh-copy-id tu_usuario@nas.local
# En ~/.ssh/config del PC:
#   Host nas
#     HostName <IP reservada del paso 3>
#     User tu_usuario
ssh nas hostname
```

Esperado: `ssh nas hostname` responde `nas` sin pedir contraseña.

Si falla: si `nas.local` no resuelve, usa la IP reservada. Si pide contraseña, repite `ssh-copy-id`.

### Paso 5: Comprobar sistema, zona horaria y config.txt

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

Si falla: si la zona horaria no es la de casa, se corrige en el paso 6 con `sudo timedatectl set-timezone <Zona>`; si faltan líneas en `config.txt`, apaga y vuelve al paso 1.

### Paso 6: Actualizar el sistema y reiniciar

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

### Paso 7: Comprobar el JMB585 a PCIe Gen 3

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

### Paso 8: Leer la configuración de la EEPROM

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

Esperado: versión del gestor de arranque y `BOOT_ORDER`. Anota ambos en el OPS.

Si falla: si el comando no existe, instala `rpi-eeprom` (Cambio) y repite.

### Paso 9: Orden de arranque con USB primero y PSU_MAX_CURRENT

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comprobación previa:

```bash
ssh nas 'vcgencmd bootloader_version; rpi-eeprom-config'
```

Si ya está `BOOT_ORDER=0xf14` y `PSU_MAX_CURRENT=5000`, salta este paso. Fuente de `BOOT_ORDER`: documentación oficial de Raspberry Pi (Raspberry Pi bootloader configuration).

Comando:

```bash
sudo rpi-eeprom-config --edit
# en el editor: BOOT_ORDER=0xf14  y  PSU_MAX_CURRENT=5000; guardar
sudo reboot
```

Esperado: tras el reinicio, `rpi-eeprom-config` muestra `BOOT_ORDER=0xf14` y `PSU_MAX_CURRENT=5000`; la Pi arranca desde el XG5 sin aviso de alimentación.

Si falla: si la Pi no arranca tras el cambio, recupera la EEPROM con Raspberry Pi Imager → Misc utility images → Bootloader (Pi 5) → USB Boot en una tarjeta SD y arranca con ella.

### Paso 10: Conectar los tres discos

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

### Paso 11: Comprobar los cuatro dispositivos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §2, §5 |

Comando:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

Esperado: cuatro dispositivos: el XG5 (~512 GB, `usb`) y tres `sata` de ~1 TB cuyos números de serie coinciden con la tabla del RBK 01. Anota la letra actual de cada uno en el OPS (puede cambiar en cada arranque).

Si falla: si falta un disco, apaga, revisa la bahía y el FFC, y repite; si sigue faltando, `ssh nas 'sudo dmesg | grep -i ata'` y para.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| JMB585 a Gen 3 | `ssh nas 'sudo lspci -vv -d 197b: \| grep LnkSta'` | Speed 8GT/s |
| Sin throttling | `ssh nas vcgencmd get_throttled` | throttled=0x0 |
| Discos SATA | `ssh nas 'lsblk -d -o NAME,TRAN \| grep -c sata'` | 3 |
| Alias SSH | `ssh nas hostname` | nas |

## Vuelta atrás

Las líneas de `config.txt` se quitan editando el fichero (con el XG5 en el PC si no arranca).
La EEPROM se recupera con la imagen de recuperación del gestor de arranque de Raspberry Pi Imager
en una tarjeta SD. La reserva DHCP se borra en el router.

## Evidencias

- Salida de `lspci` y `LnkSta` en el OPS
- `BOOT_ORDER` antes y después en el OPS
- Salida de `lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN` en el OPS
- Copia de `config.txt` en `state/config/` (`/operator-plugin:snapshot-config`)

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Modelo del router? Decide cómo se hace la reserva DHCP (pregunta abierta del HLD) | Persona 1 | 2026-10-31 |
| El orden de arranque por defecto de la Pi 5 ya incluye USB (guía §3.2); el HLD pide USB primero. ¿Se mantiene el cambio de EEPROM o se deja el valor por defecto? | Persona 1 | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 1.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
