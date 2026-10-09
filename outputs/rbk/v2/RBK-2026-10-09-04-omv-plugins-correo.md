# RBK 04 — OpenMediaVault 8, plugins y correo

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 04 — OpenMediaVault 8, plugins y correo |
| **Versión** | 2.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 2 h |

## Objetivo

Instalar OpenMediaVault 8 con los scripts de omv-extras, cambiar la contraseña de `admin`, mover
la web al puerto 8000, instalar los plugins snapraid, mergerfs, sharerootfs y compose, y dejar
los avisos por correo de Gmail probados (HLD v2 2.1 §3, §6, §10). El NAS es `nas` en 192.168.1.11
(reserva DHCP, ADR-019); el agente entra como usuario `nas` con clave ed25519 y ejecuta con `sudo`
sin contraseña (ADR-020): el guard SSH pide confirmación de cada cambio. SSH sigue solo con clave
después de instalar OMV (HLD §8): OMV regenera `sshd_config` y no debe reactivar
`PasswordAuthentication`.

## Prerrequisitos

- [ ] HLD v2 2.1 aprobado
- [ ] RBK 03 completado: `ssh nas` funciona (usuario `nas`, 192.168.1.11, solo clave) y los tres discos aparecen
- [ ] `ssh nas 'sudo -n true && echo ok'` devuelve `ok` (sudo sin contraseña, ADR-020)
- [ ] Acceso de emergencia sin SSH disponible (pantalla y teclado) por si OMV cierra el SSH. Si no hay pantalla, la sección «Recuperación sin pantalla» sustituye a este acceso (requiere lector USB-SATA para el SSD y un PC con Windows + WSL)
- [ ] Copia actual de `config.txt` en `state/config/boot/firmware/config.txt` (la usa la recuperación sin pantalla)
- [ ] Contraseña de aplicación de Gmail creada y guardada en el gestor de contraseñas
- [ ] Contraseña nueva de `admin` de OMV creada en el gestor de contraseñas

## Pasos

### Paso 0: Copia de seguridad del SSD de sistema antes de instalar OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH y PC |
| **HLD** | §3 |

Comprobación previa: `state/config/boot/firmware/config.txt` existe en el repo (si no, `/operator-plugin:snapshot-config` antes de apagar).

Comando (apagado limpio; nunca desenchufar sin él):

```bash
ssh nas 'sudo poweroff'
```

Después, con el LED verde apagado: desenchufar los 12 V, sacar el SSD y conectarlo al PC. Hacer una imagen de sus particiones y guardarla en `D:`:
- Windows: Win32 Disk Imager con «Read Only Allocated Partitions».
- O WSL (PowerShell como administrador): `wsl --mount \\.\PHYSICALDRIVEn --bare`, identificar el disco en WSL con `lsblk -o NAME,SIZE,MODEL,SERIAL` y leerlo con `sudo dd if=/dev/sdX of=/mnt/d/nas-ssd-AAAA-MM-DD.img bs=4M status=progress conv=sparse` (solo lectura del SSD; `of=` es un fichero en D:); después `wsl --unmount \\.\PHYSICALDRIVEn`.

Esperado: imagen en `D:` con el tamaño de las particiones usadas; SSD de vuelta en la Pi y `ssh nas` responde tras encenderla.

Si falla: si la imagen falla o `D:` no tiene espacio, no sigas con el paso 1; libera espacio y repite. Si WSL no ve el disco, usa Win32 Disk Imager.

> Ejecutar los pasos 1 y 2 **un comando cada vez**. Nunca pegues un bloque de varias líneas tras `ssh nas`: si la sesión se corta (reinicio), las líneas restantes se ejecutan en el PC (OPS-2026-10-09-rbk04, incidencia 1).

### Paso 1: Ejecutar el script preinstall de omv-extras

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando (dos órdenes separadas, desde el PC; lanza la segunda solo cuando termine la primera):

```bash
ssh -t nas 'wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/preinstall | sudo bash'
```

```bash
ssh nas 'sudo reboot'
```

Fuente: guía §4.1 (scripts oficiales de omv-extras); `man ssh` (`-t` reserva terminal). Lo ejecuta el usuario porque la conexión se corta. Nunca pegues las dos órdenes juntas.

Esperado: el script termina sin errores; la Pi se reinicia y vuelve a responder a `ssh nas` (espera hasta 10 min; no desenchufes mientras el LED verde parpadee).

Si falla: si falla con «unsupported OS», comprueba que no hay repositorios de Ubuntu ni PPA en `/etc/apt/sources.list.d/` y repite.

### Paso 2: Ejecutar el script install de omv-extras

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh -t nas 'wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/install | sudo bash'
```

Una sola orden de una línea. Si la sesión se corta, no escribas nada más en esa terminal hasta comprobar que el prompt es el del PC.

Esperado: el script termina y reinicia solo; la sesión SSH se corta durante la instalación (normal). La IP no cambia gracias a la reserva DHCP. Espera hasta 10 minutos a que `ssh nas` vuelva a responder; **nunca desenchufes mientras el LED verde parpadee** (escrituras en curso: riesgo de corromper la partición FAT `bootfs`, OPS-2026-10-09-rbk04 incidencia 2).

Si falla: si a los 10 minutos no responde y el LED verde está fijo o apagado, ve a «Recuperación sin pantalla» (o conecta una pantalla si la hay); el script es repetible una vez recuperado el acceso.

### Paso 3: Comprobar que OMV está en marcha

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas 'systemctl status openmediavault-engined --no-pager | head -n 5; dpkg -l openmediavault | tail -n 1'
ssh nas 'ip -br link; systemctl --failed --no-legend | wc -l; sudo -n sshd -T | grep -i "^passwordauthentication"'
```

Esperado: `active (running)` y una versión 8.x de `openmediavault`. El propio `ssh nas` ha entrado con la clave (sin pedir contraseña). La interfaz cableada se llama `end0` (el netplan de OMV casa por MAC; normal). `systemctl --failed` = `0`. `passwordauthentication yes` es lo esperado aquí: OMV lo reactiva y se corrige en el paso 11.

Si falla: si no está activo, revisa `ssh nas 'sudo journalctl -u openmediavault-engined -n 50'` y para. Si `ssh nas` pide contraseña o es rechazado, para y ve al paso 11 desde la consola local. Si `systemctl --failed` muestra `systemd-networkd-wait-online.service` (espera a todas las interfaces), ejecuta el paso 3b.

### Paso 3b: Drop-in para systemd-networkd-wait-online (solo si falla)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4 |

Comprobación previa: `ssh nas 'systemctl --failed --no-legend'` lista `systemd-networkd-wait-online.service`.

Comando:

```bash
ssh nas 'sudo mkdir -p /etc/systemd/system/systemd-networkd-wait-online.service.d && printf "[Service]\nExecStart=\nExecStart=/usr/lib/systemd/systemd-networkd-wait-online --any --timeout=30\n" | sudo tee /etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf && sudo systemctl daemon-reload && sudo systemctl restart systemd-networkd-wait-online && systemctl --failed --no-legend | wc -l'
```

Fuente: `man systemd-networkd-wait-online` (`--any`, `--timeout`); OPS-2026-10-09-rbk04 (aplicado en la ejecución).

Esperado: `0` unidades fallidas.

Si falla: `ssh nas 'sudo journalctl -u systemd-networkd-wait-online -n 30'`; vuelta atrás: `sudo rm /etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf && sudo systemctl daemon-reload`.

### Paso 4: Primer acceso y contraseña de admin

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §8 |

Esperado: entras en `http://nas.local` con `admin` y la contraseña de fábrica, y la cambias por la del gestor de contraseñas (icono de usuario → Cambiar contraseña). Barra amarilla de cambios pendientes aplicada.

Si falla: si no carga la web, comprueba el paso 3.

### Paso 5: Mover la web de OMV al puerto 8000

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §4 |

Esperado: Sistema → Área de trabajo → Puerto 8000 guardado y aplicado; la web responde en `http://nas.local:8000` y ya no en el 80.

Si falla: si se pierde el acceso, `ssh nas 'sudo omv-firstaid'` permite volver a configurar el puerto de la web.

### Paso 6: Instalar los plugins

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §3, §5, §6 |

Esperado: en Sistema → Complementos instalados `openmediavault-snapraid`, `openmediavault-mergerfs`, `openmediavault-sharerootfs` y `openmediavault-compose`. `openmediavault-nut` solo en el RBK 12.

Si falla: si un plugin no aparece, Sistema → omv-extras → recargar la lista y repetir.

### Paso 7: Comprobar los plugins instalados

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas "dpkg -l 'openmediavault-*' | grep -E 'snapraid|mergerfs|sharerootfs|compose'"
```

Esperado: cuatro líneas `ii` (snapraid, mergerfs, sharerootfs, compose).

Si falla: si falta alguno, repite el paso 6.

### Paso 8: Configurar el correo de avisos con Gmail

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 (Otros), §8 |

Esperado: Sistema → Notificación → Configuración: smtp.gmail.com, puerto 587, STARTTLS, remitente y usuario = la dirección completa, contraseña = la contraseña de aplicación del gestor de contraseñas, destinatario = el correo de la familia. Guardado y aplicado.

Si falla: si el guardado falla, revisa que la verificación en dos pasos de Google está activa y que la contraseña de aplicación es la de 16 caracteres sin espacios.

### Paso 9: Enviar un correo de prueba y activar avisos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6, §10 |

Esperado: llega el correo de prueba; en Notificaciones activados SMART, sistema de ficheros y actualizaciones.

Si falla: si no llega en 5 minutos, revisa `ssh nas 'sudo journalctl -u postfix -n 30'` (el agente lo lee) y la carpeta de spam.

### Paso 10: Comprobar que no hay actualizaciones automáticas con reinicio

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §10 |

Comando:

```bash
ssh nas "apt-config dump | grep -i 'Automatic-Reboot' || echo sin-reinicio-automatico"
```

Esperado: ninguna línea `Unattended-Upgrade::Automatic-Reboot "true"`. Las actualizaciones se hacen a mano con un UPD aprobado.

Si falla: si aparece a `true`, anótalo como incidencia y prepara el cambio con `/maintainer-plugin:create-upd`.

### Paso 11: Servicio SSH de OMV solo con clave

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | v2 2.1 §8, ADR-020 |

Esperado: Servicios → SSH: activado, puerto 22, «Autenticación por contraseña» desmarcada, «Autenticación por clave pública» marcada, inicio de sesión de root no permitido. Guardado y cambios pendientes aplicados. OMV genera `sshd_config` desde su base de datos: esta pantalla es la que manda; no se edita `/etc/ssh/sshd_config` a mano porque OMV lo sobrescribe. Usuarios → Usuarios → `nas`: grupo `_ssh` presente (OMV solo deja entrar por SSH a root y a `_ssh`).

Si falla: si al aplicar se pierde `ssh nas`, entra por la consola local y añade `nas` al grupo `_ssh` desde Usuarios → Usuarios → Editar; vuelve a aplicar y repite el paso 12. No reactives la contraseña para salir del paso.

### Paso 12: Comprobar que sshd sigue solo con clave

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | v2 2.1 §8, ADR-020 |

Comando:

```bash
ssh -o BatchMode=yes nas 'hostname; id -nG; sudo -n sshd -T | grep -Ei "^(passwordauthentication|pubkeyauthentication|permitrootlogin|port) "'
ssh -o BatchMode=yes -o PubkeyAuthentication=no -o PreferredAuthentications=password nas true 2>&1 | tail -n 1
```

Fuente: `man sshd` (opción `-T`, configuración efectiva) y `man ssh_config` (`BatchMode`, `PreferredAuthentications`).

Esperado: `nas`; los grupos incluyen `_ssh` y `sudo`; `passwordauthentication no`, `pubkeyauthentication yes`, `permitrootlogin no`, `port 22`. La segunda orden termina en `Permission denied (publickey)`: el servidor ya no ofrece contraseña.

Si falla: si `passwordauthentication yes` o la segunda orden ofrece `password`, repite el paso 11 y vuelve a comprobar; si sigue, anota la incidencia en el OPS y para (HLD §8).

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| OMV en marcha | `ssh nas systemctl is-active openmediavault-engined` | active |
| Web en 8000 | `curl -s -o /dev/null -w '%{http_code}' http://nas.local:8000` | 200 |
| SSH solo con clave | `ssh nas "sudo sshd -T \| grep -Ei '^(passwordauthentication\|pubkeyauthentication)'"` | `passwordauthentication no`, `pubkeyauthentication yes` |
| `ssh nas` | `ssh -o BatchMode=yes nas hostname` | nas |
| Puerto 80 libre | `ssh nas "sudo ss -ltnp \| grep -c ':80 '"` | 0 |
| Correo | `bandeja de entrada` | correo de prueba recibido |

## Recuperación sin pantalla

Usar si la Pi no vuelve a la red 10 minutos después de un reinicio (sin `ssh nas`, sin luces de red) y no hay pantalla. Origen: OPS-2026-10-09-rbk04, incidencia 2. Lo hace el usuario en el PC; el agente da los comandos.

1. Comprobar que el LED verde no parpadea; desenchufar los 12 V, sacar el SSD y conectarlo al PC.
2. Windows: abrir la unidad `bootfs` (p. ej. `E:`). Si `config.txt` no se puede leer o la unidad pide formatear: `chkdsk E: /f` en una consola de administrador (confirmar antes la letra en el Explorador; nunca formatear).
3. Restaurar `config.txt` desde `state/config/boot/firmware/config.txt` y comparar hash: `Get-FileHash E:\config.txt` frente a `sha256sum state/config/boot/firmware/config.txt`. Esperado: hashes iguales.
4. Si `bootfs` está sano y la Pi sigue sin red, leer el rootfs (PowerShell como administrador): `wsl --mount \\.\PHYSICALDRIVEn --partition 2` (identificar `n` con `Get-Disk` por modelo y tamaño). Leer como root con `wsl.exe -u root` bajo `/mnt/wsl/PHYSICALDRIVEnp2`.
5. `/var/log` está en RAM (writecache de OMV): tras el fallo no hay logs. Para diagnosticar, crear un servicio temporal en el rootfs (p. ej. `nas-diag.service`, `After=network-online.target`) que vuelque `ip -br addr`, `systemctl --failed` y `journalctl -b -p warning` a `/boot/firmware/diag.txt`; arrancar la Pi, volver a sacar el SSD y leer `diag.txt` en Windows.
6. Desmontar: `wsl.exe -u root umount /mnt/wsl/PHYSICALDRIVEnp2` y `sync`; luego `wsl --unmount \\.\PHYSICALDRIVEn`. Windows no deja expulsar el disco mientras WSL lo retiene: desconectar solo tras `sync` y el desmontaje.
7. Tras recuperar el acceso: borrar `nas-diag.service` (`sudo systemctl disable --now nas-diag.service && sudo rm /etc/systemd/system/nas-diag.service /boot/firmware/diag.txt`) y continuar en el paso donde se quedó.

Esperado: la Pi vuelve a responder a `ssh nas`; sin restos del servicio de diagnóstico.

Si falla: si `chkdsk` no repara `bootfs` o el rootfs no monta, restaurar la imagen del paso 0 en el SSD.

## Vuelta atrás

Restaurar en el SSD la imagen del paso 0 (estado previo a OMV). Si no hay imagen: volver
a grabar el XG5 (RBK 02) y repetir los RBK 03 y 04. Los plugins se desinstalan desde Sistema →
Complementos. Los discos de datos no se han tocado.

## Evidencias

- Versión de `openmediavault` y de cada plugin en el OPS
- Capturas 4.1 a 4.4 (sin contraseñas) en el OPS

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-09 | Runbook Agent | Escenario C: cita HLD v2 2.1; usuario `nas`, IP 192.168.1.11 (ADR-019), sudo sin contraseña con confirmación del guard (ADR-020) en prerrequisitos; paso 3 comprueba que `ssh nas` sigue con clave; nuevos pasos 11 (Servicios → SSH solo clave, grupo `_ssh`) y 12 (`sshd -T`) para que OMV no reactive PasswordAuthentication; verificación final ampliada |
| 2.1 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
| 2.2 | 2026-10-09 | Runbook Agent | Escenario C, lecciones de OPS-2026-10-09-rbk04: nuevo paso 0 (apagado limpio e imagen del SSD en D:; numeración de pasos 1-12 conservada); pasos 1-2 como órdenes de una línea `ssh -t nas '…'`, nunca un bloque pegado (incidencia 1); espera de 10 min y no desenchufar con LED verde parpadeando (incidencia 2); paso 3 comprueba `end0`, `systemctl --failed` y espera `passwordauthentication yes` hasta el paso 11 (incidencia 3); paso 3b drop-in `wait-online --any --timeout=30`; nueva sección «Recuperación sin pantalla»; prerrequisitos y vuelta atrás actualizados. Visto bueno del usuario: se mantiene Aprobado |
