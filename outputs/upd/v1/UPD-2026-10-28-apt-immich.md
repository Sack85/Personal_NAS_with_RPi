# UPD — Actualización de octubre 2026: apt completo (OMV 8.6), Immich 3.3.5 y Tailscale

| Campo | Valor |
|---|---|
| **Documento** | UPD |
| **Versión** | 1.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-28 |
| **Última modificación** | 2026-10-28 |
| **Autor** | Maintainer Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Inventario** | state/inventory/2026-10-28.yaml |
| **Inventario anterior** | Ninguno (primer inventario; sin diff posible) |
| **Ventana** | 2026-10-28/29, con la imagen del SSD de hoy verificada |
| **Riesgo máximo** | Cambio |

## Resumen

Primer plan de actualización del NAS, tras el cuelgue del 21 al 28 de octubre y con la imagen
del SSD del sistema hecha hoy (`D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`), que es la vuelta
atrás global. Se aplica todo lo pendiente de apt (OpenMediaVault 8.6.0 y plugins, Docker y
containerd, Tailscale 1.104.4, seguridad de php8.4, nginx, ca-certificates, tzdata, raspi-config,
rpicam/libcamera, rpi-connect-lite y el paquete `rpi-eeprom` **sin aplicar** la EEPROM) y se sube
Immich de v3.3.3 a v3.3.5 (corrección de seguridad). El kernel no cambia (6.18.50+rpt-rpi-2712
se mantiene; solo `linux-base`), pero tras el reinicio se comprueban igualmente los tres discos
SATA y el enlace PCIe. Antes se hace un `snapraid sync` (el último es del 2026-10-20). Tras el
reinicio final se enlaza con el RBK 16 (resiliencia) pendiente.

## Cambios disponibles

| Componente | Versión actual | Versión nueva | Tipo | Fuente | Riesgo |
|---|---|---|---|---|---|
| openmediavault | 8.5.11-1 | 8.6.0-1 | Menor | Sin notas encontradas (búsqueda 2026-10-28 sin changelog de 8.6.0); riesgo subido | Medio |
| openmediavault-compose / cterm / mergerfs / omvextrasorg / writecache | 8.2.2 / 8.0.4 / 8.0.3 / 8.0.3 / 8.3.0 | 8.2.5 / 8.0.5 / 8.0.4 / 8.0.4 / 8.3.1 | Menor | Sin notas encontradas (repositorio omv-extras); riesgo subido | Medio |
| docker-ce, containerd.io, docker-compose-plugin | 5:29.9.0, 2.4.1-2, 5.6.0 | 5:29.9.2, 2.4.2-3, 5.6.1 | Menor | Sin notas encontradas; parches del repositorio de Docker | Medio (reinicia contenedores) |
| tailscale | 1.104.2 | 1.104.4 | Menor | Sin notas encontradas; parche del repositorio de Tailscale | Bajo |
| php8.4 (9 paquetes) | 8.4.26 | 8.4.27 | Seguridad | Debian security (trixie-security), según apt | Bajo |
| nginx | 1.26.3-3+deb13u9 | 1.26.3-3+deb13u10 | Seguridad | Debian trixie-security, según apt | Medio (sirve la web de OMV) |
| ca-certificates, libbrotli1, tzdata | 20250419, 1.1.0-2+b7, 2026c | 20250419+deb13u1, 1.1.0-2+deb13u1, 2026e | Seguridad/menor | Debian trixie-updates, según apt | Bajo |
| linux-base | 4.12.1 | 4.17~bpo13+1 | Menor | Raspberry Pi OS (no cambia el kernel) | Bajo |
| raspi-config, rpicam-apps/libcamera, rpi-connect-lite | 20261026, 1.13.0, 2.13.0 | 20261026+2, 1.14.0, 2.14.0 | Menor | Repositorio de Raspberry Pi; sin notas encontradas | Bajo |
| rpi-eeprom (paquete; firmware EEPROM no se aplica) | 28.33-1 | 28.34-1 | Menor | Repositorio de Raspberry Pi; HLD §3 / ADR-021 | Medio |
| immich-server, immich-machine-learning | v3.3.3 | v3.3.5 | Seguridad (CA compromise, según el usuario) | Sin notas de v3.3.5 encontradas en la búsqueda; revisar GitHub immich-app/immich releases antes del paso 7 | Medio |
| nextcloud-aio-mastercontainer | latest | La que ofrezca el panel AIO | Menor | Panel de AIO | Bajo |

## Impacto en el diseño

| Cambio | Afecta a (HLD) | Riesgo | Mitigación |
|---|---|---|---|
| OMV 8.6.0 y plugins | §3 Sistema, §6 Servicios, §10 | Un plugin incompatible deja la web sin cargar o reescribe sshd/writecache | Foto de configuración antes; después `openmediavault-engined` activo, `sshd -T` y web de OMV |
| OMV gestiona sshd | §8 Seguridad | La contraseña por SSH podría volver a activarse | `ssh -o BatchMode=yes nas hostname` y `sshd -T \| grep passwordauthentication` → `no` |
| Docker/containerd | §6 Servicios (AIO, Immich, Caddy si aplica) | Los contenedores se reinician durante la actualización | Se actualiza fuera de uso; después todos `healthy`/`Up` |
| Tailscale 1.104.4 | §4 Red | Pérdida del nombre `nas` o del certificado de Caddy | `tailscale status` con hostname `nas`; si no, `tailscale set --hostname=nas` |
| nginx | §4 Red, §6 (web de OMV) | La web de OMV no responde | `systemctl is-active nginx` y cargar la web |
| rpi-eeprom (paquete) | §3 Arranque, ADR-021 | El paquete podría programar una actualización de la EEPROM en el siguiente arranque | `rpi-eeprom-update` solo en lectura antes de reiniciar; no se ejecuta `-a`; guard bloquea EEPROM |
| Immich 3.3.5 | §6 Servicios, §10 (Immich con UPD) | Migración de base de datos o fallo al arrancar | Precondición de volcado de Immich; vuelta atrás a `IMMICH_VERSION=v3.3.3` |

## Decisión

| Componente | Decisión | Motivo |
|---|---|---|
| apt completo (OMV 8.6.0 y plugins, Docker, Tailscale, php8.4, nginx, ca-certificates, tzdata, raspi-config, rpicam, rpi-connect-lite, linux-base) | Aplicar | Parches y seguridad; vuelta atrás con la imagen del SSD de hoy |
| Paquete rpi-eeprom | Aplicar | Solo el paquete; no cambia el firmware sin `rpi-eeprom-update -a` |
| Firmware EEPROM | Posponer | Arranque USB con `nospi10`; el usuario se queda en `BOOT_ORDER=0xf41` (ADR-021) |
| Immich v3.3.5 | Aplicar | Corrección de seguridad |
| Nextcloud AIO | No aplica | Se actualiza desde su panel (usuario) si ofrece versión nueva; no se fuerza |

## Precondiciones

- [ ] Imagen del SSD `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz` con verificación terminada sin errores (sustituye al backup restic, que aún no existe: riesgo aceptado por el usuario)
- [ ] `snapraid status` sin errores (OK en el inventario) y `snapraid sync` hecho hoy (paso 2), porque el último es del 2026-10-20
- [ ] Backup de AIO: desactivado por ADR-027; no aplica. Volcado de Immich de la última noche presente en `/srv/mergerfs/pool/Archivo/immich-db`
- [ ] Backup restic de menos de 31 días: **no cumple** (nunca hecho); se acepta con la imagen del SSD como vuelta atrás y los datos del pool protegidos por SnapRAID
- [ ] SAI en `OL`: no hay SAI instalado (pregunta abierta HLD §9); no se actualiza si hay aviso de corte
- [ ] Sin alertas CRITICAL en el inventario (no hay inventario anterior para `tools/inventory_diff.py`; salud del inventario sin alertas: PCIe 8GT/s, throttled 0x0, SMART 5/197/198 a 0)

## Pasos

### Paso 1: Comprobar precondiciones y estado de partida

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas "sudo snapraid status | tail -n 8; grep -E '^(dtparam=pciex1|dtoverlay=pcie-32bit-dma-pi5)' /boot/firmware/config.txt; ls -t /srv/mergerfs/pool/Archivo/immich-db | head -n 2; sudo rpi-eeprom-update"
```

Esperado: «No error detected»; las líneas `dtparam=pciex1` y `dtoverlay=pcie-32bit-dma-pi5`;
volcado de Immich de la última noche; `rpi-eeprom-update` informa (solo lectura) de la versión
actual y la disponible, sin aplicar nada.

Si falla: no se actualiza; se anota en el OPS y se revisa SnapRAID o config.txt primero.

### Paso 2: Sync de SnapRAID antes de actualizar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas "sudo snapraid diff | tail -n 6; sudo snapraid sync && sudo snapraid status | tail -n 5"
```

Esperado: sync termina con «Everything OK» y `status` sin errores ni «to sync». Si `diff` muestra
un número anómalo de borrados (más de 50), se para y se pregunta al usuario antes del sync.

Si falla: no se actualiza; se anota el error en el OPS y se revisa con `/storage-plugin:diagnose-disk`.

### Paso 3: Foto de la configuración

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | PC |

Invoca `/operator-plugin:snapshot-config` y haz commit de `state/config/`.

Esperado: `state/config/` al día con fecha 2026-10-28 (sshd_config, Caddyfile, config.txt, compose).

Si falla: sigue solo si el usuario lo acepta; la imagen del SSD sigue siendo la vuelta atrás.

### Paso 4: Simular la actualización

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas "sudo apt-get update -q && sudo apt-get -s full-upgrade | grep -E '^(Inst|Remv)'"
```

Esperado: solo `Inst` de los paquetes de la tabla «Cambios disponibles»; **ninguna** línea
`Remv` y ningún `linux-image` nuevo.

Si falla: si aparece una eliminación o un kernel nuevo, se para y se rehace el UPD
(`/maintainer-plugin:update-upd`).

### Paso 5: Aplicar las actualizaciones de apt

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Sistema → Gestión de actualizaciones → Comprobar → seleccionar todo → Instalar. Esperar
a «Done» sin errores (la web puede cortarse un momento al actualizarse nginx y OMV; recargar).
No reiniciar todavía.

Esperado: la lista de actualizaciones queda vacía; `ssh nas "apt list --upgradable 2>/dev/null | wc -l"` devuelve 1 (solo la cabecera).

Si falla: copia el error en el OPS y no reinicies; el agente revisa con `ssh nas "sudo apt-get -s -f install"`.

### Paso 6: Comprobar sshd, Tailscale y EEPROM antes del reinicio

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh -o BatchMode=yes nas "hostname; sudo sshd -T | grep passwordauthentication; tailscale version | head -n 1; tailscale status --self --peers=false; sudo rpi-eeprom-update; systemctl is-active openmediavault-engined nginx"
```

Esperado: `nas`; `passwordauthentication no`; tailscale 1.104.4 con el nombre `nas`;
`rpi-eeprom-update` sin «UPDATE PENDING» aplicado (solo informa); `active` dos veces.

Si falla: si `passwordauthentication yes`, se para y se vuelve al paso de SSH del RBK 04. Si el
nombre de Tailscale no es `nas`, el agente ejecuta `ssh nas "sudo tailscale set --hostname=nas"`
(mismo flag no por defecto que el primer `tailscale up`). Si `rpi-eeprom-update` indica una
actualización programada para el próximo arranque, el usuario la cancela con
`ssh -t nas "sudo rpi-eeprom-update -r"` (el guard bloquea EEPROM al agente).

### Paso 7: Subir Immich a v3.3.5

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH y PC |

Comprobación previa: leer las notas de v3.3.5 en GitHub (immich-app/immich, Releases) y confirmar
que no exigen cambios en el `docker-compose.yml`; si los exigen, se para y se actualiza el UPD.

En el PC, editar la línea del repo `IMMICH_VERSION=v3.3.3` → `IMMICH_VERSION=v3.3.5` en
`state/config/srv/immich/compose/env.sin-secretos`. En el NAS, solo esa línea (sin tocar
`DB_PASSWORD`), una orden por línea, sin pegar varias líneas:

```bash
ssh nas "sudo sed -i 's/^IMMICH_VERSION=.*/IMMICH_VERSION=v3.3.5/' /srv/immich/compose/.env && sudo grep -c '^IMMICH_VERSION=v3.3.5$' /srv/immich/compose/.env && sudo grep -c '^DB_PASSWORD=' /srv/immich/compose/.env"
ssh nas "cd /srv/immich/compose && sudo docker compose pull && sudo docker compose up -d"
```

Esperado: los dos `grep -c` devuelven `1` y `1`; `pull` descarga v3.3.5 y `up -d` recrea
`immich-server` e `immich-machine-learning`; a los 2–3 min `docker ps` los muestra `healthy`.

Si falla: ver «Vuelta atrás» de Immich.

### Paso 8: Nextcloud AIO

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO |

Abrir el panel de AIO. Si ofrece actualización del mastercontainer o de los contenedores, pulsar
«Stop containers» → actualizar → «Start and update containers». Si no ofrece nada, se anota «sin
versión nueva» en el OPS.

Esperado: todos los contenedores en verde en el panel.

Si falla: se anota el error y se revisa `ssh nas "sudo docker logs --tail 50 nextcloud-aio-mastercontainer"`.

### Paso 9: Reinicio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |

Comando (una sola orden de una línea; no pegar varias líneas tras `ssh nas`):

```bash
ssh nas "sudo reboot"
```

Esperado: la sesión se corta (normal); en menos de 10 min `ssh -o BatchMode=yes nas hostname`
responde `nas`. **Nunca desenchufes mientras el LED verde parpadee.**

Si falla: si a los 10 min no responde y el LED verde está quieto, «Recuperación sin pantalla» del
RBK 16 y, si no vuelve, restaurar la imagen del SSD (Vuelta atrás).

### Paso 10: Comprobar discos, PCIe y servicios

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh -o BatchMode=yes nas "uname -r; ls -l /dev/disk/by-id/ | grep -E 'WDZ03YJJ|WD-WXU1EB6APMW5|S5SVNG0N868475F' | grep -v part; lsblk -d -o NAME,SIZE,MODEL,SERIAL; sudo lspci -vv | grep LnkSta:; vcgencmd get_throttled; findmnt -n /srv/mergerfs/pool; sudo sshd -T | grep passwordauthentication; tailscale status --self --peers=false; systemctl is-active openmediavault-engined nginx caddy; sudo docker ps --format '{{.Names}}: {{.Status}}'"
```

Esperado: kernel `6.18.50+rpt-rpi-2712` (sin cambio); los tres discos SATA por serie; `Speed
8GT/s`; `throttled=0x0`; pool montado; `passwordauthentication no`; Tailscale con nombre `nas`;
`active` tres veces; contenedores de AIO e Immich `Up` / `healthy`.

Si falla: ver «Vuelta atrás». El usuario comprueba además que la web de OMV carga y que
`https://nas.<tailnet>` (Caddy) abre Nextcloud e Immich.

### Paso 11: Inventario posterior y enlace con el RBK 16

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | PC |

Invoca `/maintainer-plugin:inventory` y luego `uv run python tools/inventory_diff.py`
(2026-10-28 previo → posterior). Después, con el NAS ya reiniciado y sano, se ejecuta el RBK 16
(`/operator-plugin:create-ops RBK-2026-10-28-16-resiliencia.md`) en un OPS aparte; su paso 2
(imagen) puede darse por cubierto con la imagen de hoy si el usuario lo acepta, ya que sus cambios
se hacen sobre el sistema actualizado.

Esperado: versiones nuevas en el inventario y sin alertas CRITICAL.

Si falla: alerta CRITICAL → no se sigue con el RBK 16; revisión indicada por el diff.

## Verificación posterior

| Comprobación | Comando | Esperado |
|---|---|---|
| Kernel sin cambio | `ssh nas uname -r` | 6.18.50+rpt-rpi-2712 |
| Discos visibles | `ssh nas lsblk -d -o NAME,SIZE,MODEL,SERIAL` | SSD de sistema + tres SATA (WDZ03YJJ, WD-WXU1EB6APMW5, S5SVNG0N868475F) |
| Enlace PCIe | `ssh nas "sudo lspci -vv \| grep LnkSta:"` | Speed 8GT/s, Width x1 |
| SSH sin contraseña | `ssh -o BatchMode=yes nas "sudo sshd -T \| grep passwordauthentication"` | passwordauthentication no |
| Tailscale | `ssh nas "tailscale status --self --peers=false"` | nombre `nas`, 1.104.4 |
| OMV y nginx | `ssh nas systemctl is-active openmediavault-engined nginx` | active, active; web de OMV carga (usuario) |
| Caddy | `ssh nas systemctl is-active caddy` | active; Nextcloud e Immich abren por HTTPS |
| Contenedores | `ssh nas "sudo docker ps --format '{{.Names}}: {{.Status}}'"` | AIO e Immich v3.3.5 `Up`/`healthy` |
| EEPROM no tocada | `ssh nas "sudo rpi-eeprom-update"` | versión de bootloader igual que en el paso 1 |
| SnapRAID | `ssh nas "sudo snapraid status \| tail -n 5"` | No error detected |
| Inventario posterior | `/maintainer-plugin:inventory` | sin alertas nuevas en `tools/inventory_diff.py` |

## Vuelta atrás

- **Global (el NAS no arranca o la web/SSH quedan rotos sin arreglo rápido)**: `ssh nas "sudo
  poweroff"` si responde; con el LED verde apagado, desenchufar los 12 V, conectar el SSD al PC y
  restaurar `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz` (lo hace el usuario; identificar el SSD
  por modelo y serie `78EB616DKAWP` con `lsblk -o NAME,SIZE,MODEL,SERIAL`, nunca por letra).
  Volver a poner el SSD en el **USB-A azul**. Los datos del pool no se tocan.
- **OMV / plugins / nginx**: el usuario ejecuta `sudo omv-firstaid` y se compara con
  `state/config/`; versión anterior de un paquete desde la caché de apt
  (`ls /var/cache/apt/archives/openmediavault_8.5.11*`, `sudo dpkg -i` de ese fichero exacto).
- **sshd con contraseña**: rehacer el paso de SSH del RBK 04 y `omv-salt deploy run ssh`.
- **Tailscale**: `ssh nas "sudo tailscale set --hostname=nas"`; si no conecta,
  `sudo apt-get install tailscale=1.104.2` desde la caché.
- **Docker**: `sudo apt-get install docker-ce=5:29.9.0* containerd.io=2.4.1-2` si los contenedores
  no arrancan con la versión nueva.
- **Immich**: `ssh nas "sudo sed -i 's/^IMMICH_VERSION=.*/IMMICH_VERSION=v3.3.3/' /srv/immich/compose/.env"`
  y `ssh nas "cd /srv/immich/compose && sudo docker compose up -d"`; deshacer el cambio en
  `env.sin-secretos`. Si la base de datos se migró y no arranca con v3.3.3, restaurar el volcado
  de `/srv/mergerfs/pool/Archivo/immich-db` según el RBK 15.
- **EEPROM**: no se aplica; si se hubiera programado, `ssh -t nas "sudo rpi-eeprom-update -r"` (usuario).
- **AIO**: restaurar desde su panel (backup desactivado por ADR-027: en ese caso, imagen del SSD).

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-28 | Maintainer Agent | Creación |
| 1.0 | 2026-10-28 | Maintainer Agent | Estado cambiado a Aprobado (GO de persona 1 el 2026-10-28; acepta sin backup restic, sin SAI y backup AIO desactivado por ADR-027; vuelta atrás: imagen del SSD en D:\_nas_imagenes, ejecución solo tras verificarla) |
