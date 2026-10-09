# HLD — NAS familiar con Raspberry Pi 5

| Campo | Valor |
|---|---|
| **Documento** | HLD |
| **Versión** | 1.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Architect Agent |
| **Entregable previo** | NRD v1 (1.3, Aprobado) — NRD-2026-10-08-nas-familiar.md |

## Resumen

Raspberry Pi 5 (8 GB) con OpenMediaVault 8 (OMV) arrancando desde un SSD NVMe en caja USB 3,
encendida 24/7. Dos niveles: el SSD guarda sistema, Docker, los datos internos de Nextcloud AIO
y la base de datos y miniaturas de Immich; un pool MergerFS de dos discos de 1 TB (Toshiba
MK1059 y Samsung QVO) guarda Documentos, Imágenes (incluidas las subidas de los móviles),
Vídeos y los backups de aplicaciones. SnapRAID protege el pool con el WD Blue de 1 TB como
paridad y sync diario a las 23:30. Un disco USB externo de 4 TB (el Hitachi de 320 GB queda
descartado), con burn-in SMART antes del primer uso y lectura SMART antes de cada copia, recibe
cada mes un backup restic con 12 versiones y vive fuera de casa entre copias.
Nextcloud e Immich solo se alcanzan desde fuera por Tailscale, y Tailscale se corta
automáticamente fuera del horario de uso (L-V 18:00-23:00, sábado y domingo 08:00-23:00).
Los discos mecánicos paran con hd-idle a los 45 min; una alarma SMART a 45 °C avisa por correo y
apaga el NAS si el calor se mantiene. La limpieza de fotos de Immich archiva en el álbum
"Revisar" y nunca borra.

## 1. Requisitos cubiertos

| Requisito (NRD) | Cómo se cubre | Sección del HLD |
|---|---|---|
| §1 Hitachi 320 GB descartado | Backup a disco USB externo de 4 TB nuevo | 2, 5, 7 |
| §1 Pi 4 futura: IP fija y SMB a Vídeos | Reserva DHCP en el router y usuario SMB `descargas` con escritura solo en Vídeos | 4, 6 |
| §2.1 Móviles: Cámara y WhatsApp a Immich | App Immich con copia de esos dos álbumes; biblioteca de subidas en `Imagenes/Moviles` del pool | 6 |
| §2.1 Limpieza automática que nunca borra | Tarea `immich-limpieza` con clave API sin permiso de borrado: añade al álbum "Revisar" y archiva | 6, 7 |
| §2.2 PC: sus Documentos e Imágenes completas | Cliente Nextcloud; montajes externos por persona; Imágenes compartida | 6 |
| §3 Capacidad a 3 años: 1 561 GB | Pool D1 + D2 de ~1 860 GB útiles (ext4, 2 × 931 GiB) | 5 |
| §3 Backup ~1 550 GB a 3 años + 12 versiones | Disco USB de 4 TB; cálculo de margen en §7 | 7 |
| §4 Samba | Recursos SMB por carpeta, sin invitados | 6 |
| §4 Nextcloud AIO, papelera y versiones ≥ 30 días | AIO con retención de papelera y versiones de 30 días; Documentos sin versiones nativas, cubiertos por papelera + SnapRAID + restic (riesgo aceptado, ADR-008) | 6, 7 |
| §4.1 Immich: biblioteca externa sin duplicar | Biblioteca externa = `Imagenes` excluyendo `Moviles/**` | 6 |
| §4.1 Primera clasificación y ML remoto | ML remoto en el PC de persona 1 (LAN) con la Pi de respaldo | 6, 9 |
| §4.1 Base de datos de Immich en restic | Volcado diario de la base de datos al pool; miniaturas en el SSD, excluidas | 6, 7 |
| §5 Fallo de un disco de datos, RPO 24 h | SnapRAID con sync diario a las 23:30 | 5, 7 |
| §5 Borrado accidental, umbral 50 | Umbral de 50 borrados en el sync, papelera de Nextcloud y Samba, restic | 5, 7 |
| §5 Ransomware, RPO 1 mes | restic mensual a USB desconectado, 12 versiones | 7 |
| §5 Desastre en casa | Disco USB guardado fuera de casa entre copias | 7 |
| §5 Fallo del SSD del sistema, RPO 24 h | Backup diario de AIO y volcado de Immich en el pool | 7 |
| §6 Ubicación, ruido, red por cable | Caja ventilada, ventilador 120 mm fijo, solo Ethernet | 2, 4 |
| §6 SAI con NUT, apagado a 5 min | NUT independiente, apagado a 300 s en batería | 9 |
| §6.1 Encendido 24/7, discos parados y sin acceso exterior fuera de horario | hd-idle 45 min; temporizadores systemd de Tailscale; tareas a las 23:00-01:00 | 4, 5, 9 |
| §6.1 Consumo estimado | ~9 W en reposo, ~17 W en uso, ~95 kWh/año | 9 |
| §6.2 Alarma SMART 45 °C, aviso y apagado | smartd con aviso a 40/45 °C; vigilante `nas-temp` que apaga tras 15 min ≥ 45 °C | 9 |
| §6.2 Ventilador activo | Ventilador 120 mm + Active Cooler | 2, 9 |
| §7 Nada expuesto; Tailscale; ningún puerto en el router | Puertos solo en la LAN y la tailnet | 4, 8 |
| §7 Secretos fuera del repo; restic fuera del NAS | Gestor de contraseñas con acceso de emergencia | 8 |
| §7.1 Compartición y acceso de emergencia | Cuentas de Nextcloud con montajes de solo lectura cruzados; hoja impresa | 6, 8 |
| §8 Actualizaciones mensuales con UPD | Política y tabla de componentes | 10 |
| §8 Revisión semanal, mensual, semestral y de verano | Calendario de tareas | 10 |

## 2. Hardware y montaje

| Pieza | Modelo | Función |
|---|---|---|
| Placa | Raspberry Pi 5 8 GB + Active Cooler | Servidor, Docker para Nextcloud AIO e Immich |
| Controladora | Radxa Penta SATA HAT (JMB585) + cable FFC | 4 SATA por PCIe Gen 3, sin RAID por hardware |
| Alimentación | Adaptador 12 V / 5 A al conector DC del HAT | Discos y Pi por el GPIO; USB-C de la Pi sin conectar |
| Sistema | Toshiba XG5 512 GB NVMe en caja USB 3 | Arranque, Docker, datos internos de Nextcloud, base de datos y miniaturas de Immich |
| Paridad | WD Blue 1 TB | Paridad de SnapRAID |
| Datos D1 | Toshiba MK1059 1 TB | Pool |
| Datos D2 | Samsung QVO 1 TB (SSD QLC) | Pool |
| Backup | Disco USB externo 4 TB (por comprar, ~100 €) | restic mensual; fuera de casa entre copias; burn-in SMART antes del primer uso |
| Caja | Impresa en PETG o ASA (nunca PLA) para el Penta SATA HAT | Soporte y canal de aire |
| Aire | Ventilador 120 mm a velocidad fija baja + filtro de polvo | Discos y HAT ≤ 40 °C con 35 °C de ambiente |
| SAI | Con USB compatible con NUT (por confirmar o comprar, 60–90 €) | Apagado limpio en cortes |
| Descartado | Hitachi 320 GB | No se usa (NRD §1) |

Bahías: 1 = WD Blue (paridad), 2 = vacía, 3 = Toshiba MK1059 (D1, la de más aire),
4 = Samsung QVO (D2, la de menos aire). Los dos mecánicos quedan separados por la bahía vacía
(guía §1). FFC con la cara negra hacia fuera y los dos pestillos cerrados. El NAS va en balda
alta y abierta, lejos del sol y del chorro del aire acondicionado, con el filtro en la entrada
de aire. La bahía 2 queda libre para una ampliación futura (riesgo "Pool lleno").

## 3. Sistema y arranque

Raspberry Pi OS Lite 64-bit (Trixie) grabado con Raspberry Pi Imager en el XG5: equipo `nas`,
usuario propio (no `pi`), SSH activado, sin WiFi y sin Raspberry Pi Connect. La Pi 5 arranca
desde USB sin tarjeta SD (orden de arranque de la EEPROM con USB primero; lo cambia el usuario).
Encima, OpenMediaVault 8 con omv-extras y los plugins: snapraid, mergerfs, compose (Docker),
sharerootfs y el de SMART incluido en OMV. Al final de `config.txt`, bajo `[all]`:

```
dtparam=pciex1
dtparam=pciex1_gen=3
dtoverlay=pcie-32bit-dma-pi5
usb_max_current_enable=1
```

`pcie-32bit-dma-pi5` evita que el JMB585 pierda los discos tras actualizar el kernel;
`usb_max_current_enable=1` da 1,6 A a la caja USB del SSD al alimentar por el HAT.

## 4. Red y puertos

Solo Ethernet al router. Reserva DHCP para `nas` y otra para la futura Pi 4 de descargas; las
IP concretas se anotan en el runbook de red. La web de OMV pasa al puerto 8000 para dejar el
80 a Nextcloud AIO. Nextcloud usa un dominio gratuito de deSEC cuyo registro apunta a la IP de
Tailscale del NAS, de modo que el mismo nombre funciona en casa y fuera con la app de Tailscale
activa (ADR-005). Ningún puerto se abre en el router: DuckDNS con puerto abierto y un reverse
proxy público (Caddy) quedan descartados (ADR-018); Caddy o `tailscale serve` solo se usarían
como proxy HTTPS interno.

Corte de Tailscale por horario (NRD §6.1, ADR-010): dos temporizadores systemd en el NAS.
`tailscale-on.timer` ejecuta `tailscale up` L-V a las 18:00 y sábado y domingo a las 08:00;
`tailscale-off.timer` ejecuta `tailscale down` todos los días a las 23:00. Un servicio de
arranque (`tailscale-horario.service`) aplica el estado que toca según la hora tras cualquier
reinicio, para que un corte de luz de madrugada no deje el acceso abierto. `tailscaled` sigue
corriendo y no pierde el registro del equipo; en la red de casa Samba, Nextcloud e Immich
siguen disponibles por la IP local. Vuelta atrás: desactivar los temporizadores y `tailscale up`.

| Puerto | Servicio | Expuesto a Internet |
|---|---|---|
| 22 | SSH (LAN) | No |
| 8000 | Panel de OMV (LAN) | No |
| 8080 | Panel de AIO (LAN, siempre por IP) | No |
| 80, 443, 8443 | Nextcloud AIO (LAN y Tailscale) | No |
| 2283 | Immich (LAN y Tailscale) | No |
| 445 | Samba (LAN) | No |
| 3493 | NUT (solo localhost) | No |
| 3003 | ML remoto de Immich en el PC de persona 1 (LAN, solo durante la clasificación) | No |
| 41641/udp | Tailscale (conexión saliente) | No |

## 5. Almacenamiento

| Rol | Disco | Tamaño | Conexión | Sistema de ficheros | Montaje | En pool | Content |
|---|---|---|---|---|---|---|---|
| Sistema | Toshiba XG5 NVMe | 512 GB | USB 3 (caja) | ext4 | / | No | Sí |
| Paridad | WD Blue | 1 TB | SATA bahía 1 | ext4 (0 % reservado) | /srv/dev-disk-by-uuid-… (parity) | No | No |
| D1 | Toshiba MK1059 | 1 TB | SATA bahía 3 | ext4 (0 % reservado) | /srv/dev-disk-by-uuid-… (d1) | Sí | Sí |
| D2 | Samsung QVO | 1 TB | SATA bahía 4 | ext4 (0 % reservado) | /srv/dev-disk-by-uuid-… (d2) | Sí | Sí |
| Backup | Disco USB externo | 4 TB | USB 3, desconectado (SMART con `smartctl -d sat`) | ext4, etiqueta `backup` | /mnt/backup (solo durante la copia) | No | No |

Los UUID reales se anotan al formatear y en `state/config/`. Los tamaños son los nominales del
NRD: el NAS no respondía por SSH al escribir este HLD, así que no se han verificado con
`lsblk -b`. El runbook de discos compara los bytes de los tres discos antes de formatear: si el
WD Blue tiene menos bytes que el Toshiba o el QVO, para y vuelve al arquitecto (riesgo en §12).

### SnapRAID

| Parámetro | Valor |
|---|---|
| Array | `nas` |
| Paridades | 1 (WD Blue, fichero `snapraid.parity`) |
| Content files | 3 (d1, d2 y el SSD del sistema en `/var/snapraid/`) |
| Exclusiones | `*.unrecoverable`, `/lost+found/`, `/tmp/`, `.Trash-*/`, `.recycle/`, `Imagenes/.immich-tmp/` |
| Sync | Diario a las 23:30 con diff previo, tras el volcado de Immich y el backup de AIO |
| Umbral de borrados | No sincronizar si hay más de 50 borrados; aviso por correo y sync manual tras revisar |
| Scrub | Domingo tras el sync, 12 % de los bloques con más de 10 días |
| Avisos | Informe de cada sync y scrub por correo |

### MergerFS

| Parámetro | Valor |
|---|---|
| Nombre | `pool` en `/srv/mergerfs/pool` |
| Ramas | D1 y D2 (nunca la paridad) |
| Política de creación | `mfs` (el de más espacio libre) |
| Espacio libre mínimo | 20G |
| Opciones | `cache.files=off`, `dropcacheonclose=true`, `category.search=ff` |

## 6. Servicios y carpetas

**Samba**: un recurso por carpeta del pool, sin invitados, con papelera `.recycle` (30 días) y
`force user`/`force group` = `www-data` en Documentos e Imágenes para que Nextcloud gestione lo
que llega por SMB. Usuarios OMV: `persona1`, `persona2` (grupo `familia`) y `descargas` para la
futura Pi 4, con escritura solo en `Videos`.

**Nextcloud AIO** (Docker vía plugin compose): `NEXTCLOUD_DATADIR` en `ncdata` del SSD (datos
internos, vistas previas y ficheros sueltos), `NEXTCLOUD_MOUNT=/srv/mergerfs/pool`, límite de
subida 16G, solo el contenedor Imaginary. Documentos e Imágenes del pool entran como
almacenamiento externo de tipo Local, con "Comprobar cambios: una vez por acceso directo":

- `Documentos/persona1` montado en lectura y escritura para persona 1 y en **solo lectura** para
  persona 2 (otro montaje de la misma ruta con la opción de solo lectura); igual a la inversa.
- `Imagenes` montado en lectura y escritura para el grupo `familia`.
- Papelera con retención de 30 días (`trashbin_retention_obligation = 30, 35`) y versiones con
  `versions_retention_obligation = 30, auto` (ADR-008).
- Backup diario de AIO a las 23:05 en `Archivo/nextcloud-aio-backup` del pool, con
  actualización automática de contenedores tras el backup.

**Cliente de escritorio** en los 2 PC: sincroniza completa la carpeta de Documentos propia y
todo Imágenes en D:; los Documentos del otro se consultan por la web, sin sincronizar.

**Immich** (Docker vía plugin compose, en un fichero aparte de AIO; ADR-011):

- `UPLOAD_LOCATION` en el SSD (`/srv/immich` sobre el sistema de archivos raíz): miniaturas,
  vídeos recodificados y temporales.
- La subcarpeta `library` del contenedor se monta en `/srv/mergerfs/pool/Imagenes/Moviles`: las
  subidas de los móviles quedan en el pool, dentro de Imágenes, y Nextcloud las sincroniza a los
  PC. Plantilla de almacenamiento `{{y}}/{{MM}}` por etiqueta de usuario
  (`Moviles/persona1/2026/10`).
- La subcarpeta `backups` se monta en `/srv/mergerfs/pool/Archivo/immich-db`: volcado diario de
  PostgreSQL a las 23:00, 14 copias.
- Biblioteca externa = `/srv/mergerfs/pool/Imagenes` en solo lectura con exclusión `Moviles/**`
  (las subidas ya son de Immich) y `**/.recycle/**`: sin duplicar fotos (NRD §4.1).
- Búsqueda inteligente (CLIP) y caras activas. Primera clasificación con ML remoto en el PC de
  persona 1 (contenedor `immich-machine-learning`, puerto 3003, solo LAN) y la Pi como URL de
  respaldo; concurrencia de trabajos a 1 en la Pi. Tras la primera clasificación se retira el ML
  remoto y la Pi procesa las fotos nuevas (ADR-012).
- Tareas nocturnas de Immich a las 00:00.
- Móviles: app Immich con copia en segundo plano solo de los álbumes Cámara y WhatsApp, URL de
  casa (IP local) y URL externa (Tailscale) configuradas.

**Limpieza `immich-limpieza`** (ADR-013): script en el NAS con temporizador systemd diario a las
00:30. Usa la API de Immich con una clave de API propia **sin el permiso `asset.delete`** (solo
lectura de recursos, actualización de recursos y de álbumes). Por cada consulta de búsqueda
inteligente ("meme", "plato de comida", "captura de pantalla") toma los resultados por encima
del umbral de similitud fijado en el runbook, más las imágenes con nombre `Screenshot*`, los
añade al álbum "Revisar" y los archiva (visibilidad Archivo). Escribe un registro con los ID
movidos para poder deshacerlo. Nunca llama a borrar; el usuario revisa y borra a mano. Cubre
también las fotos de WhatsApp antiguas de la biblioteca externa.

**Otros**: hd-idle, NUT, smartd con avisos por correo (Gmail con contraseña de aplicación en el
gestor de contraseñas), y los temporizadores `tailscale-on/off` y `nas-temp`.

| Carpeta | Ubicación | Grupo familia | Backup offline |
|---|---|---|---|
| Documentos/persona1, Documentos/persona2 | pool (www-data) | Dueño lectura y escritura; el otro solo lectura | Sí |
| Imagenes (incluye `Moviles/`) | pool (www-data) | Lectura y escritura | Sí |
| Videos | pool | Lectura; escritura solo `descargas` | No |
| Archivo/nextcloud-aio-backup | pool | Sin acceso | Sí |
| Archivo/immich-db | pool | Sin acceso | Sí |
| compose, ncdata, /srv/immich | SSD del sistema | Sin acceso | ncdata vía backup de AIO; miniaturas no (se regeneran) |

## 7. Protección de datos y backups

Programación nocturna (NRD §6.1, sin solapes): 23:00 volcado de Immich → 23:05 backup de AIO
(~10 min) → 23:30 diff + sync de SnapRAID → 00:00 tareas de Immich → 00:30 limpieza. Domingo,
scrub tras el sync.

restic mensual (primer sábado de mes, en horario de uso): el usuario trae el disco USB, lo
conecta y lo monta; el agente lee antes su SMART (ver "Salud del disco de backup") y, si está
bien, lanza `restic backup` de `Documentos`, `Imagenes`, `Archivo` con exclusión de `Videos`,
después `restic check --read-data-subset=5%`; la retención (12
mensuales) la aplica el usuario porque `forget/prune` está bloqueado al agente. Después el disco
se desmonta y vuelve fuera de casa.

Margen del disco: ~1 200 GB hoy y ~1 550 GB a 3 años; las 12 versiones mensuales añaden lo
cambiado en un año (~115 GB). A 3 años: ~1 665 GB sobre ~3 600 GB útiles de un disco de 4 TB
(≈ 46 %), con holgura para 5+ años y para más versiones (ADR-017).

**Salud del disco de backup** (ADR-017). La caja USB necesita `smartctl -d sat` (si la caja no
pasa SMART, se cambia de caja antes del primer uso):

- Burn-in antes del primer uso: `smartctl -d sat -t long` (varias horas en 4 TB) y
  `smartctl -d sat -a` con el test `Completed without error` y 5/187/197/198/199 a 0. Si falla,
  se devuelve el disco.
- Antes de cada backup mensual: `smartctl -d sat -H -A` y comprobar 5, 187, 197, 198, 199 y
  temperatura. Si el estado no es PASSED, si alguno de 5/187/197/198 es distinto de 0 o ha subido
  desde la copia anterior, si 199 sube, o si la temperatura supera 45 °C, se **aborta** sin
  escribir y se avisa (sustitución del disco: experto en discos). Los valores se anotan en el OPS
  para ver la tendencia.
- Tras cada backup: `restic check --read-data-subset=5%` (parcial, lee un 5 % de los datos
  distinto cada mes); si falla, no se aplica la retención y se revisa antes de la siguiente copia.

| Escenario (NRD) | Mecanismo | RPO resultante | Cómo se recupera |
|---|---|---|---|
| Fallo de un disco de datos | SnapRAID | 24 h | Disco nuevo en el mismo montaje + `snapraid -d dN fix` (DCP) |
| Fallo del disco de paridad | SnapRAID | 0 | Disco nuevo ≥ 1 TB + sync completo (DCP) |
| Borrado accidental | Umbral de 50 borrados, papelera de Nextcloud 30 días, `.recycle` de Samba, SnapRAID hasta el sync, restic | 24 h | Papelera, `snapraid fix -f` o `restic restore` |
| Ransomware o cifrado | restic al disco USB desconectado, 12 versiones | 1 mes | `restic restore` a carpeta nueva y resincronizar los PC |
| Error de la limpieza de Immich | Solo archiva y añade a "Revisar"; clave API sin borrado; registro de ID | 0 | Quitar del álbum y desarchivar |
| Pérdida de la base de datos de Immich | Volcado diario al pool + restic | 24 h (pool) / 1 mes (USB) | Restaurar el volcado en un Immich nuevo |
| Rayo, robo o inundación | Disco USB de backup fuera de casa (restic) | 1 mes | Restauración en un NAS nuevo según los RBK |
| Fallo del SSD del sistema | Backup diario de AIO y volcado de Immich en el pool | 24 h | Reinstalar según RBK, restaurar AIO e Immich; miniaturas se regeneran |

## 8. Seguridad

- Nunca se exponen a Internet el panel de OMV (8000), el de AIO (8080) ni SSH (22).
- Ningún puerto abierto en el router; acceso exterior solo a Nextcloud e Immich y por Tailscale,
  cortado fuera del horario de uso. Sin DuckDNS, sin 443 abierto y sin reverse proxy público
  (ADR-018).
- Usuario propio en la Pi (no `pi`); contraseña del `admin` de OMV cambiada en el primer acceso
  por el usuario.
- Un usuario por persona en OMV, Nextcloud e Immich; grupo `familia`; sin invitados en Samba.
  `descargas` solo escribe en Videos.
- ML remoto de Immich solo en la LAN; el contenedor del PC se para tras la clasificación.
- La clave de API de la limpieza no tiene permiso de borrado; se guarda en un fichero del NAS
  legible solo por root, no en el repo.
- Secretos (OMV, AIO y su frase de acceso, restic, Immich, Gmail, Tailscale) en el gestor de
  contraseñas, nunca en el repo; la contraseña de restic, además, fuera del NAS y con acceso de
  emergencia a favor de persona 2.
- Hoja impresa sin contraseñas para persona 2: cómo entrar en Nextcloud y descargar, y cómo leer
  el disco USB con restic.

## 9. Energía y temperatura

**SAI**: NUT en modo independiente, apagado limpio tras 300 s en batería y aviso por correo. El
corte de Tailscale no afecta a NUT (es local). Mientras no haya SAI (pregunta abierta), un corte
de luz es un apagado sucio: riesgo en §12.

**Spindown**: hd-idle con `-i 0` por defecto y 2 700 s (45 min) para el WD Blue y el Toshiba;
spindown de OMV desactivado; el QVO no se para. APM 254 en el Toshiba si el atributo 193 sube
más de 100 al día. Fuera de horario los mecánicos solo despiertan en la ventana 23:00-01:00 y
si un PC encendido consulta Nextcloud (riesgo en §12).

**Consumo estimado** (NRD §6.1): reposo con mecánicos parados ~9 W (Pi 5 ~3,5 W, SSD y HAT
~2 W, QVO ~0,5 W, dos HDD en standby ~1 W, ventilador ~1 W, pérdidas del adaptador ~1 W); en uso
~17 W (dos HDD girando ~7 W más). Con ~40 h/semana de uso: ~95 kWh/año.

**Temperatura** (NRD §6.2, ADR-014): objetivos Pi < 70 °C, `get_throttled` = 0x0, discos
25–40 °C.

- smartd (vigilancia SMART de OMV) cada 30 min con `-n standby` (no despierta discos): aviso por
  correo a 40 °C y alarma crítica a 45 °C.
- Vigilante `nas-temp` (temporizador systemd cada 5 min, `smartctl -n standby -A`): si un disco
  marca ≥ 45 °C en 3 lecturas seguidas (15 min) o ≥ 50 °C en una, envía correo y ejecuta un
  apagado limpio (`systemctl poweroff`). Si la Pi supera 80 °C, correo.
- Ventilador 120 mm fijo bajo + Active Cooler; filtro limpio cada mes.
- Primera ejecución de Immich: si los discos superan 40 °C durante la clasificación, se pausa y
  se sigue en horario de uso.

## 10. Actualizaciones y mantenimiento

Mensuales y manuales desde OMV con un plan de actualización (UPD) aprobado; nunca automáticas
con reinicio. Ventana: sábado por la mañana (en horario de uso, lejos de las tareas de
23:00-01:00). Antes: `snapraid status` sin errores, backup de AIO y volcado de Immich de esa
noche correctos. Después de un cambio de kernel o firmware: `lsblk` con los tres discos SATA y
`LnkSta` a 8GT/s. Immich se actualiza a mano con su UPD leyendo las notas de versión (cambios
incompatibles frecuentes); AIO se actualiza solo tras su backup.

Calendario: semanal (correo de SnapRAID y backup de AIO), mensual (SMART del disco de backup + restic + check, filtro,
SMART 5/197/198/193 y temperatura), semestral (restauración de prueba, prueba del SAI, prueba de
acceso de persona 2), verano (alarmas de 45 °C del periodo e higrómetro).

| Componente | Cómo se actualiza | Qué comprobar después |
|---|---|---|
| Kernel y firmware de la Pi | OMV → Gestión de actualizaciones | `lsblk`, `lspci` JMB585, `LnkSta` 8GT/s, `get_throttled` |
| OpenMediaVault y plugins | OMV → Gestión de actualizaciones | `systemctl status openmediavault-engined`, plugins cargados |
| Nextcloud AIO | Automático tras el backup diario | Panel AIO: contenedores en marcha y backup correcto |
| Immich | Manual con UPD: nueva etiqueta en el compose | Contenedores sanos, biblioteca externa visible, subida de prueba desde un móvil, `immich-limpieza` sin errores |
| SnapRAID, MergerFS, hd-idle, NUT, smartd | apt vía OMV | `snapraid status`, pool montado, `hdparm -C`, `upsc ups@localhost`, correo de prueba |
| Tailscale | apt (repositorio de Tailscale) | `tailscale status`, temporizadores activos |
| restic | apt | `restic version`, `restic snapshots` con el disco conectado |

## 11. Decisiones de arquitectura (ADR)

| ID | Decisión | Alternativas descartadas | Motivo | Requisito |
|---|---|---|---|---|
| ADR-001 | SnapRAID + MergerFS con ext4 por disco | RAID 5 mdadm, ZFS, Btrfs RAID | Discos distintos y usados, 8 GB de RAM, spindown real, cada disco legible por separado | NRD §5, §6.1 |
| ADR-002 | Sistema en SSD NVMe por USB | Tarjeta SD | La SD falla antes, más con calor y escrituras de Docker | NRD §6 |
| ADR-003 | WD Blue como paridad (sujeto a `lsblk -b`) | Toshiba MK1059 o QVO como paridad | Mecánico de sobremesa más sano; el QVO rinde mejor como datos; tamaño igual al de los datos | NRD §5 |
| ADR-004 | Backup a disco USB externo nuevo (4 TB, ver ADR-017) | Hitachi 320 GB; nube | El Hitachi no cabe 1,2 TB y da problemas; nube descartada por el usuario | NRD §1, §6 |
| ADR-005 | Tailscale con dominio deSEC apuntando a la IP de Tailscale | Abrir 443; Cloudflare Tunnel; solo IP de Tailscale sin dominio | Sin puertos abiertos; certificado válido para el cliente de Nextcloud; mismo nombre dentro y fuera | NRD §7 |
| ADR-006 | 24/7 con spindown hd-idle a 45 min | Apagado diario por RTC | Decisión del usuario; menos ciclos térmicos y condensación | NRD §6.1 |
| ADR-007 | Documentos e Imágenes en el pool como almacenamiento externo de Nextcloud; datos internos en el SSD | Todo el `ncdata` en el pool; Documentos en el SSD | 966 GB no caben en el SSD de 512 GB; con `ncdata` en el pool los trabajos de Nextcloud cada 5 min despertarían los discos | NRD §2.2, §3, §6.1 |
| ADR-008 | Papelera de 30 días en Nextcloud; versiones cubiertas por papelera + SnapRAID + restic donde el almacenamiento externo no guarde versiones | Mover Documentos a `ncdata` en el pool para tener versiones nativas | Nextcloud no conserva versiones en almacenamiento externo Local de forma fiable; la alternativa rompe el spindown (ADR-007). Riesgo aceptado por el usuario el 2026-10-09 (opción a) | NRD §4 |
| ADR-009 | Compartición con montajes externos duplicados (lectura y escritura para el dueño, solo lectura para el otro) | Compartir carpetas desde la cuenta del dueño; cuenta de emergencia | El permiso lo fija el admin y no depende de que el dueño comparta; persona 2 ve todo sin conocimientos técnicos | NRD §7.1 |
| ADR-010 | Corte de Tailscale con temporizadores systemd `tailscale up/down` y servicio de arranque | ACL de Tailscale por horario; parar `tailscaled`; cortafuegos | Las ACL no tienen horario; `down` conserva el registro; el servicio de arranque cubre reinicios | NRD §6.1, §7 |
| ADR-011 | Immich en Docker aparte de AIO; `library` en `Imagenes/Moviles` del pool; miniaturas y base de datos en el SSD | Subir fotos con la app de Nextcloud; todo Immich en el pool; Immich como contenedor comunitario de AIO | Subidas en el pool y sincronizadas a los PC; miniaturas rápidas en SSD sin despertar discos; actualizaciones de Immich controladas por UPD | NRD §2.1, §4.1 |
| ADR-012 | Primera clasificación con ML remoto en el PC (LAN) y la Pi de respaldo; después solo la Pi | Solo la Pi; trocear por horario | En la Pi tardaría días con los discos girando fuera de horario y más calor; el PC lo hace en horas | NRD §4.1, §6.1, §6.2 |
| ADR-013 | Limpieza por API con clave sin permiso de borrado: álbum "Revisar" + archivar | Borrado automático; mover ficheros en disco; limpieza manual | Garantiza por permisos que nunca borra; no toca rutas que sincroniza Nextcloud; reversible con el registro | NRD §2.1, §5 |
| ADR-014 | Alarma SMART 45 °C con smartd + vigilante que apaga tras 15 min ≥ 45 °C o una lectura ≥ 50 °C | Solo aviso; control de ventilador por temperatura | Requisito de apagado si se mantiene; ventilador fijo por ruido (NRD §6) | NRD §6.2 |
| ADR-015 | Tareas programadas en 23:00-01:00 encadenadas | Madrugada (03:00-04:00 de la guía) | No despertar los discos de madrugada; sin solapes con el backup de AIO | NRD §6.1, §8 |
| ADR-016 | Política `mfs` con 20G libres | `epmfs` (mantener rutas en un disco) | Reparte el llenado entre D1 y D2; con `epmfs` Imágenes llenaría un disco a 3 años | NRD §3 |
| ADR-017 | Disco de backup USB de 4 TB con burn-in SMART largo, SMART (5/187/197/198/199 y temperatura, `-d sat`) antes de cada copia con aborto si hay errores, y `restic check --read-data-subset` tras cada copia. Concreta ADR-004 | 2 TB (60–80 €, ~90 % a 3 años); copiar sin leer SMART | Decisión del usuario: holgura para 5+ años; un disco que vive fuera y se usa una vez al mes debe probarse antes de confiarle la única copia offline | NRD §3, §5 |
| ADR-018 | Acceso exterior solo por Tailscale; descartados DuckDNS + puerto abierto, abrir 443 y reverse proxy público (Caddy). Caddy o `tailscale serve` solo como proxy HTTPS interno (LAN/tailnet) cuando un servicio sin HTTPS propio lo necesite. Refuerza ADR-005 | DuckDNS con puerto abierto (usado por el usuario en el pasado); Caddy expuesto en 443 | El usuario lo usó y lo descarta; cualquier puerto abierto expone Nextcloud e Immich a Internet; Tailscale cumple sin abrir nada | NRD §7 |

## 12. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Tamaños sin verificar con lsblk (WD Blue con menos bytes que un disco de datos) | Baja | Alto | Verificar `lsblk -b` en el runbook de discos antes de formatear; si falla, volver al HLD |
| Actualización de kernel deja sin discos | Media | Alto | Overlay `pcie-32bit-dma-pi5` y comprobación tras cada kernel |
| Calor de verano (35 °C ambiente) lleva discos a > 40 °C | Media | Alto | Ventilador, alarma 45 °C, apagado automático, revisión de verano |
| Condensación por 90 % HR | Baja | Alto | Ubicación alta y ventilada, 24/7 sin ciclos de frío, higrómetro |
| Toshiba de portátil con desgaste de cabezales | Media | Medio | Vigilar atributo 193, APM 254, DCP preparado |
| Disco de backup defectuoso o degradándose sin aviso | Baja | Alto | Burn-in SMART largo antes del primer uso; SMART antes de cada copia con aborto; `restic check` parcial tras cada copia (ADR-017) |
| Disco de backup lleno | Baja | Medio | 4 TB (~46 % a 3 años); revisión mensual del tamaño del repositorio |
| Sin SAI: corte de luz = apagado sucio | Media | Medio | Comprar SAI (pregunta abierta); ext4 con journal; SnapRAID `check` tras corte |
| Sin versiones de Nextcloud en Documentos externos (riesgo aceptado por el usuario, ADR-008) | Alta | Medio | Papelera 30 días, SnapRAID (24 h) y restic mensual |
| PC encendido de noche mantiene despiertos los discos | Media | Bajo | Comprobar `hdparm -C` y registro de hd-idle en la revisión semanal; pausar el cliente de noche |
| Ransomware propagado a los D: de los PC | Baja | Alto | restic offline mensual; papelera de Nextcloud como primer recurso |
| Pool lleno antes de 5 años | Media | Medio | Revisión mensual de espacio; bahía 2 libre y DCP para disco mayor |
| Un único disco de backup sin copia fuera de casa durante la copia | Baja | Alto | Copia en el día; mejora futura con segundo disco rotatorio |

### Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Hay SAI con USB compatible con NUT? (NRD) | Persona 1 | 2026-10-31 |
| ¿Modelo del router? Pendiente de que lo indique el usuario; con él se decide si permite DNS local para el dominio de Nextcloud (uso en casa sin Tailscale activo) y la reserva DHCP | Persona 1 | 2026-10-31 |
| ¿Umbral de similitud de la búsqueda inteligente para la limpieza? Se fija con una prueba sobre 200 fotos en el runbook de Immich | Persona 1 | Runbook de Immich |
| ¿Cuota para Vídeos cuando exista la Pi 4? (MergerFS no tiene cuotas; se propone vigilar el espacio y fijar un máximo en el proyecto futuro) | Persona 1 | Proyecto Pi 4 |

## 13. Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Architect Agent | Creación |
| 1.1 | 2026-10-09 | Architect Agent | Decisiones del usuario: disco de backup de 4 TB con salud SMART y `restic check` (ADR-017); Documentos sin versiones nativas como riesgo aceptado (ADR-008); DuckDNS/puerto abierto/Caddy público descartados (ADR-018); modelo del router queda abierto |
| 1.1 | 2026-10-09 | Architect Agent | Estado cambiado a Aprobado |
