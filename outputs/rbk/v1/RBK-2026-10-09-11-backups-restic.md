# RBK 11 — Backups con restic

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 11 — Backups con restic |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 1 h + burn-in (10-12 h) + primer backup (horas) |

## Objetivo

Preparar el disco USB externo de 4 TB (burn-in SMART largo antes del primer uso), crear el
repositorio restic y hacer el primer backup de Documentos, Imagenes y Archivo con
`restic check --read-data-subset=5%`; dejar escrita la rutina mensual con la lectura SMART previa
y sus criterios de aborto y la retención de 12 mensuales que aplica el usuario (HLD §7, ADR-004,
ADR-017). El Hitachi de 320 GB no se usa.

## Prerrequisitos

- [ ] RBK 08 completado (datos cargados) y RBK 10 y 15 con su primer backup de AIO y volcado de Immich
- [ ] Contraseña del repositorio restic creada en el gestor de contraseñas, con acceso de emergencia para persona 2, fuera del NAS
- [ ] Disco USB de 4 TB nuevo en su caja, con su número de serie anotado (RBK 01)

## Pasos

### Paso 1: Conectar e identificar el disco USB

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 (Backup) |

Comando:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

El usuario conecta el disco a un USB 3 libre antes del comando.

Esperado: un disco nuevo `usb` de ~4 000 000 000 000 bytes con el número de serie del RBK 01; el XG5 y los tres SATA como antes. Anota la letra actual en el OPS.

Si falla: si no aparece, cambia de puerto USB 3 y repite; si aparece con otro tamaño, para.

### Paso 2: Comprobar que la caja pasa SMART

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7, ADR-017 |

Comando:

```bash
ssh nas 'sudo smartctl -d sat -i -H /dev/sdX'
```

Esperado: `SMART support is: Enabled` y `SMART overall-health self-assessment test result: PASSED` con `-d sat`.

Si falla: si la caja no pasa SMART, para: se cambia de caja antes del primer uso (ADR-017).

### Paso 3: Lanzar el burn-in (test largo)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7, ADR-017 |

Comando:

```bash
ssh nas 'sudo smartctl -d sat -t long /dev/sdX'
```

Esperado: «Testing has begun» y la duración estimada (varias horas en 4 TB).

Si falla: si la caja corta el test al dormir el disco, anótalo; ver pregunta abierta.

### Paso 4: Leer el resultado del burn-in

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7, ADR-017 |

Comando:

```bash
ssh nas "sudo smartctl -d sat -l selftest /dev/sdX; sudo smartctl -d sat -A /dev/sdX | grep -E '^ *(5|187|194|197|198|199) '"
```

Esperado: `Completed without error` y atributos 5, 187, 197, 198 y 199 a 0. Valores y temperatura anotados en el OPS (base de la tendencia).

Si falla: si falla el test o algún atributo es distinto de 0, **se devuelve el disco**; no se escribe nada.

### Paso 5: Particionar y formatear el disco USB

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §5 (Backup, ext4, etiqueta backup) |

Comprobación previa:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

Comprueba dos veces que `sdX` es el disco `usb` de ~4 TB con el número de serie del RBK 01.

Comando:

```bash
sudo wipefs -a /dev/sdX
sudo parted -s /dev/sdX mklabel gpt mkpart backup ext4 0% 100%
sudo mkfs.ext4 -L backup /dev/sdX1
```

Esperado: una partición `sdX1` ext4 con etiqueta `backup` en el disco de 4 TB; los tres SATA y el XG5 intactos.

Si falla: si se escribió en otro disco, para todo y no escribas nada más; restaura desde SnapRAID o desde los PC según el disco.

### Paso 6: Montar el disco por etiqueta

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, §7 |

Comando:

```bash
ssh nas 'sudo mkdir -p /mnt/backup && sudo mount /dev/disk/by-label/backup /mnt/backup && df -h /mnt/backup'
```

Esperado: `/dev/sdX1` montado en `/mnt/backup` con ~3,6 T libres. No se monta desde OMV (pasa el mes desconectado).

Si falla: si no monta, revisa `dmesg` y la etiqueta con `lsblk -o NAME,LABEL`.

### Paso 7: Instalar restic

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7, §10 |

Comando:

```bash
ssh nas 'sudo apt install -y restic && restic version'
```

Esperado: `restic` instalado; `restic version` muestra la versión (anotada en el OPS).

Si falla: si no está en el repositorio, prepara un UPD.

### Paso 8: Crear el repositorio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7, §8 |

Comando:

```bash
ssh nas
sudo restic -r /mnt/backup/restic init
```

Esperado: `created restic repository … at /mnt/backup/restic`; la contraseña la teclea el usuario desde el gestor de contraseñas y no se guarda en el NAS.

Si falla: si se pierde la contraseña antes de la primera copia, borra el repositorio vacío (lo hace el usuario) y repite.

### Paso 9: Primer backup

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7 |

Comando:

```bash
sudo restic -r /mnt/backup/restic backup /srv/mergerfs/pool/Documentos /srv/mergerfs/pool/Imagenes /srv/mergerfs/pool/Archivo
```

De día, en horario de uso, fuera de 23:00-01:00. `Videos` no se copia (HLD §6).

Esperado: resumen de restic con `snapshot … saved` y 0 errores; ~1,2 TB añadidos. Duración anotada en el OPS.

Si falla: si se corta, repítelo: restic continúa sin volver a copiar lo ya guardado.

### Paso 10: Comprobar el repositorio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7, ADR-017 |

Comando:

```bash
sudo restic -r /mnt/backup/restic check --read-data-subset=5%
```

Esperado: `no errors were found`.

Si falla: si falla, no se aplica retención y se revisa antes de la siguiente copia (`/storage-plugin:diagnose-disk`).

### Paso 11: Listar snapshots y restaurar un fichero de prueba

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7, §10 |

Comando:

```bash
sudo restic -r /mnt/backup/restic snapshots
sudo restic -r /mnt/backup/restic restore latest --target /srv/mergerfs/pool/Restaurado --include /srv/mergerfs/pool/Documentos/persona1/<fichero>
cmp /srv/mergerfs/pool/Restaurado/srv/mergerfs/pool/Documentos/persona1/<fichero> /srv/mergerfs/pool/Documentos/persona1/<fichero>
```

Esperado: un snapshot con fecha de hoy; un fichero de Documentos restaurado en `/srv/mergerfs/pool/Restaurado` idéntico al original (`cmp` sin salida).

Si falla: si la restauración falla, el backup no vale: para y revisa.

### Paso 12: Desmontar y llevar el disco fuera de casa

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7 |

Comando:

```bash
ssh nas 'sudo umount /mnt/backup && findmnt /mnt/backup || echo desmontado'
```

Esperado: `/mnt/backup` desmontado; el usuario desenchufa el disco y lo guarda fuera de casa.

Si falla: si `umount` dice «target is busy», cierra las sesiones que usen el disco y repite.

### Paso 13: Hoja impresa para persona 2

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §8 |

Esperado: hoja impresa, sin contraseñas, con: cómo entrar en Nextcloud y descargar; dónde está el disco USB; cómo leerlo con restic (`restic -r <ruta> snapshots` y `restore`) y que la contraseña está en el gestor con acceso de emergencia.

Si falla: si falta algo, se completa en la prueba semestral de acceso de persona 2.

### Paso 14: Rutina mensual 1: lectura SMART previa

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §7 (Salud del disco de backup), ADR-017 |

Comando:

```bash
ssh nas "lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN; sudo smartctl -d sat -H -A /dev/sdX | grep -E 'overall-health|^ *(5|187|194|197|198|199) '"
```

Esperado: primer sábado de cada mes, con el disco conectado e identificado por serie: `PASSED`; 5, 187, 197 y 198 a 0 y sin subir respecto al OPS anterior; 199 sin subir; temperatura ≤ 45 °C. Valores anotados en el OPS.

Si falla: si no es `PASSED`, si 5/187/197/198 ≠ 0 o han subido, si 199 sube o si la temperatura supera 45 °C: **se aborta sin montar ni escribir**, se avisa al usuario y se pasa a `/storage-plugin:diagnose-disk` para sustituir el disco.

### Paso 15: Rutina mensual 2: montar, copiar y comprobar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7 |

Comando:

```bash
sudo mount /dev/disk/by-label/backup /mnt/backup
sudo restic -r /mnt/backup/restic backup /srv/mergerfs/pool/Documentos /srv/mergerfs/pool/Imagenes /srv/mergerfs/pool/Archivo
sudo restic -r /mnt/backup/restic check --read-data-subset=5%
```

Esperado: backup con `snapshot … saved` y `check` con `no errors were found`.

Si falla: si `check` falla, no se ejecuta el paso 16 y se revisa antes de la siguiente copia.

### Paso 16: Rutina mensual 3: retención de 12 mensuales

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §7, ADR-017 |

Comprobación previa:

```bash
sudo restic -r /mnt/backup/restic snapshots
```

Solo si el `check` del paso 15 dio `no errors were found` y el disco es el de la serie del RBK 01.

Comando:

```bash
sudo restic -r /mnt/backup/restic forget --keep-monthly 12 --prune
sudo umount /mnt/backup
```

Esperado: `forget` conserva 12 snapshots mensuales y `prune` libera espacio; `snapshots` lista como mucho 12.

Si falla: si `forget` borró snapshots que no debía, no se pueden recuperar: el siguiente backup crea una versión nueva; anota la incidencia.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Burn-in | `ssh nas 'sudo smartctl -d sat -l selftest /dev/sdX'` | Completed without error |
| Snapshot | `sudo restic -r /mnt/backup/restic snapshots (usuario)` | 1 snapshot con fecha de hoy |
| Check | `sudo restic -r /mnt/backup/restic check --read-data-subset=5% (usuario)` | no errors were found |
| Disco fuera | `ssh nas 'findmnt /mnt/backup \\|\\| echo desmontado'` | desmontado |

## Vuelta atrás

Hasta el paso 4 no se ha escrito el disco: si falla el burn-in, se devuelve. Desde el paso 5 el
disco de backup está formateado; no contiene datos de otro sitio, así que repetir desde el paso 5
no pierde nada. El repositorio se puede volver a crear. La carpeta `/srv/mergerfs/pool/Restaurado` la borra el
usuario tras la prueba.

## Evidencias

- Atributos 5, 187, 194, 197, 198 y 199 del disco USB tras el burn-in y en cada rutina mensual (tendencia) en el OPS
- Resumen de `restic backup` y de `restic check` en el OPS; captura 11.1
- Fecha y lugar de custodia del disco fuera de casa en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| Algunas cajas USB duermen el disco y cortan el test largo de 4 TB: si pasa, ¿se lanza el burn-in con el disco conectado al PC o se cambia de caja? | Persona 1 | Ejecución del RBK 11 |
| ¿Se excluyen las papeleras `.recycle` de Samba del backup restic (`--exclude .recycle`)? El HLD no lo dice | Arquitecto | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
