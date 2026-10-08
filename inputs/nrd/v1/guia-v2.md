# NAS Raspberry Pi 5 — Guía de instalación v2

> Transcripción de `guia-v2.pdf` (2 oct. 2026) para que la lean los agentes.
> Los marcadores `[Captura X.Y]` y `[Foto X.Y]` son capturas pendientes.

## Qué cambia respecto a la v1

La v2 sustituye NextcloudPi y el RAID mdadm + LVM + Btrfs por Raspberry Pi OS con
OpenMediaVault 8, SnapRAID y MergerFS: pensado para discos viejos y distintos, poca RAM,
standby real y clima tropical.

| Tema | v1 (2020) | v2 (2026) | Por qué |
|---|---|---|---|
| Placa y discos | Raspberry Pi + hub USB | Raspberry Pi 5 + HAT Radxa Penta SATA (PCIe) | SATA directo, sin el cuello de botella del hub |
| Arranque | Tarjeta SD | SSD Toshiba XG5 por USB | La SD es el primer punto de fallo, y el calor lo acelera |
| Sistema | Imagen NextcloudPi | Raspberry Pi OS Lite 64-bit (Trixie) + OpenMediaVault 8 | NAS completo con interfaz web y kernel oficial de la Pi |
| Protección de datos | Particiones a medida, RAID 5 + RAID 1, LVM y Btrfs | SnapRAID (1 disco de paridad) + MergerFS, ext4 por disco | Aprovecha discos distintos; si fallan dos, solo se pierde lo de esos dos |
| Red | WiFi + IP fija en dhcpcd.conf | Solo Ethernet + reserva DHCP en el router | Trixie ya no usa dhcpcd, y un servidor va por cable |
| Acceso al sistema | PuTTY con usuario pi | `ssh` (incluido en Windows 10/11) con usuario propio | El usuario pi por defecto ya no existe |
| Sincronizar PC y móviles | Cliente Nextcloud | Nextcloud AIO: cliente en los PC y app en los móviles | Un solo sistema; con 8 GB de RAM hay margen |
| Backups | Snapshots y copias en el mismo RAID | Backup diario de Nextcloud AIO + restic al Hitachi desconectado + copia fuera de casa | Una copia en los mismos discos no protege de rayo, robo ni ransomware |
| Horario | Apagado diario por cron | Encendido 24/7 con spindown a 30-45 min | Con humedad, apagar y encender a diario daña más |
| Correo de avisos | Gmail con "aplicaciones menos seguras" | Gmail con contraseña de aplicación | Google ya no permite la primera opción |
| Alimentación | Sin protección | SAI con USB + NUT | Apagado limpio en cortes de luz |
| Acceso exterior | DynHost OVH + puerto 443 abierto | Dominio con certificado sin abrir puertos; desde fuera, Tailscale o solo Nextcloud publicado (opcional) | No exponer el panel del NAS a Internet |

Se mantiene de la v1: ext4 como sistema de ficheros de los datos, vigilancia SMART con aviso
por correo y actualizaciones automáticas de seguridad.

## Arquitectura

Dos niveles: el SSD recibe el trabajo diario y el pool de discos guarda el archivo, protegido
por paridad diaria, un backup mensual offline y una copia fuera de casa.

```
PC y móviles de la familia ──Nextcloud──▶ SSD XG5 512 GB · nivel caliente
                           ──Samba y fotos del móvil──▶ Pool MergerFS ~2 TB · nivel frío
SAI con NUT ──12 V + USB──▶ NAS

NAS · Raspberry Pi 5 + OMV 8
├── SSD XG5 512 GB (nivel caliente): sistema, Docker y Nextcloud AIO; datos de Nextcloud
│   (lo que se edita); copia del content de SnapRAID; siempre activo, sin partes móviles
├── Servicios de OMV 8: Samba y Nextcloud AIO (Docker); SnapRAID, MergerFS y hd-idle;
│   SMART y avisos por correo
├── Pool MergerFS ~2 TB (nivel frío): D1 Toshiba 1 TB + D2 QVO 1 TB (SSD)
└── Paridad WD Blue 1 TB: SnapRAID sync diario a las 04:00; scrub semanal del 12 %;
    tamaño igual o mayor que cada disco
Backup mensual ──▶ Hitachi 320 GB offline: restic mensual, 12 versiones; desconectado,
                   en otra habitación
Tercera copia ──▶ Copia fuera de casa: disco rotado o nube, con restic; solo Documentos y Fotos
```

Los discos del pool solo despiertan cuando alguien lee o escribe en ellos, y durante el sync
nocturno.

## 1. Material y montaje

Tres discos de 1 TB en el HAT, una bahía libre para el aire, el sistema en un SSD USB y un solo
adaptador de 12 V para todo.

| Pieza | Modelo | Función |
|---|---|---|
| Placa | Raspberry Pi 5 + Active Cooler oficial | Servidor, 8 GB de RAM |
| Controladora | Radxa Penta SATA HAT (JMB585) + cable FFC | 4 SATA por PCIe, sin RAID por hardware |
| Alimentación | Adaptador 12 V / 5 A al conector DC del HAT (5,5 × 2,5 mm, centro positivo) | Alimenta los discos y la Pi por el GPIO |
| Sistema | Toshiba XG5 512 GB (NVMe) en caja USB 3 | Sistema, Docker y datos de Nextcloud |
| Paridad | WD Blue 1 TB | Paridad de SnapRAID |
| Datos D1 | Toshiba MK1059 1 TB | Datos del pool |
| Datos D2 | Samsung QVO 1 TB (SSD QLC) | Datos del pool |
| Backup | Hitachi 320 GB en caja USB | Copia offline, guardada fuera de la habitación del NAS |
| Caja | Impresa en 3D en PETG o ASA, nunca PLA | Diseños para este HAT: Michael Klements (MakerWorld), Patrick Friedel (Printables) |
| Aire | Ventilador de 120 mm a baja velocidad + filtro de polvo | Refrigeración de discos y HAT |
| SAI | Con puerto USB compatible con NUT | Apagado limpio en cortes de luz |
| Red | Cable Ethernet al router | Sin WiFi |

### Colocación de los discos

1. Separa los dos discos mecánicos (WD y Toshiba) con la bahía vacía entre ellos.
2. Pon el Toshiba en la posición que reciba más aire: es el que más calienta.
3. Pon el QVO en la posición con menos aire: un SSD apenas calienta.
4. Conecta el FFC con la cara negra hacia ti y cierra bien los dos pestillos.

[Foto 1.1: HAT con los tres discos en sus bahías y la bahía libre]

### Ubicación en casa

- Ni en el suelo, ni dentro de un mueble cerrado, ni bajo el chorro del aire acondicionado:
  superficie fría y aire húmedo condensan.
- El filtro va en la entrada de aire; límpialo una vez al mes.
- Objetivo térmico: discos entre 25 y 40 °C (alarma a 45 °C) y `vcgencmd get_throttled` igual a `0x0`.

[Foto 1.2: NAS montado en su sitio definitivo, con el ventilador y el filtro]

## 2. Grabar el sistema en el SSD

El sistema va en el SSD XG5, grabado desde tu PC con Raspberry Pi Imager 2: ya no hacen falta
GParted, Etcher ni ficheros `ssh` y `wpa_supplicant.conf`.

1. Instala Raspberry Pi Imager 2.x. Las versiones 1.x no ofrecen la imagen basada en Trixie.
   En Linux, la AppImage puede necesitar el paquete `libfuse2t64`.
2. Conecta el XG5 a tu PC con su caja USB.
3. En el asistente elige: Dispositivo → **Raspberry Pi 5**; Sistema → **Raspberry Pi OS (other)
   → Raspberry Pi OS Lite (64-bit)**; Almacenamiento → el XG5. Comprueba el tamaño (~512 GB)
   para no borrar otro disco.
4. En la personalización rellena:
   - Nombre del equipo: `nas`
   - Zona horaria y teclado: los tuyos
   - Usuario y contraseña: uno propio, no `pi` (ya no existe usuario por defecto)
   - WiFi: **vacío**. Un servidor va por cable, y el instalador de OMV puede romper la configuración WiFi.
   - Acceso remoto: **activar SSH** con contraseña
   - Raspberry Pi Connect: desactivado
5. Pulsa Escribir y espera a la verificación.

[Captura 2.1: Imager con Raspberry Pi 5, Raspberry Pi OS Lite (64-bit) y el XG5 seleccionados]

[Captura 2.2: pantalla de personalización con nombre `nas`, usuario y SSH activado]

Si en el primer arranque no puedes entrar por SSH, puede que la personalización no se aplicara.
Es un fallo conocido de algunas versiones 2.0.x: vuelve a grabar con la versión más reciente.

## 3. Primer arranque

Antes de arrancar se añaden cuatro líneas a `config.txt` desde el PC; después se valida sistema
y red sin discos, y solo al final se conectan.

### 3.1 config.txt, todavía en el PC

Con el XG5 aún conectado al PC, abre la partición `bootfs` y añade al final de `config.txt`,
debajo de la última línea `[all]`:

```
dtparam=pciex1
dtparam=pciex1_gen=3
dtoverlay=pcie-32bit-dma-pi5
usb_max_current_enable=1
```

| Línea | Para qué |
|---|---|
| `dtparam=pciex1` | Activa el conector PCIe donde va el HAT |
| `dtparam=pciex1_gen=3` | PCIe Gen 3: el JMB585 lo aprovecha |
| `dtoverlay=pcie-32bit-dma-pi5` | Necesario desde el cambio de kernel ee95f3c: sin él, los discos desaparecen tras una actualización (Radxa) |
| `usb_max_current_enable=1` | Alimentada por el GPIO, la Pi limita el USB a 600 mA y el SSD puede no arrancar (Radxa foro) |

Con el overlay de 32 bits ya no hace falta congelar el kernel. Tras cada actualización de
kernel, comprueba con `lsblk` que siguen los discos.

[Captura 3.1: config.txt con las cuatro líneas añadidas]

### 3.2 Arrancar sin discos

1. Conecta el XG5 a un puerto USB 3 (azul) de la Pi y el cable Ethernet. Los discos SATA,
   todavía desconectados.
2. Alimenta solo por el conector de 12 V del HAT. No conectes a la vez el USB-C de la Pi.
3. La Pi 5 arranca desde USB sin tarjeta SD: su orden de arranque por defecto ya incluye USB.
4. En el router, busca el equipo `nas` y crea una **reserva DHCP** (por ejemplo 192.168.1.200).
   Sustituye al `dhcpcd.conf` de la v1.
5. Desde tu PC: `ssh tu_usuario@nas.local` (o la IP reservada).

[Captura 3.2: router con la reserva DHCP del equipo nas]

### 3.3 Actualizar y comprobar el HAT

```
sudo apt update && sudo apt full-upgrade -y && sudo reboot
```

Tras el reinicio, comprueba que el JMB585 aparece y negocia Gen 3 (debe decir `Speed 8GT/s`):

```
lspci | grep -i jmicron
sudo lspci -vv -d 197b: | grep LnkSta
```

Opcional, para quitar el aviso de alimentación al arrancar: `sudo rpi-eeprom-config --edit`,
añade `PSU_MAX_CURRENT=5000`, guarda y reinicia.

### 3.4 Conectar los discos

1. `sudo poweroff`, desenchufa el 12 V y conecta los tres discos en sus bahías.
2. Arranca y comprueba que salen cuatro dispositivos (XG5 + tres SATA):

```
lsblk -o NAME,SIZE,MODEL,SERIAL
```

[Captura 3.3: salida de lsblk con los cuatro dispositivos]

## 4. Instalar OpenMediaVault 8

OMV 8 se instala con dos scripts de omv-extras sobre Raspberry Pi OS Lite Trixie, y después
todo se configura desde el navegador (guía probada en Trixie).

### 4.1 Scripts de instalación

```
wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/preinstall | sudo bash
sudo reboot
wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/install | sudo bash
```

- El segundo script tarda un buen rato y reinicia solo. Necesita Ethernet e Internet todo el tiempo.
- La sesión SSH se cortará durante la instalación: es normal. Gracias a la reserva DHCP, la IP no cambia.
- No añadas repositorios de Ubuntu ni PPA: el instalador falla con "unsupported OS".
- Comprueba al final: `systemctl status openmediavault-engined` debe decir `active (running)`.

### 4.2 Primer acceso

1. Abre `http://nas.local` (o la IP reservada). Usuario `admin`, contraseña de fábrica
   `openmediavault`.
2. Cambia la contraseña: icono de usuario arriba a la derecha → Cambiar contraseña.
3. Acepta los cambios pendientes si aparece la barra amarilla.
4. **Sistema → Área de trabajo → Puerto: 8000.** Libera el puerto 80 para Nextcloud AIO.
   Desde ahora entras por `http://nas.local:8000`.

[Captura 4.1: pantalla de inicio de sesión de OMV]

[Captura 4.2: Sistema → Área de trabajo con el puerto 8000]

### 4.3 Plugins

En **Sistema → Complementos**, instala:

| Plugin | Para qué | Sección |
|---|---|---|
| openmediavault-snapraid | Paridad de los discos de datos | 6 |
| openmediavault-mergerfs | Unir D1 y D2 en una sola carpeta | 7 |
| openmediavault-sharerootfs | Carpetas compartidas en el SSD del sistema (lo instala SnapRAID) | 10 |
| openmediavault-compose | Docker para Nextcloud AIO | 10 |
| openmediavault-nut | SAI y apagado limpio | 12 |

[Captura 4.3: Sistema → Complementos con los cinco plugins instalados]

### 4.4 Avisos por correo

Google ya no admite "aplicaciones menos seguras" como en la v1. Activa la verificación en dos
pasos en tu cuenta y crea una **contraseña de aplicación** de 16 caracteres.

En **Sistema → Notificación → Configuración**:

| Campo | Valor |
|---|---|
| Servidor SMTP | smtp.gmail.com |
| Puerto | 587 |
| Cifrado | STARTTLS |
| Remitente | tu_correo@gmail.com |
| Autenticación | Activada; usuario = la dirección completa |
| Contraseña | La contraseña de aplicación |
| Destinatario principal | Tu correo |

Guarda, envía un correo de prueba y activa en **Notificaciones** los avisos de SMART, sistema de
ficheros y actualizaciones.

[Captura 4.4: Sistema → Notificación con el SMTP de Gmail]

### 4.5 Actualizaciones

Aplica las actualizaciones a mano una vez al mes desde **Sistema → Gestión de
actualizaciones**, no en automático con reinicio como en la v1. Después de cada actualización
de kernel, comprueba que siguen los tres discos.

## 5. Discos: revisión y formateo

Primero se comprueba la salud de cada disco y se confirma cuál hace de paridad; después se
formatea cada uno en ext4 por separado, sin RAID ni LVM.

### 5.1 Revisión SMART por terminal

```
sudo smartctl -a /dev/sdX          # repetir para cada disco SATA
sudo smartctl -t long /dev/sdX     # test largo: 2-3 h por disco de 1 TB
sudo smartctl -l selftest /dev/sdX
lsblk -b -d -o NAME,SIZE,MODEL     # tamaño exacto en bytes
```

| Atributo | Qué indica | Regla |
|---|---|---|
| 5 Reallocated_Sector_Ct | Sectores ya sustituidos | Si crece entre dos lecturas, retirar el disco |
| 197 Current_Pending_Sector | Sectores dudosos | Distinto de 0: no usar como paridad |
| 198 Offline_Uncorrectable | Sectores ilegibles | Distinto de 0: no usar como paridad |
| 199 UDMA_CRC_Error_Count | Errores de cable o conector | Si crece, revisar el FFC y la bahía |
| 9 Power_On_Hours | Horas de uso | Informativo |
| 177 / 241 (solo QVO) | Desgaste y escrituras del SSD | Informativo |

La paridad debe ser el disco mecánico más sano y de tamaño igual o mayor que cada disco de
datos. Si el WD cumple, se confirma como paridad.

[Captura 5.1: salida de smartctl de cada disco]

### 5.2 Vigilancia SMART en OMV

1. **Almacenamiento → S.M.A.R.T. → Configuración:** activado, intervalo 1800 s, modo de energía
   **En espera** (Standby). Así la vigilancia no despierta discos dormidos.
2. Temperaturas: informativa 40 °C, crítica 45 °C.
3. **Dispositivos:** activa la vigilancia en los tres discos.
4. **Pruebas programadas:** corta semanal y larga mensual de cada disco.

[Captura 5.2: S.M.A.R.T. → Configuración con modo Standby]

### 5.3 Borrar y formatear

Borrar elimina todo el contenido del disco. Si alguno de los discos viejos guarda datos que
quieras conservar, cópialos antes.

1. **Almacenamiento → Discos:** selecciona cada disco SATA → Borrar → Rápido.
2. **Almacenamiento → Sistemas de archivos → Crear y montar:** EXT4, un disco cada vez.
3. Anota qué montaje (`/srv/dev-disk-by-uuid-…`) corresponde a cada disco:

| Rol | Disco | Punto de montaje |
|---|---|---|
| Paridad | WD Blue 1 TB | |
| D1 | Toshiba MK1059 1 TB | |
| D2 | Samsung QVO 1 TB | |

4. En la paridad, los bloques reservados deben ser 0 para que la paridad quepa siempre:

```
sudo tune2fs -l /dev/sdX1 | grep 'Reserved block count'
sudo tune2fs -m 0 /dev/sdX1   # solo si no es 0, y solo en la paridad
```

[Captura 5.3: Almacenamiento → Sistemas de archivos con los tres discos montados]

## 6. SnapRAID

SnapRAID calcula la paridad de D1 y D2 en el WD una vez al día: protege del fallo de un disco y
del bitrot, y deja recuperar lo borrado desde el último sync.

### 6.1 Crear el array

En **Servicios → SnapRAID**:

1. **Arrays → Crear:** nombre `nas`.
2. **Discos → Añadir**, uno por fila:

| Disco | Nombre | Datos | Paridad | Content |
|---|---|---|---|---|
| WD Blue 1 TB | parity | no | sí | no |
| Toshiba MK1059 1 TB | d1 | sí | no | sí |
| Samsung QVO 1 TB | d2 | sí | no | sí |
| SSD del sistema (raíz) | ssd | no | no | sí |

SnapRAID necesita al menos un fichero content más que discos de paridad; aquí hay tres, en tres
discos distintos.

3. **Reglas → Excluir:** `*.unrecoverable`, `/lost+found/`, `/tmp/` y `.Trash-*/`.
4. Guarda y aplica. La configuración queda en `/etc/snapraid/omv-snapraid-<id>.conf`.

[Captura 6.1: Servicios → SnapRAID → Discos con los cuatro roles]

### 6.2 Primer sync

Copia antes una parte de los datos al pool (sección 7) y lanza el primer sync desde el plugin o
por terminal:

```
sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync
sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status
```

### 6.3 Programación

| Tarea | Cuándo | Ajuste |
|---|---|---|
| diff + sync | Cada día a las 04:00 | No sincronizar si hay más de 50 ficheros borrados: avisa por correo y espera |
| scrub | Domingo tras el sync | 12 % de los bloques con más de 10 días: todo el array en unas 8 semanas |
| status | Tras cada sync | Informe por correo |

El umbral de borrados es la clave: si alguien borra una carpeta por error, el sync no se ejecuta
y la paridad aún permite recuperarla. Configúralo en la opción de diff programado del plugin.

[Captura 6.2: ajustes del diff programado con el umbral de borrados]

### 6.4 Recuperar

| Situación | Comando |
|---|---|
| Fichero borrado por error (antes del siguiente sync) | `sudo snapraid -c <conf> fix -f "ruta/del/fichero"` |
| Disco de datos muerto (tras montar el disco nuevo en su lugar) | `sudo snapraid -c <conf> -d d1 -l fix.log fix` y después `-d d1 -a check` |
| Comprobar errores de lectura | `sudo snapraid -c <conf> -p bad scrub` |

Después de una recuperación, lanza un sync normal.

## 7. MergerFS y carpetas compartidas

MergerFS une D1 y D2 en una sola carpeta de unos 2 TB; la paridad no entra en el pool. Cada disco
sigue siendo un ext4 que se puede leer por separado en cualquier Linux.

### 7.1 Crear el pool

En **Almacenamiento → mergerfs → Crear**:

| Campo | Valor | Por qué |
|---|---|---|
| Nombre | `pool` | Se monta en `/srv/mergerfs/pool` |
| Sistemas de archivos | D1 y D2 (nunca la paridad) | La paridad la gestiona SnapRAID |
| Política de creación | `mfs` (más espacio libre) | Con dos discos evita errores de disco lleno |
| Espacio libre mínimo | `20G` | Garantiza que la paridad siempre quepa |

Guarda y aplica. El pool aparece como un sistema de archivos más.

[Captura 7.1: Almacenamiento → mergerfs con el pool creado]

### 7.2 Carpetas compartidas

En **Almacenamiento → Carpetas compartidas → Crear**, todas sobre el sistema de archivos `pool`:

| Carpeta | Contenido | Backup offline (sección 11) |
|---|---|---|
| Documentos | Papeles, trabajo, facturas | Sí |
| Fotos | Fotos y vídeos familiares; aquí llegan las del móvil vía Nextcloud | Sí |
| Videos | Películas y series | No: es reemplazable |
| Archivo | Copias antiguas, instaladores y el backup diario de Nextcloud (nextcloud-aio-backup) | Solo nextcloud-aio-backup |

[Captura 7.2: Carpetas compartidas con las cuatro carpetas sobre el pool]

## 8. Usuarios y Samba

Cada miembro de la familia tiene su usuario; los permisos se dan al grupo `familia` y las
carpetas se ven en Windows y Linux como unidades de red.

### 8.1 Usuarios y grupo

1. **Usuarios → Grupos → Crear:** `familia`.
2. **Usuarios → Usuarios → Crear:** un usuario por persona, miembro de `familia`.
3. **Usuarios → Grupos → familia → Privilegios** sobre cada carpeta compartida:

| Carpeta | familia |
|---|---|
| Documentos | Lectura y escritura |
| Fotos | Lectura y escritura |
| Videos | Lectura y escritura |
| Archivo | Solo lectura |

[Captura 8.1: privilegios del grupo familia]

### 8.2 Samba

1. **Servicios → SMB/CIFS → Configuración:** activado. El resto, por defecto.
2. **Servicios → SMB/CIFS → Recursos compartidos → Crear:** uno por carpeta compartida, sin
   acceso de invitados. Activa la papelera de reciclaje: un borrado desde el PC va primero a
   `.recycle`.
3. Prueba desde los PC:
   - Windows: `\\nas\Documentos` en el Explorador, o Conectar unidad de red.
   - Linux (Dolphin): `smb://nas.local/Documentos`.

La carpeta `Fotos` lleva además dos opciones extra para que Nextcloud también pueda escribir en
ella: ver la sección 10.4.

[Captura 8.2: Servicios → SMB/CIFS → Recursos compartidos]

[Captura 8.3: carpeta Documentos abierta desde el Explorador de Windows]

## 9. Spindown con hd-idle

Los dos discos mecánicos se paran tras 45 minutos sin uso; el NAS sigue encendido 24/7. El QVO
es un SSD y no necesita spindown.

1. En OMV, **Almacenamiento → Discos → Editar** cada disco: tiempo de spindown **desactivado**.
   Así no compite con hd-idle.
2. Instala hd-idle y localiza los nombres estables de los discos:

```
sudo apt install hd-idle
ls -l /dev/disk/by-id/ | grep -v part
```

3. Edita `/etc/default/hd-idle` con los nombres de tu equipo:

```
START_HD_IDLE=true
HD_IDLE_OPTS="-i 0 -a /dev/disk/by-id/ata-WDC_XXXX -i 2700 -a /dev/disk/by-id/ata-TOSHIBA_MK1059XXXX -i 2700 -l /var/log/hd-idle.log"
```

`-i 0` al principio impide parar cualquier otro disco, incluido el SSD del sistema.

4. Activa el servicio y comprueba el estado de cada disco (esta orden no los despierta):

```
sudo systemctl enable --now hd-idle
sudo hdparm -C /dev/sdX
```

Vigila el atributo SMART 193 Load_Cycle_Count de los discos de portátil. Si sube cientos por
día, pon el APM a 254 en **Almacenamiento → Discos → Editar**: frena el aparcado agresivo de
cabezales.

[Captura 9.1: Almacenamiento → Discos → Editar con el spindown desactivado]

## 10. Nextcloud AIO en el SSD

Nextcloud AIO sincroniza los PC con su cliente de escritorio y recibe las fotos de los móviles.
Sus datos viven en el SSD; las fotos y su backup diario, en el pool.

### 10.1 Carpetas y permisos

1. Con sharerootfs instalado, el sistema de archivos raíz (`/`) aparece en **Almacenamiento →
   Sistemas de archivos**.
2. **Almacenamiento → Carpetas compartidas → Crear** sobre `/`: `compose` (ficheros de Docker) y
   `ncdata` (datos de Nextcloud, vacía). Anota la ruta absoluta de `ncdata`.
3. Prepara el pool por terminal:

```
sudo mkdir -p /srv/mergerfs/pool/Archivo/nextcloud-aio-backup
sudo chown -R www-data:www-data /srv/mergerfs/pool/Fotos
```

4. **Servicios → Compose → Configuración:** elige `compose` como carpeta de ficheros y aplica.
   Si Docker no está instalado, el plugin ofrece instalarlo.

[Captura 10.1: carpetas compose y ncdata sobre el sistema de archivos raíz]

### 10.2 Contenedor

En **Servicios → Compose → Ficheros → Crear**, nombre `nextcloud-aio`. Es el compose oficial con
tres variables activadas:

```yaml
name: nextcloud-aio
services:
  nextcloud-aio-mastercontainer:
    image: ghcr.io/nextcloud-releases/all-in-one:latest
    init: true
    restart: always
    container_name: nextcloud-aio-mastercontainer
    volumes:
      - nextcloud_aio_mastercontainer:/mnt/docker-aio-config
      - /var/run/docker.sock:/var/run/docker.sock:ro
    network_mode: bridge
    ports:
      - "80:80"
      - "8080:8080"
      - "8443:8443"
    environment:
      NEXTCLOUD_DATADIR: /RUTA/ABSOLUTA/DE/ncdata
      NEXTCLOUD_MOUNT: /srv/mergerfs/pool/Fotos
      NEXTCLOUD_UPLOAD_LIMIT: 16G
volumes:
  nextcloud_aio_mastercontainer:
    name: nextcloud_aio_mastercontainer
```

| Variable | Qué hace |
|---|---|
| `NEXTCLOUD_DATADIR` | Datos de Nextcloud en el SSD. No se puede cambiar después de instalar |
| `NEXTCLOUD_MOUNT` | Deja a Nextcloud acceder solo a `Fotos` del pool |
| `NEXTCLOUD_UPLOAD_LIMIT` | Tamaño máximo por fichero, para los vídeos del móvil |

Guarda y pulsa Arriba (Up).

[Captura 10.2: fichero compose de Nextcloud AIO en estado Up]

### 10.3 Panel de AIO

1. Abre `https://IP_DEL_NAS:8080` y acepta el aviso del certificado autofirmado. Entra a este
   panel siempre por la IP, nunca por el dominio.
2. Guarda la **frase de acceso** que muestra, fuera del NAS: sin ella no entras ni restauras.
3. Dominio: en la sección "Don't have a domain? Get a free one from deSEC", registra uno gratis.
   AIO obtiene el certificado por DNS, sin abrir puertos.
4. Contenedores opcionales: activa solo **Imaginary** (vistas previas rápidas de fotos). Deja
   apagados Office, Talk, ClamAV y la búsqueda de texto completo: consumen RAM.
5. Inicia los contenedores y guarda la contraseña inicial del usuario admin de Nextcloud.
6. **Copia de seguridad:** ruta `/srv/mergerfs/pool/Archivo/nextcloud-aio-backup`, diaria a las
   03:00 hora local, con actualizaciones automáticas después. Si el panel pide la hora en UTC,
   conviértela. Guarda también la contraseña del backup.

El backup de AIO detiene Nextcloud unos minutos y guarda datos, base de datos y configuración.
Restic lo copia después al Hitachi (sección 11).

[Captura 10.3: panel de AIO con los contenedores en marcha y el backup diario]

### 10.4 Fotos del pool en Nextcloud

1. En Nextcloud, como admin, **Usuarios**: un usuario por persona y el grupo `familia`.
2. **Aplicaciones:** activa "External storage support".
3. **Administración → Almacenamiento externo:** carpeta `Fotos`, tipo Local, ruta
   `/srv/mergerfs/pool/Fotos`, disponible para el grupo `familia`.
4. En OMV, recurso SMB `Fotos` → **Opciones extra:** `force user = www-data` y
   `force group = www-data`. Así lo copiado desde los PC también lo puede gestionar Nextcloud.

Los borrados en `Fotos` los cubren SnapRAID (hasta el siguiente sync) y restic, no la papelera
de Nextcloud.

[Captura 10.4: Almacenamiento externo con Fotos para el grupo familia]

### 10.5 PC y móviles

- **PC:** instala el cliente de escritorio, entra con el dominio y elige las carpetas. En
  Windows, activa los ficheros virtuales para no duplicar espacio.
- **Móviles:** app Nextcloud → Ajustes → **Subida automática**: carpeta `Fotos/Movil-<nombre>`,
  solo con WiFi, solo cargando y subcarpetas por año y mes.
- Antes de activar la subida, comprueba en la WiFi de casa que el móvil abre `https://tu-dominio`.

Con "solo cargando", las fotos suben sobre todo de noche: el disco del pool despierta una vez,
cerca del sync de las 04:00.

[Captura 10.5: subida automática configurada en el móvil]

## 11. Backups

SnapRAID no es un backup. Lo irreemplazable (Documentos, Fotos y el backup diario de Nextcloud)
va además al Hitachi con restic una vez al mes, y una tercera copia sale de casa.

### 11.1 Preparar el Hitachi (una sola vez)

Conéctalo por USB y localízalo con `lsblk`: será el único disco de ~320 GB. Las órdenes
siguientes **borran el disco indicado**; comprueba la letra dos veces.

```
sudo wipefs -a /dev/sdX
sudo parted -s /dev/sdX mklabel gpt mkpart backup ext4 0% 100%
sudo mkfs.ext4 -L backup /dev/sdX1
sudo mkdir -p /mnt/backup
sudo mount /dev/disk/by-label/backup /mnt/backup
sudo apt install restic
sudo restic -r /mnt/backup/restic init
```

No lo montes desde OMV: es un disco que pasa el mes desconectado. Guarda la contraseña del
repositorio fuera del NAS; sin ella, el backup es irrecuperable.

### 11.2 Rutina mensual

```
sudo mount /dev/disk/by-label/backup /mnt/backup
sudo restic -r /mnt/backup/restic backup /srv/mergerfs/pool/Documentos /srv/mergerfs/pool/Fotos /srv/mergerfs/pool/Archivo/nextcloud-aio-backup
sudo restic -r /mnt/backup/restic forget --keep-monthly 12 --prune
sudo restic -r /mnt/backup/restic check
sudo umount /mnt/backup
```

Hazlo de día, lejos del backup de AIO de las 03:00. Después, desenchufa el disco y guárdalo
fuera de la habitación del NAS. A diferencia del `rsync --delete`, cada copia es una versión
nueva: un borrado o un cifrado no destruye las copias anteriores.

[Captura 11.1: salida de restic backup con el resumen de ficheros]

### 11.3 Restaurar

```
sudo restic -r /mnt/backup/restic snapshots
sudo restic -r /mnt/backup/restic restore latest --target /srv/mergerfs/pool/Restaurado --include /srv/mergerfs/pool/Documentos
```

Restaura siempre a una carpeta nueva y copia después lo que necesites.

### 11.4 Copia fuera de casa (regla 3-2-1)

Un rayo o una inundación afectan a toda la casa a la vez. Elige una de estas dos opciones:

| Opción | Cómo | Coste |
|---|---|---|
| Rotación de dos discos | Un segundo disco viejo con su propio repositorio restic; uno siempre en otra casa, se cambian cada mes | Un disco viejo |
| Nube | restic directo a un almacenamiento en la nube, solo Documentos y Fotos, cifrado antes de salir de casa | Pocos euros al mes |

## 12. SAI y apagado limpio

El SAI alimenta el adaptador de 12 V; si la luz falta más de 5 minutos, NUT apaga el NAS
ordenadamente antes de agotar la batería.

1. Enchufa el adaptador de 12 V del NAS (y el router, si cabe) al SAI, y el cable USB del SAI a la Pi.
2. Comprueba que la Pi lo ve: `lsusb` debe mostrar el SAI.
3. **Servicios → SAI (UPS)**:

| Campo | Valor |
|---|---|
| Activado | Sí |
| Modo | Independiente (standalone) |
| Identificador | `ups` |
| Directivas del driver | `driver = usbhid-ups` y `port = auto` |
| Modo de apagado | Temporizador, 300 s en batería |

4. Activa los avisos del SAI en **Sistema → Notificación → Notificaciones**.
5. Comprueba el estado: `upsc ups@localhost` debe mostrar `ups.status: OL` (conectado a la red).

Prueba una vez: desenchufa el SAI de la pared, espera el correo de aviso y vuelve a enchufarlo
antes de los 5 minutos. Si tu SAI corta su salida al final del apagado, el NAS arrancará solo
cuando vuelva la luz.

[Captura 12.1: Servicios → SAI con usbhid-ups y el temporizador]

## 13. Temperatura y mantenimiento

El objetivo es una Pi por debajo de 70 °C sin throttling y discos por debajo de 40 °C, con un
ventilador que no cambie de ruido de madrugada.

### 13.1 Ventilación

- El Active Cooler de la Pi lo regula el firmware: no hay que tocar nada.
- El ventilador de 120 mm va a velocidad fija baja, siempre igual: un zumbido constante molesta
  menos que uno que acelera durante el sync de las 04:00.
- Si montas el top board de Radxa, ajusta sus umbrales para que el ventilador quede en un nivel fijo.

### 13.2 Comprobaciones

```
vcgencmd measure_temp
vcgencmd get_throttled           # 0x0 = sin throttling ni subtensión
sudo smartctl -A /dev/sdX | grep -i temp
```

En el panel de OMV, añade los widgets de temperatura de CPU y de estado SMART.

[Captura 13.1: panel de OMV con temperatura y SMART]

### 13.3 Lista periódica

Cada semana:

- [ ] Leer el informe de SnapRAID por correo (sync hecho, sin umbral superado)
- [ ] Comprobar en el panel de AIO que el backup diario terminó

Cada mes:

- [ ] Backup restic al Hitachi y guardarlo fuera de la habitación
- [ ] Limpiar el filtro de polvo
- [ ] Aplicar actualizaciones de OMV y comprobar `lsblk` si cambió el kernel
- [ ] Revisar SMART: atributos 5, 197, 198 y 193

Cada seis meses:

- [ ] Restaurar un fichero de prueba desde restic
- [ ] Probar el SAI desenchufándolo de la pared
- [ ] Cambiar el disco de la copia fuera de casa (o comprobar la copia en la nube)

## 14. Opcional: acceso desde fuera de casa

En casa no hace falta nada más. Para usar Nextcloud desde fuera, elige una de estas dos vías; el
resto del NAS no se expone nunca.

| Opción | Cómo | Puertos abiertos | A tener en cuenta |
|---|---|---|---|
| Tailscale | Sigue la guía de AIO para Tailscale | Ninguno | Lo más seguro; cada dispositivo de la familia necesita la app de Tailscale |
| Publicar Nextcloud | Abrir 443/TCP en el router hacia el NAS, con el dominio de deSEC o el de OVH de la v1 | Solo 443/TCP | Lo más cómodo; activa la verificación en dos pasos en cada cuenta |

Nunca expongas a Internet el panel de OMV (8000), el panel de AIO (8080) ni SSH.

## Anexo: seguir la guía con Claude in Chrome

Claude in Chrome puede recorrer las pantallas de OMV y Nextcloud paso a paso y hacer las
capturas; los pasos de terminal, contraseñas y borrados los haces tú.

### Cómo trabajar

1. Abre esta guía y la interfaz de OMV (`http://nas.local:8000`) en pestañas de Chrome.
2. Inicia sesión tú en OMV: Claude in Chrome no escribe contraseñas.
3. Pídele, por ejemplo: "sigue la sección 6.1 de la guía y haz la captura 6.1 al terminar".
4. Te pedirá confirmación antes de cada Guardar o Aplicar: revisa el formulario y confirma.
5. Pega cada captura en lugar de su marcador `[Captura X.Y]`.

| Lo hace Claude in Chrome | Lo haces tú |
|---|---|
| Navegar menús de OMV, Nextcloud y el router | Escribir contraseñas e iniciar sesión |
| Rellenar campos que no sean contraseñas | Borrar o formatear discos (5.3) |
| Hacer capturas de cada pantalla | Órdenes de terminal por SSH |
| Comprobar que cada ajuste quedó aplicado | Fotos del montaje físico |

La v1 incluía contraseñas reales en claro. En esta versión no escribas ninguna, y tapa en las
capturas cualquier contraseña, frase de acceso de AIO o IP pública.

### Lista de capturas

| Nº | Qué muestra | Cómo |
|---|---|---|
| 1.1 | HAT con los discos en sus bahías | Foto |
| 1.2 | NAS en su sitio con ventilador y filtro | Foto |
| 2.1 | Imager con dispositivo, sistema y XG5 | Tú, en el PC |
| 2.2 | Personalización de Imager | Tú, en el PC |
| 3.1 | config.txt con las cuatro líneas | Tú, en el PC |
| 3.2 | Reserva DHCP en el router | Claude in Chrome |
| 3.3 | Salida de lsblk | Tú, terminal |
| 4.1 | Inicio de sesión de OMV | Claude in Chrome |
| 4.2 | Área de trabajo con el puerto 8000 | Claude in Chrome |
| 4.3 | Complementos instalados | Claude in Chrome |
| 4.4 | Notificación con el SMTP de Gmail | Claude in Chrome |
| 5.1 | smartctl de cada disco | Tú, terminal |
| 5.2 | S.M.A.R.T. en modo Standby | Claude in Chrome |
| 5.3 | Sistemas de archivos montados | Claude in Chrome |
| 6.1 | Discos de SnapRAID con sus roles | Claude in Chrome |
| 6.2 | Diff programado con umbral | Claude in Chrome |
| 7.1 | Pool de mergerfs | Claude in Chrome |
| 7.2 | Carpetas compartidas del pool | Claude in Chrome |
| 8.1 | Privilegios del grupo familia | Claude in Chrome |
| 8.2 | Recursos SMB | Claude in Chrome |
| 8.3 | Documentos abierto en Windows | Tú, en el PC |
| 9.1 | Spindown desactivado en OMV | Claude in Chrome |
| 10.1 | Carpetas compose y ncdata en el SSD | Claude in Chrome |
| 10.2 | Compose de Nextcloud AIO en Up | Claude in Chrome |
| 10.3 | Panel de AIO con contenedores y backup | Claude in Chrome |
| 10.4 | Almacenamiento externo Fotos | Claude in Chrome |
| 10.5 | Subida automática en el móvil | Tú, en el móvil |
| 11.1 | Resumen de restic backup | Tú, terminal |
| 12.1 | Configuración del SAI | Claude in Chrome |
| 13.1 | Panel de OMV con temperaturas | Claude in Chrome |
