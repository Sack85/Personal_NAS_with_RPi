# OPS — Ejecución del RBK 04 (OpenMediaVault 8, plugins y correo)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v2 (2.1, Aprobado) — RBK-2026-10-09-04-omv-plugins-correo.md |
| **Resultado** | En curso |
| **Inicio** | 2026-10-09 |
| **Fin** | — |

> Ejecución **parcial**: pasos 1 a 3 hechos hoy; se continúa mañana (2026-10-10) desde el paso 4
> con `/operator-plugin:update-ops`. Registro hecho a posteriori, sin re-ejecutar nada.

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
| 4. Primer acceso y contraseña de admin | Cambio | Usuario | — | Pendiente | — |
| 5. Mover la web de OMV al puerto 8000 | Cambio | Usuario | — | Pendiente | — |
| 6. Instalar los plugins | Cambio | Usuario | — | Pendiente | — |
| 7. Comprobar los plugins instalados | Lectura | Agente | — | Pendiente | — |
| 8. Configurar el correo de avisos con Gmail | Cambio | Usuario | — | Pendiente | — |
| 9. Enviar un correo de prueba y activar avisos | Cambio | Usuario | — | Pendiente | — |
| 10. Comprobar que no hay actualizaciones automáticas con reinicio | Lectura | Agente | — | Pendiente | — |
| 11. Servicio SSH de OMV solo con clave | Cambio | Usuario | — | Pendiente | — |
| 12. Comprobar que sshd sigue solo con clave | Lectura | Agente | — | Pendiente | — |

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

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 1-2 | Incidencia 1: el usuario pegó todo el bloque de comandos de una vez; al cortarse el SSH en el reinicio, las líneas restantes se ejecutaron en el PC (WSL). Un `wget preinstall \| sudo bash` quedó esperando la contraseña sudo del PC y no llegó a ejecutarse | Cancelado; comprobado sin cambios en `/etc/apt` del PC | RBK: separar el bloque y advertir de no pegar varias líneas tras `ssh nas` (`/runbook-plugin:update-rbk`) |
| 2 | Incidencia 2: tras el reinicio la Pi no volvió a la red (sin luces de red, LED verde fijo; sin pantalla). Causa raíz: `/boot/firmware/config.txt` (FAT) corrupto, probablemente por cortes de corriente o desconexiones sin apagar | Apagado (desenchufar 12 V), SSD al PC, lectura del rootfs con `wsl --mount` (E2), servicio temporal `nas-diag.service` que volcaba la red a `/boot/firmware/diag.txt`; `chkdsk E: /f` y `config.txt` restaurado desde `state/config/` (E3). Desmontaje: `umount` como root (`wsl.exe -u root`); Windows no deja expulsar (WSL retiene el disco), se desconectó tras `sync` | `nas-diag.service` y `diag.txt` eliminados en el paso 3. Recomendado: SAI y apagar siempre con `sudo poweroff`; añadir al RBK la recuperación offline |
| 3 | Interfaz renombrada `eth0` → `end0`; `systemd-networkd-wait-online` fallaba esperando todas las interfaces | Drop-in `/etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf` con `--any --timeout=30`; 0 unidades fallidas | Cambio fuera del RBK: incorporarlo al RBK 04 y al HLD (`/runbook-plugin:update-rbk`) |
| 3 | Incidencia 3: OMV reactivó `PasswordAuthentication` (`sshd -T`: `passwordauthentication yes`) | Se corrige en el paso 11 desde la web de OMV | Pendiente (usuario, 2026-10-10) |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| OMV 8 instalado y engined activo | 8.5.11-1, active | Sí |
| `ssh nas` con clave | Sí | Sí |
| Unidades systemd fallidas | 0 | Sí |
| SSH solo con clave | `passwordauthentication yes` | No (paso 11 pendiente) |
| Pasos 4-12 | Pendientes | — |

## Cambios en la configuración

- OpenMediaVault 8.5.11-1 con omv-extras y `openmediavault-writecache`; cloud-init eliminado.
- Netplan de OMV (`10-openmediavault-default.yaml`, `20-openmediavault-eth0.yaml`); interfaz `end0`.
- Drop-in `systemd-networkd-wait-online.service.d/any.conf` (`--any --timeout=30`).
- `/boot/firmware/config.txt` restaurado desde `state/config/` (mismo contenido).
- Usuario `nas` en el grupo `_ssh`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Operator Agent | Registro de la ejecución parcial (pasos 1-3); continúa en el paso 4 |
