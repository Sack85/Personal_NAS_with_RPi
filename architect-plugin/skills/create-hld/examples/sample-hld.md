# HLD — NAS familiar con Raspberry Pi 5

| Campo | Valor |
|---|---|
| **Documento** | HLD |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-10 |
| **Última modificación** | 2026-10-10 |
| **Autor** | Architect Agent |
| **Entregable previo** | NRD v1 (1.0, Aprobado) — NRD-2026-10-08-nas-familiar.md |

## Resumen

Raspberry Pi 5 con OpenMediaVault 8 arrancando desde un SSD NVMe por USB. Dos niveles: el SSD
guarda sistema, Docker y datos de Nextcloud AIO; un pool MergerFS de dos discos de 1 TB guarda
el archivo familiar, protegido por SnapRAID con un disco de paridad de 1 TB, un backup restic
mensual a un disco desconectado y una copia fuera de casa. Nada se expone a Internet salvo,
opcionalmente, Nextcloud por Tailscale.

## 1. Requisitos cubiertos

| Requisito (NRD) | Cómo se cubre | Sección del HLD |
|---|---|---|
| §3 Capacidad a 3 años: 1 695 GB | Pool D1 + D2 de ~1 800 GB útiles | 5 |
| §5 Fallo de un disco, RPO 24 h | SnapRAID con sync diario a las 04:00 | 5, 7 |
| §5 Ransomware, RPO 1 mes | restic mensual al Hitachi desconectado, 12 versiones | 7 |
| §5 Desastre en casa | Copia fuera de casa de Documentos y Fotos | 7 |
| §6 Clima tropical, 24/7 | Spindown a 45 min, ventilador fijo, filtro, SAI | 9 |
| §7 Nada expuesto salvo Nextcloud | Puertos 8000, 8080 y 22 solo en la LAN; Tailscale | 4, 8 |
| §8 Actualizaciones con plan | Mensuales, manuales, comprobación de discos tras kernel | 10 |

## 2. Hardware y montaje

| Pieza | Modelo | Función |
|---|---|---|
| Placa | Raspberry Pi 5 8 GB + Active Cooler | Servidor |
| Controladora | Radxa Penta SATA HAT (JMB585) + FFC | 4 SATA por PCIe Gen 3, sin RAID por hardware |
| Alimentación | 12 V / 5 A al conector DC del HAT | Discos y Pi por el GPIO; USB-C de la Pi desconectado |
| Sistema | Toshiba XG5 512 GB NVMe en caja USB 3 | Arranque, Docker, datos de Nextcloud |
| Aire | Ventilador 120 mm a velocidad fija baja + filtro | Discos y HAT por debajo de 40 °C |
| SAI | Con USB compatible con NUT | Apagado limpio tras 5 min sin red |

Bahías: 1 = WD (paridad), 2 = vacía, 3 = Toshiba (D1, la de más aire), 4 = QVO (D2, la de menos
aire). Los dos mecánicos quedan separados por la bahía vacía. FFC con la cara negra hacia fuera
y los dos pestillos cerrados.

## 3. Sistema y arranque

Raspberry Pi OS Lite 64-bit (Trixie) grabado con Raspberry Pi Imager 2.x: equipo `nas`,
usuario propio, SSH con contraseña, sin WiFi, sin Raspberry Pi Connect. La Pi 5 arranca desde
USB sin SD. OpenMediaVault 8 con los scripts de omv-extras. Al final de `config.txt`, bajo
`[all]`:

```
dtparam=pciex1
dtparam=pciex1_gen=3
dtoverlay=pcie-32bit-dma-pi5
usb_max_current_enable=1
```

## 4. Red y puertos

Solo Ethernet. Reserva DHCP del equipo `nas` en el router (192.168.1.200). La web de OMV pasa
al puerto 8000 para dejar el 80 a Nextcloud AIO.

| Puerto | Servicio | Expuesto a Internet |
|---|---|---|
| 22 | SSH | No |
| 8000 | Panel de OMV | No |
| 8080 | Panel de AIO | No |
| 80, 8443 | Nextcloud AIO (validación y certificado) | No |
| 445 | Samba | No |

## 5. Almacenamiento

| Rol | Disco | Tamaño | Conexión | Sistema de ficheros | Montaje | En pool | Content |
|---|---|---|---|---|---|---|---|
| Sistema | Toshiba XG5 | 512 GB | USB 3 | ext4 | / | No | Sí |
| Paridad | WD Blue | 1 TB | SATA bahía 1 | ext4 (0 % reservado) | /srv/dev-disk-by-uuid-… (parity) | No | No |
| D1 | Toshiba MK1059 | 1 TB | SATA bahía 3 | ext4 | /srv/dev-disk-by-uuid-… (d1) | Sí | Sí |
| D2 | Samsung QVO | 1 TB | SATA bahía 4 | ext4 | /srv/dev-disk-by-uuid-… (d2) | Sí | Sí |
| Backup | Hitachi | 320 GB | USB, desconectado | ext4, etiqueta `backup` | /mnt/backup (solo al usarlo) | No | No |

Los UUID reales se anotan en el runbook de formateo y en `state/config/`.

### SnapRAID

| Parámetro | Valor |
|---|---|
| Array | `nas` |
| Paridades | 1 (WD Blue) |
| Content files | 3 (d1, d2 y el SSD del sistema) |
| Exclusiones | `*.unrecoverable`, `/lost+found/`, `/tmp/`, `.Trash-*/` |
| Sync | Diario a las 04:00 con diff previo |
| Umbral de borrados | No sincronizar si hay más de 50 borrados; aviso por correo |
| Scrub | Domingo tras el sync, 12 % de bloques con más de 10 días |

### MergerFS

| Parámetro | Valor |
|---|---|
| Nombre | `pool` en `/srv/mergerfs/pool` |
| Ramas | D1 y D2 (nunca la paridad) |
| Política de creación | `mfs` |
| Espacio libre mínimo | 20G |

## 6. Servicios y carpetas

Samba sin invitados y con papelera `.recycle`. Nextcloud AIO por Compose: datos en `ncdata` del
SSD, solo `Fotos` del pool montada (`NEXTCLOUD_MOUNT`), límite de subida 16G, solo el contenedor
Imaginary. Backup diario de AIO a las 03:00 en `Archivo/nextcloud-aio-backup`. hd-idle para
spindown y NUT para el SAI.

| Carpeta | Ubicación | Grupo familia | Backup offline |
|---|---|---|---|
| Documentos | pool | Lectura y escritura | Sí |
| Fotos | pool (www-data, compartida con Nextcloud) | Lectura y escritura | Sí |
| Videos | pool | Lectura y escritura | No |
| Archivo | pool | Solo lectura | Solo nextcloud-aio-backup |
| compose, ncdata | SSD del sistema | Sin acceso | ncdata vía backup de AIO |

## 7. Protección de datos y backups

| Escenario (NRD) | Mecanismo | RPO resultante | Cómo se recupera |
|---|---|---|---|
| Fallo de un disco de datos | SnapRAID | 24 h | Disco nuevo en el mismo montaje + `snapraid -d dN fix` |
| Fallo de la paridad | SnapRAID | 0 | Disco nuevo ≥ 1 TB + sync completo |
| Borrado accidental | Papelera Samba, SnapRAID antes del sync, restic | 24 h | `.recycle` o `snapraid fix -f` o `restic restore` |
| Ransomware | restic al Hitachi desconectado | 1 mes | `restic restore` a carpeta nueva |
| Desastre en casa | Copia fuera de casa (restic) | 1 mes | Restauración en un NAS nuevo según los RBK |
| Fallo del SSD del sistema | Backup diario de AIO en el pool | 24 h | Reinstalar según RBK y restaurar AIO |

## 8. Seguridad

- Nunca se exponen a Internet el panel de OMV (8000), el de AIO (8080) ni SSH (22).
- Acceso exterior solo a Nextcloud y por Tailscale; sin puertos abiertos en el router.
- Usuario propio en la Pi (no `pi`); contraseña de `admin` de OMV cambiada en el primer acceso.
- Un usuario por persona en OMV y en Nextcloud, grupo `familia`, sin invitados.
- Secretos (OMV, AIO, restic, Gmail) en el gestor de contraseñas, nunca en el repo.

## 9. Energía y temperatura

SAI con NUT en modo independiente, apagado tras 300 s en batería. hd-idle para el WD y el
Toshiba a 2 700 s (45 min) con `-i 0` por defecto; spindown de OMV desactivado; APM 254 si el
atributo 193 del Toshiba sube más de 100 al día. Objetivos: Pi < 70 °C, discos ≤ 40 °C (aviso),
45 °C (crítico), `get_throttled` = 0x0.

## 10. Actualizaciones y mantenimiento

Mensuales y manuales desde OMV con un plan de actualización aprobado; nunca automáticas con
reinicio. Antes: sync de SnapRAID y backup de AIO correctos. Después de un cambio de kernel:
`lsblk` con los tres discos SATA y `LnkSta` a 8GT/s.

| Componente | Cómo se actualiza | Qué comprobar después |
|---|---|---|
| Kernel y firmware de la Pi | OMV → Gestión de actualizaciones | `lsblk`, `lspci` JMB585, `LnkSta` 8GT/s |
| OpenMediaVault y plugins | OMV → Gestión de actualizaciones | `systemctl status openmediavault-engined`, plugins cargados |
| Nextcloud AIO | Automático tras el backup diario | Panel AIO: contenedores en marcha y backup correcto |
| SnapRAID, MergerFS, hd-idle, NUT | apt vía OMV | `snapraid status`, pool montado, `hdparm -C`, `upsc ups@localhost` |

## 11. Decisiones de arquitectura (ADR)

| ID | Decisión | Alternativas descartadas | Motivo | Requisito |
|---|---|---|---|---|
| ADR-001 | SnapRAID + MergerFS con ext4 por disco | RAID 5 mdadm, ZFS, Btrfs RAID | Discos distintos y viejos, poca RAM, spindown real, cada disco legible solo | NRD §5, §6 |
| ADR-002 | Sistema en SSD USB | Tarjeta SD | La SD falla antes, más con calor | NRD §6 |
| ADR-003 | WD Blue como paridad | Toshiba o QVO | Mecánico más sano y tamaño ≥ datos | NRD §5 |
| ADR-004 | Nextcloud AIO con datos en el SSD | NextcloudPi, datos en el pool | Rendimiento y discos dormidos | NRD §4 |
| ADR-005 | Tailscale para acceso exterior | Abrir 443 | Sin puertos abiertos | NRD §7 |
| ADR-006 | 24/7 con spindown | Apagado diario | Ciclos térmicos y humedad | NRD §6 |

## 12. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Actualización de kernel deja sin discos | Media | Alto | Overlay de 32 bits y comprobación tras cada kernel |
| Toshiba de portátil con desgaste de cabezales | Media | Medio | Vigilar atributo 193, APM 254, DCP preparado |
| Condensación por humedad | Baja | Alto | Ubicación fuera del suelo y lejos del aire acondicionado |
| Pool lleno antes de 3 años | Media | Medio | Revisión mensual de espacio y DCP para disco mayor |

## 13. Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-10 | Architect Agent | Creación |
