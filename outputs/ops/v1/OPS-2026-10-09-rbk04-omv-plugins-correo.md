# OPS — Ejecución del RBK 04 (OpenMediaVault 8, plugins y correo)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v2 (2.1, Aprobado) — RBK-2026-10-09-04-omv-plugins-correo.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-09 |
| **Fin** | 2026-10-13 |

> Pasos 1 a 3 hechos el 2026-10-09; reanudada el 2026-10-13 en el paso 4 con
> `/operator-plugin:update-ops` y completada (pasos 4-12). El paso 0 (imagen del SSD) y el 3b
> quedan como estaban documentados o no aplican.

## Alcance

Instalación de OpenMediaVault 8 con omv-extras (pasos 1-3 del RBK 04). Quedan pendientes el
primer acceso web, el puerto 8000, los plugins, el correo y el SSH solo con clave en OMV
(pasos 4-12). Ningún paso destructivo; los discos de datos no se tocan.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 04 v2.1 aprobado | Sí |
| RBK 01-03 aplicados | Sí (OPS-2026-10-09-rbk01-03-montaje-arranque.md, Aprobado) |
| `ssh nas` con clave, 192.168.1.11 | Sí, antes del paso 1 |
| Pasos destructivos | Ninguno |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Ejecutar el script preinstall de omv-extras | Cambio | Usuario | — | OK | E1 |
| 2. Ejecutar el script install de omv-extras | Cambio | Usuario | 18:02 | OK | E1, E2, E3 |
| 3. Comprobar que OMV está en marcha | Lectura | Agente | — | OK | E4 |
| 4. Primer acceso y contraseña de admin | Cambio | Usuario | 2026-10-13 | OK | E5 |
| 5. Mover la web de OMV al puerto 8000 | Cambio | Agente | 2026-10-13 | OK | E6 |
| 6. Instalar los plugins | Cambio | Usuario | 2026-10-13 | OK | E7 |
| 7. Comprobar los plugins instalados | Lectura | Agente | 2026-10-13 | OK | E8 |
| 8. Configurar el correo de avisos con Gmail | Cambio | Usuario | 2026-10-13 | OK | E9 |
| 9. Enviar un correo de prueba y activar avisos | Cambio | Usuario | 14:14 | OK | E9 |
| 10. Comprobar que no hay actualizaciones automáticas con reinicio | Lectura | Agente | 2026-10-13 | OK | E10 |
| 11. Servicio SSH de OMV solo con clave | Cambio | Usuario | 2026-10-13 | OK | E11 |
| 12. Comprobar que sshd sigue solo con clave | Lectura | Agente | 2026-10-13 | OK | E12 |

## Evidencias

### E1 — Salida del install de omv-extras (pegada por el usuario)

```
salt: Succeeded: 15, Failed: 0
[omvinstall] done  (rc=0)
plugin openmediavault-writecache instalado
cloud-init eliminado
DNS failing to resolve. Fixing
reinicio 18:02:44
```

### E2 — Diagnóstico offline del rootfs (SSD en el PC, `wsl --mount \\.\PHYSICALDRIVE1 --partition 2`)

```
/etc/netplan/10-openmediavault-default.yaml   renderer: networkd
/etc/netplan/20-openmediavault-eth0.yaml      match: macaddress, dhcp4: true
/var/log: sin entradas posteriores a 18:02 (writecache mantiene /var/log en RAM)
```

### E3 — Reparación de la partición de arranque (FAT, en Windows)

```
config.txt: "fichero dañado e ilegible"
chkdsk E: /f  ->  "La première unité d'allocation n'est pas valide" (corregido)
config.txt restaurado desde state/config/boot/firmware/config.txt
SHA256 idéntico al del repo: 132B731F…
436 ficheros de bootfs leídos sin errores
Arranque posterior: luces de discos, SSH OK en 192.168.1.11
```

### E4 — Paso 3 y ajustes posteriores (agente, `ssh nas`)

```
openmediavault 8.5.11-1
openmediavault-engined: active (running)
ssh nas: entra con clave
interfaz: eth0 -> end0 (netplan casa por MAC; red OK)
systemd-networkd-wait-online: fallaba -> drop-in any.conf (--any --timeout=30)
systemctl --failed: 0 unidades
usuario nas en grupo _ssh
sshd -T: passwordauthentication yes   (ver incidencia 3)
```

### E5 — Paso 4 (usuario, web de OMV)

```
Contraseña de admin cambiada (en el gestor de contraseñas)
```

### E6 — Paso 5 (agente, `ssh nas`)

```
omv-rpc WebGui setSettings: port 8000
omv-salt deploy run nginx: Succeeded: 23, Failed: 0
http://<nas>:8000 -> HTTP 200
http://<nas>:80   -> sin respuesta
```

### E7 — Paso 6

```
Web (Claude Desktop + Chrome): openmediavault-snapraid 8.0.3, -sharerootfs 8.0.1-1, -mergerfs 8.0.3
  mergerfs: "CONNECTION LOST" (reinicio de engined); instalación terminada
Agente (apt por SSH): openmediavault-compose 8.2.2
  descarga de regctl fallida (GnuTLS pull error) -> sudo dpkg --configure -a -> OK
openmediavault-cterm: no instalado (apt no lo requiere)
omv-salt deploy run (cron, compose pendientes): Succeeded: 24, Failed: 0
omv-rpc Config applyChanges: "Invalid RPC response"
```

### E8 — Paso 7 (agente)

```
dpkg -l: ii openmediavault-snapraid, -sharerootfs, -mergerfs, -compose (4 plugins)
```

### E9 — Pasos 8-9 (usuario, web de OMV)

```
SMTP smtp.gmail.com:587, STARTTLS, autenticación; contraseña de aplicación en el gestor de contraseñas
postfix: status=sent; Gmail: 250 2.0.0 OK (2 mensajes, 14:14)
Notificaciones: authentication, misc, apt, monit (procesos, carga, CPU, memoria, filesystems), smartmontools
```

### E10 — Paso 10 (agente)

```
Unattended-Upgrade::Automatic-Reboot "false";
```

### E11 — Paso 11 (usuario, web de OMV)

```
SSH activado, puerto 22
Permitir root: no (estaba sí)
Autenticación por contraseña: no (estaba sí)
Clave pública: sí
Aplicados también los cambios pendientes de la instalación (cpupower, cron, systemd-logind)
```

### E12 — Paso 12 y cierre (agente)

```
sshd -T: passwordauthentication no, pubkeyauthentication yes, permitrootlogin no, port 22
id nas: grupos _ssh y sudo
Intento de acceso sin clave rechazado -> Permission denied (publickey)
systemctl --failed: 0 unidades
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 1-2 | Incidencia 1: el usuario pegó todo el bloque de comandos de una vez; al cortarse el SSH en el reinicio, las líneas restantes se ejecutaron en el PC (WSL). Un `wget preinstall \| sudo bash` quedó esperando la contraseña sudo del PC y no llegó a ejecutarse | Cancelado; comprobado sin cambios en `/etc/apt` del PC | RBK: separar el bloque y advertir de no pegar varias líneas tras `ssh nas` (`/runbook-plugin:update-rbk`) |
| 2 | Incidencia 2: tras el reinicio la Pi no volvió a la red (sin luces de red, LED verde fijo; sin pantalla). Causa raíz: `/boot/firmware/config.txt` (FAT) corrupto, probablemente por cortes de corriente o desconexiones sin apagar | Apagado (desenchufar 12 V), SSD al PC, lectura del rootfs con `wsl --mount` (E2), servicio temporal `nas-diag.service` que volcaba la red a `/boot/firmware/diag.txt`; `chkdsk E: /f` y `config.txt` restaurado desde `state/config/` (E3). Desmontaje: `umount` como root (`wsl.exe -u root`); Windows no deja expulsar (WSL retiene el disco), se desconectó tras `sync` | `nas-diag.service` y `diag.txt` eliminados en el paso 3. Recomendado: SAI y apagar siempre con `sudo poweroff`; añadir al RBK la recuperación offline |
| 3 | Interfaz renombrada `eth0` → `end0`; `systemd-networkd-wait-online` fallaba esperando todas las interfaces | Drop-in `/etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf` con `--any --timeout=30`; 0 unidades fallidas | Cambio fuera del RBK: incorporarlo al RBK 04 y al HLD (`/runbook-plugin:update-rbk`) |
| 3 | Incidencia 3: OMV reactivó `PasswordAuthentication` (`sshd -T`: `passwordauthentication yes`) | Se corrige en el paso 11 desde la web de OMV | Cerrada el 2026-10-13 (E11, E12) |
| 5 | Incidencia 4 (desviación aceptada): el paso lo hizo el agente; el puerto 8000 lo aplicó el agente por SSH (`omv-rpc` + `omv-salt deploy run nginx`) en lugar del usuario en la web | Resultado comprobado (E6) | RBK: valorar recoger la vía por SSH (`/runbook-plugin:update-rbk`) |
| 6 | Incidencia 5: un clic en la web quedó bloqueado por el control de seguridad de Claude Desktop; mergerfs mostró "CONNECTION LOST" (reinicio de engined) pero terminó | Comprobado en el paso 7 (E8) | Ninguno |
| 6 | Incidencia 6: el paso se hizo entre el usuario (snapraid, sharerootfs, mergerfs desde la web con Claude Desktop + Chrome) y el agente (compose por apt); falló la descarga de regctl (GnuTLS pull error) | `dpkg --configure -a`; cambios pendientes aplicados con `omv-salt deploy run` (24 OK); `omv-rpc Config applyChanges` dio "Invalid RPC response" | RBK: documentar el reintento y la vía por `omv-salt` |
| 11 | Incidencia 7: hecho desde la web con Claude Desktop + Chrome; había cambios pendientes de la instalación (cpupower, cron, systemd-logind) | El usuario decidió aplicarlos junto con el SSH | Ninguno; verificado en E12 |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| OMV 8 instalado y engined activo | 8.5.11-1, active | Sí |
| Web de OMV en el puerto 8000 | HTTP 200; :80 sin respuesta | Sí |
| Plugins snapraid, sharerootfs, mergerfs, compose | 4 en estado `ii` | Sí |
| Correo de avisos | Prueba entregada (250 OK) | Sí |
| Sin reinicio automático por actualizaciones | `Automatic-Reboot "false"` | Sí |
| `ssh nas` con clave | Sí | Sí |
| SSH solo con clave | `passwordauthentication no`, `permitrootlogin no` | Sí |
| Unidades systemd fallidas | 0 | Sí |

## Cambios en la configuración

- OpenMediaVault 8.5.11-1 con omv-extras y `openmediavault-writecache`; cloud-init eliminado.
- Netplan de OMV (`10-openmediavault-default.yaml`, `20-openmediavault-eth0.yaml`); interfaz `end0`.
- Drop-in `systemd-networkd-wait-online.service.d/any.conf` (`--any --timeout=30`).
- `/boot/firmware/config.txt` restaurado desde `state/config/` (mismo contenido).
- Usuario `nas` en el grupo `_ssh`.
- Contraseña de admin de OMV cambiada (en el gestor de contraseñas).
- Web de OMV en el puerto 8000.
- Plugins openmediavault-snapraid 8.0.3, -sharerootfs 8.0.1-1, -mergerfs 8.0.3, -compose 8.2.2.
- Correo de avisos por smtp.gmail.com:587 (STARTTLS) y notificaciones activadas.
- SSH de OMV: puerto 22, sin root, sin contraseña, con clave pública.
- Aplicados los cambios pendientes de cpupower, cron y systemd-logind.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Operator Agent | Registro de la ejecución parcial (pasos 1-3); continúa en el paso 4 |
| 1.1 | 2026-10-13 | Operator Agent | Reanudada en el paso 4; pasos 4-12 completados; Resultado Completado |
| 1.2 | 2026-10-13 | Operator Agent | Ejecución cerrada y aprobada |
