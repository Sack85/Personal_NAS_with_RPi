# DCP — D1 (Toshiba MK1059) degradado y retirado: WD pasa a d1 y Seagate 2 TB a paridad

| Campo | Valor |
|---|---|
| **Documento** | DCP |
| **Versión** | 1.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-15 |
| **Última modificación** | 2026-10-15 |
| **Autor** | Storage Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Escenario** | Retirada |
| **Disco afectado** | D1 — Toshiba MK1059GSM 1 TB, `/dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES`, serie Y1NDFAQES (ya retirado) |
| **Disco nuevo** | Seagate ST2000LM007-1R8174 2 TB (SMR, 5400 rpm), `/dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ`, serie WDZ03YJJ, como paridad tras superar la prueba de la fase B; el WD WD10JPVX (serie WD-WXU1EB6APMW5, antigua paridad) pasa a d1 |
| **Inventario** | state/config/montajes.md (2026-10-13); sin inventario YAML posterior |
| **Riesgo máximo** | Destructivo |

## Resumen

El Toshiba de d1 se ha degradado (sectores pendientes e ilegibles crecientes, errores UNC) y el
usuario ya lo ha sacado de la bahía 1. **No se reconstruye con `snapraid fix`**: la paridad solo
llegó al 99 % con 7 bloques ilegibles, sus ~293 GB son copia de los PCs (originales en D: de cada
PC) y el WD de la paridad se reutiliza como datos. Los datos se recuperan recopiándolos con
FreeFileSync. Riesgo aceptado por el usuario: entre la fase A y el final del sync de la fase C el
pool no tiene paridad; los originales siguen en los PCs.

Escenario: el caso es un fallo de disco de datos con paridad nueva más grande, pero se registra
como **Retirada** porque d1 se retira sin `snapraid fix` (los datos se recuperan recopiándolos
desde los PCs, no desde la paridad); el escenario «Fallo de disco de datos» exige reconstruir con
`fix`, que aquí no es posible ni útil.

Plan en tres fases:

- **Fase A (inmediata)**: desactivar el sync de las 23:30, quitar d1 y la paridad del array,
  borrar `snapraid.parity` del WD, etiquetarlo `d1`, montar el pool con WD + QVO y recopiar.
- **Fase B (prueba del Seagate)**: borrado y escritura completa del Seagate y criterios de
  aceptación por SMART (197 = 0, 198 = 0, 5 estable, test largo sin errores, sin pendientes nuevos
  a las 24 h). Si no los cumple, se descarta (queda para la Pi 4) y se compra un CMR ≥ 2 TB; este
  DCP se actualiza con el disco nuevo y la fase C se ejecuta con él.
- **Fase C (si pasa)**: ext4 `parity` en el Seagate, array SnapRAID `nas` con paridad Seagate,
  d1 WD y d2 QVO, content en d1, d2 y SSD, tarea de las 23:30 reactivada y sync completo (lento
  por ser SMR).

## Diagnóstico

- Toshiba MK1059GSM Y1NDFAQES: atributo 197 (Current_Pending_Sector) de 0 a 64 y 198
  (Offline_Uncorrectable) de 0 a 5 en dos días, 29 errores ATA en el registro SMART, `UNC` en
  `dmesg`; el sync inicial de SnapRAID terminó con 7 `io error` de lectura en d1. Disco
  degradándose: retirado (no vuelve al NAS).
- Paridad WD WD10JPVX WD-WXU1EB6APMW5 (ext4 `parity`, UUID `a31e93cf-80b6-404a-84e3-535f60c44009`,
  mntent `1901249d…`): sana, contiene `snapraid.parity` incompleto (99 %) que no sirve para un fix.
- d2 Samsung 870 QVO S5SVNG0N868475F (UUID `56801884-fc00-4ec8-a648-6135b2047cde`, mntent
  `96abea2b…`, ~294 GB): intacto.
- Pool MergerFS `pool` (uuid `a64bbd9e-4639-481d-a415-fd4745764fa8`) desmontado porque falta d1;
  array SnapRAID `nas` `358857d2-7c5b-415d-a2e0-3997c6f6b385`.
- Seagate ST2000LM007-1R8174 WDZ03YJJ (2 TB, 2,5", 5400 rpm, **SMR**, partición NTFS con ~35 MB de
  configuración de un servidor de descargas que el usuario autoriza borrar). SMART: 5 = 0,
  187 = 408 (normalizado 001, por debajo de cualquier umbral razonable), 188 muy alto, 193 = 116263
  ciclos de carga, 197 = 8, 198 = 8, 4803 h. Es un candidato dudoso: los 8 pendientes pueden ser
  sectores mal escritos que se resuelven al reescribirlos (197 → 0 sin subir 5) o sectores físicamente
  malos (5 sube o 197/198 no bajan). La fase B lo decide. SMR como paridad: válido para SnapRAID
  (escritura secuencial grande), pero el sync completo será lento.
- Backup restic: aún no operativo (fase de backups pendiente). El respaldo real de los datos del
  pool son los originales en los PCs (Documentos/Imágenes en D:), por eso se acepta el riesgo.
- `Videos` ya no existe como carpeta compartida (eliminada por el usuario) y el aviso de loadavg de
  monit se desactivó el 2026-10-13 (memory/ops/session-2026-10-13.md); se reflejan en el HLD.

## Situación de partida

| Rol | Disco | Tamaño | Estado |
|---|---|---|---|
| Paridad | WD WD10JPVX (WD-WXU1EB6APMW5), bahía 3 | 1 TB | Bien; `snapraid.parity` al 99 % con 7 bloques malos |
| D1 | Toshiba MK1059GSM (Y1NDFAQES), bahía 1 | 1 TB | Degradado, ya retirado físicamente |
| D2 | Samsung 870 QVO (S5SVNG0N868475F), bahía 4 | 1 TB | Bien, ~294 GB |
| Candidato | Seagate ST2000LM007 (WDZ03YJJ), fuera del NAS | 2 TB | Sin probar (197 = 8, 198 = 8) |

## Situación final

| Rol | Disco | Tamaño | Sistema de ficheros | En pool | Content |
|---|---|---|---|---|---|
| Sistema | SSD del sistema (raíz) | 512 GB | ext4 | No | Sí |
| Paridad | Seagate ST2000LM007 (WDZ03YJJ), bahía 1 | 2 TB | ext4 (0 % reservado) | No | No |
| D1 | WD WD10JPVX (WD-WXU1EB6APMW5), bahía 3 | 1 TB | ext4 (0 % reservado) | Sí | Sí |
| D2 | Samsung 870 QVO (S5SVNG0N868475F), bahía 4 | 1 TB | ext4 (0 % reservado) | Sí | Sí |

## Precondiciones

- [ ] Sync programado de SnapRAID (tarea Cron de las 23:30) desactivado antes de tocar el array (paso 1)
- [ ] Backup: restic aún no operativo; el usuario confirma que los originales de lo que había en el pool siguen en los PCs (D:) y no los borra hasta terminar la fase C
- [ ] Toshiba Y1NDFAQES fuera del NAS y guardado aparte, etiquetado "degradado — no usar"
- [ ] Nadie escribe en el pool salvo la recopia de FreeFileSync: pausar la subida automática de los móviles hasta el final del sync de la fase C
- [ ] Consolas: cada orden es una sola línea `ssh -t nas "…"`; no pegar varias líneas tras `ssh nas`

## Pasos

### Fase A — Pool sin paridad con WD como d1 (inmediata)

### Paso 1: Desactivar el sync programado de las 23:30

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando (primero se lista; el uuid de la tarea se copia exacto de la salida):

```bash
ssh -t nas "sudo omv-rpc -u admin Cron getList '{\"start\":0,\"limit\":-1,\"type\":[\"userdefined\"]}'"
ssh -t nas "sudo omv-rpc -u admin Cron set '{\"uuid\":\"<uuid-tarea-snapraid-listado>\",\"enable\":false,\"execution\":\"exactly\",\"minute\":[\"30\"],\"everynminute\":false,\"hour\":[\"23\"],\"everynhour\":false,\"dayofmonth\":[\"*\"],\"everyndayofmonth\":false,\"month\":[\"*\"],\"dayofweek\":[\"*\"],\"username\":\"root\",\"command\":\"/usr/sbin/omv-snapraid-diff\",\"sendemail\":true,\"comment\":\"SnapRAID diff/sync/scrub\"}'"
ssh -t nas "sudo omv-salt deploy run cron"
ssh -t nas "sudo omv-rpc -u admin Cron getList '{\"start\":0,\"limit\":-1,\"type\":[\"userdefined\"]}' | grep -o '\"enable\":[a-z]*' | sort | uniq -c"
```

Esperado: una sola tarea `omv-snapraid-diff` con `"enable":false`; `grep -c omv-snapraid-diff /etc/cron.d/openmediavault-userdefined` da 0.

Si falla: si no se puede desactivar, no se sigue: un sync sin paridad válida dejaría un array incoherente; se anota en el OPS y para.

### Paso 2: Confirmar discos y estado sin tocar nada

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh -t nas "lsblk -o NAME,SIZE,MODEL,SERIAL,LABEL,MOUNTPOINT"
ssh -t nas "ls -l /dev/disk/by-id/ | grep -v part"
ssh -t nas "sudo omv-rpc -u admin SnapRaid getDriveList '{\"start\":0,\"limit\":-1}'"
```

Esperado: solo el SSD del sistema, el WD (WD-WXU1EB6APMW5, label `parity`) y el QVO (S5SVNG0N868475F, label `d2`); ningún Toshiba. SnapRAID lista parity, d1, d2 y ssd; se anotan los uuid de las unidades `parity` y `d1`.

Si falla: si aparece el Toshiba, para: el usuario lo retira antes de seguir.

### Paso 3: Quitar d1 (Toshiba) y parity (WD) del array SnapRAID

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando (uuid exactos del paso 2):

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid deleteDrive '{\"uuid\":\"<uuid-unidad-d1-listado>\"}'"
ssh -t nas "sudo omv-rpc -u admin SnapRaid deleteDrive '{\"uuid\":\"<uuid-unidad-parity-listado>\"}'"
ssh -t nas "sudo omv-salt deploy run snapraid"
ssh -t nas "sudo omv-rpc -u admin SnapRaid getDriveList '{\"start\":0,\"limit\":-1}' | grep -o '\"name\":\"[^\"]*\"' | sort | uniq -c"
```

Esperado: quedan solo `d2` y `ssd`, cada uno una vez; `grep -c '^parity\|^data d1' /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf` da 0.

Si falla: si `deleteDrive` no existe, lee los métodos con `sudo omv-rpc -u admin SnapRaid getDrive '{\"uuid\":\"…\"}'`, anótalo en el OPS y para.

### Paso 4: Quitar el sistema de ficheros del Toshiba de OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

El Toshiba ya no está; su entrada de montaje (`16149efb…`, UUID `1d82d7b3-ca0f-460f-8356-23b5e46ecf79`) impediría montar el pool y generaría avisos.

Comando:

```bash
ssh -t nas "sudo omv-confdbadm read conf.system.filesystem.mountpoint | grep -o '\"uuid\": *\"[^\"]*\"\|\"fsname\": *\"[^\"]*\"'"
ssh -t nas "sudo omv-rpc -u admin FsTab delete '{\"uuid\":\"<uuid-mntent-toshiba-listado>\"}'"
ssh -t nas "sudo omv-salt deploy run fstab"
ssh -t nas "grep -c 1d82d7b3-ca0f-460f-8356-23b5e46ecf79 /etc/fstab"
```

Esperado: el último comando da 0.

Si falla: si OMV lo rechaza porque el pool lo referencia, haz primero el paso 6 y vuelve a este; anótalo en el OPS.

### Paso 5: Borrar `snapraid.parity` del WD y etiquetarlo `d1`

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |

Comprobación previa:

```bash
ssh -t nas "lsblk -o NAME,SIZE,MODEL,SERIAL,LABEL,UUID /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5"
ssh -t nas "ls -la /srv/dev-disk-by-uuid-a31e93cf-80b6-404a-84e3-535f60c44009/"
```

Debe salir serie WD-WXU1EB6APMW5, label `parity`, UUID `a31e93cf-80b6-404a-84e3-535f60c44009` y en la raíz solo `snapraid.parity` y `lost+found`.

Comando (una orden por línea):

```bash
ssh -t nas "sudo rm /srv/dev-disk-by-uuid-a31e93cf-80b6-404a-84e3-535f60c44009/snapraid.parity"
ssh -t nas "sudo e2label /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5-part1 d1"
```

Esperado: `ls` muestra solo `lost+found`; `lsblk -o NAME,LABEL,UUID` muestra el WD con label `d1` y el **mismo** UUID (el montaje de OMV no cambia).

Si falla: si `-part1` no existe, usa la ruta by-id exacta que muestre `ls -l /dev/disk/by-id/ | grep WD-WXU1EB6APMW5` (sin comodines).

### Paso 6: Pool MergerFS con WD (d1) y QVO (d2)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando:

```bash
ssh -t nas "sudo omv-rpc -u admin Mergerfs set '{\"uuid\":\"a64bbd9e-4639-481d-a415-fd4745764fa8\",\"name\":\"pool\",\"mntentref\":\"5cb09afe-def1-407f-a7ec-6e8c839e844d\",\"filesystems\":[\"<mntent-WD-1901249d-completo>\",\"<mntent-QVO-96abea2b-completo>\"],\"paths\":null,\"sharedfolderrefs\":[],\"createpolicy\":\"mfs\",\"minfreespace\":20,\"minfreespaceunit\":\"G\",\"options\":\"cache.files=off,dropcacheonclose=true,category.search=ff\"}'"
ssh -t nas "sudo omv-salt deploy run mergerfs"
ssh -t nas "sudo omv-rpc -u admin Mergerfs getList '{\"start\":0,\"limit\":-1}' | grep -o '\"name\":\"[^\"]*\"' | sort | uniq -c"
ssh -t nas "findmnt -o TARGET,SOURCE,FSTYPE,SIZE /srv/mergerfs/pool"
```

Los mntent completos se copian de la salida del paso 4.

Esperado: un único pool `pool`; `findmnt` muestra `fuse.mergerfs` de ~1,8 T; `ls /srv/mergerfs/pool` muestra las carpetas compartidas del QVO.

Si falla: si el deploy da `Failed`, `sudo journalctl -u srv-mergerfs-pool.mount -n 30` y para.

### Paso 7: Recopiar desde los PCs con FreeFileSync

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC (FreeFileSync contra las carpetas Samba del NAS) |

En cada PC, sincronización **Actualizar** (→, nunca Espejo ni bidireccional) de los originales en
D: hacia la carpeta compartida correspondiente. Solo copia lo que falta. Filtro de exclusión:
`._sync_*` y `.owncloudsync.log`. Compara primero y revisa que no hay borrados en el lado NAS.

Esperado: FreeFileSync termina sin errores; `ssh -t nas "df -h /srv/dev-disk-by-uuid-a31e93cf-80b6-404a-84e3-535f60c44009 /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde"` muestra ~293 GB nuevos repartidos (sobre todo en el WD).

Si falla: errores de permisos → revisar usuario Samba (RBK 08); el resto se reintenta, nunca se borra en los PCs.

### Fase B — Prueba del Seagate (decide si sirve)

### Paso 8: Instalar el Seagate en la bahía 1 e identificarlo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |

Apaga con `ssh -t nas "sudo poweroff"`, espera a que el LED verde deje de parpadear, desenchufa la
alimentación del HAT, pon el Seagate en la bahía 1 (la del Toshiba; los mecánicos Seagate y WD
quedan separados por la bahía 2 vacía) y arranca. Luego el Agente lee:

```bash
ssh -t nas "lsblk -b -o NAME,SIZE,MODEL,SERIAL,FSTYPE"
ssh -t nas "sudo smartctl -a /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
```

Esperado: Seagate serie WDZ03YJJ de 2000398934016 bytes con partición NTFS; SMART con 5 = 0, 197 = 8, 198 = 8 (anotar todos los valores brutos en el OPS como línea base).

Si falla: si no aparece, revisa el conector de la bahía; si 5 > 0 o 197 > 8 ya antes de empezar, se anota y se sigue con la prueba (la decide el paso 11).

### Paso 9: Borrar firmas y escribir el disco entero

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |

Comprobación previa:

```bash
ssh -t nas "lsblk -o NAME,SIZE,MODEL,SERIAL"
ssh -t nas "readlink -f /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
```

Confirma que la ruta apunta al disco de 1,8 T con serie WDZ03YJJ y que no es el WD ni el QVO ni el SSD.

Comando (una orden por línea; `systemd-run` para que no se corte si se cae el SSH; dura muchas horas por ser SMR):

```bash
ssh -t nas "sudo wipefs -a /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
ssh -t nas "sudo systemd-run --unit=prueba-seagate badblocks -wsv -b 4096 -t 0 -o /root/badblocks-WDZ03YJJ.txt /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
ssh -t nas "sudo journalctl -u prueba-seagate -n 5 --no-pager"
```

Alternativa equivalente si `badblocks` no está: `sudo systemd-run --unit=prueba-seagate dd if=/dev/zero of=/dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ bs=1M oflag=direct status=progress`.

Esperado: `wipefs` borra la firma NTFS; al terminar, `journalctl -u prueba-seagate` muestra `Pass completed, 0 bad blocks found` y `/root/badblocks-WDZ03YJJ.txt` vacío.

Si falla: cualquier bloque malo o error de E/S en `dmesg` → disco descartado (paso 11, rama "no pasa").

### Paso 10: Test SMART largo

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh -t nas "sudo smartctl -t long /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
ssh -t nas "sudo smartctl -l selftest -A /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
```

(El segundo, cuando haya pasado el tiempo que indica el primero, ~5 h.)

Esperado: `Extended offline  Completed without error`; 197 = 0, 198 = 0, 5 igual a la línea base.

Si falla: test con `read failure` o 197/198 > 0 → descartado.

### Paso 11: Decisión a las 24 h

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando (24 h después del paso 10):

```bash
ssh -t nas "sudo smartctl -A -l error /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
```

Criterios de aceptación, todos: 197 = 0, 198 = 0, 5 sin cambios desde la línea base, test largo sin errores, ningún error ATA nuevo en el registro respecto al paso 8.

Esperado: los cinco criterios se cumplen → se sigue con la fase C.

Si falla: **no pasa**: el Seagate se retira (queda para la Pi 4 de descargas, sin datos importantes), el NAS sigue sin paridad con el pool de la fase A, y se compra un disco CMR ≥ 2 TB (comprobar en la ficha del fabricante que no es SMR). Este DCP se actualiza con `/storage-plugin:update-dcp` con el modelo y serie del disco nuevo antes de la fase C.

### Fase C — Seagate como paridad y sync completo (solo si pasa)

### Paso 12: Crear ext4 `parity` en el Seagate

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comprobación previa:

```bash
ssh -t nas "lsblk -o NAME,SIZE,MODEL,SERIAL,FSTYPE"
ssh -t nas "readlink -f /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
```

Confirma serie WDZ03YJJ, 1,8 T, sin sistema de ficheros.

Comando:

```bash
ssh -t nas "sudo omv-rpc -u admin FileSystemMgmt create '{\"devicefile\":\"/dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ\",\"type\":\"ext4\",\"label\":\"parity\"}'"
ssh -t nas "lsblk -o NAME,SIZE,SERIAL,FSTYPE,LABEL,UUID /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"
ssh -t nas "sudo tune2fs -l /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ-part1 | grep -i 'reserved block count'"
```

Esperado: partición ext4 label `parity` con UUID nuevo (se anota); `Reserved block count: 0` (OMV formatea con `-m 0`).

Si falla: si el bloque reservado no es 0, el usuario ejecuta `sudo tune2fs -m 0 /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ-part1` tras repetir la comprobación previa.

### Paso 13: Montar el sistema de ficheros nuevo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando:

```bash
ssh -t nas "sudo omv-rpc -u admin FileSystemMgmt setMountPoint '{\"id\":\"/dev/disk/by-uuid/<uuid-nuevo-paso-12>\"}'"
ssh -t nas "sudo omv-salt deploy run fstab"
ssh -t nas "findmnt /srv/dev-disk-by-uuid-<uuid-nuevo-paso-12>"
ssh -t nas "sudo omv-confdbadm read conf.system.filesystem.mountpoint | grep -c <uuid-nuevo-paso-12>"
```

Esperado: montado en `/srv/dev-disk-by-uuid-<uuid>` con 1,8 T; el grep da 1 (sin duplicados); se anota el mntent nuevo.

Si falla: si el método se llama distinto en OMV 8, `sudo omv-rpc -u admin FileSystemMgmt getList '{\"start\":0,\"limit\":-1}'`, se anota en el OPS y para.

### Paso 14: Apartar los content antiguos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |

Los content del array viejo describen al Toshiba y a la paridad incompleta; un sync con ellos fallaría por UUID cambiado. Se renombran (no se borran; `*.bak` ya está excluido).

Comando (una orden por línea):

```bash
ssh -t nas "sudo mv /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/snapraid.content /srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde/snapraid.content.2026-10-15.bak"
ssh -t nas "sudo mv /snapraid.content /snapraid.content.2026-10-15.bak"
ssh -t nas "sudo find / -xdev -maxdepth 1 -name 'snapraid.content*'"
```

Esperado: solo quedan los `.bak`; no hay `snapraid.content` en d2 ni en la raíz.

Si falla: si no existe alguno, se anota y se sigue.

### Paso 15: Array SnapRAID: parity Seagate, d1 WD, d2 QVO

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando:

```bash
ssh -t nas "sudo omv-rpc -u admin SnapRaid setDrive '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"arrayref\":\"358857d2-7c5b-415d-a2e0-3997c6f6b385\",\"mntentref\":\"<mntent-seagate-paso-13>\",\"name\":\"parity\",\"parity\":true,\"paritynum\":1,\"data\":false,\"content\":false}'"
ssh -t nas "sudo omv-rpc -u admin SnapRaid setDrive '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"arrayref\":\"358857d2-7c5b-415d-a2e0-3997c6f6b385\",\"mntentref\":\"<mntent-WD-1901249d-completo>\",\"name\":\"d1\",\"parity\":false,\"paritynum\":1,\"data\":true,\"content\":true}'"
ssh -t nas "sudo omv-salt deploy run snapraid"
ssh -t nas "sudo omv-rpc -u admin SnapRaid getDriveList '{\"start\":0,\"limit\":-1}' | grep -o '\"name\":\"[^\"]*\"' | sort | uniq -c"
ssh -t nas "grep -E '^(parity|data|content)' /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf"
```

Esperado: `parity`, `d1`, `d2`, `ssd` una vez cada uno; la conf tiene `parity /srv/dev-disk-by-uuid-<uuid-seagate>/snapraid.parity`, `data d1 /srv/dev-disk-by-uuid-a31e93cf-…`, `data d2 /srv/dev-disk-by-uuid-56801884-…` y tres `content` (d1, d2, raíz).

Si falla: si sale un duplicado, `deleteDrive` del sobrante y repetir el deploy.

### Paso 16: Sync completo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh -t nas "sudo systemd-run --unit=snapraid-sync-inicial snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf sync"
ssh -t nas "sudo journalctl -u snapraid-sync-inicial -n 20 --no-pager"
```

Esperado: termina con `Everything OK` y 0 errores (varias horas: Seagate SMR y ~590 GB de datos). No escribir en el pool mientras dura.

Si falla: errores de lectura en d1/d2 → `/storage-plugin:diagnose-disk` de ese disco; errores de escritura en la paridad → Seagate descartado, volver a la rama "no pasa" del paso 11.

### Paso 17: Reactivar la tarea de las 23:30

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`) |

Comando:

```bash
ssh -t nas "sudo omv-rpc -u admin Cron set '{\"uuid\":\"<uuid-tarea-snapraid-listado>\",\"enable\":true,\"execution\":\"exactly\",\"minute\":[\"30\"],\"everynminute\":false,\"hour\":[\"23\"],\"everynhour\":false,\"dayofmonth\":[\"*\"],\"everyndayofmonth\":false,\"month\":[\"*\"],\"dayofweek\":[\"*\"],\"username\":\"root\",\"command\":\"/usr/sbin/omv-snapraid-diff\",\"sendemail\":true,\"comment\":\"SnapRAID diff/sync/scrub\"}'"
ssh -t nas "sudo omv-salt deploy run cron"
ssh -t nas "grep -c omv-snapraid-diff /etc/cron.d/openmediavault-userdefined"
```

Esperado: el grep da 1 (una única tarea, sin duplicados).

Si falla: si da 2, borrar la tarea sobrante con `Cron delete` y su uuid exacto.

### Paso 18: hd-idle, SMART y foto de la configuración

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH y PC |

En hd-idle (si la fase 09 ya está aplicada) se sustituye `ata-TOSHIBA_MK1059GSM_Y1NDFAQES` por `/dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ` con el mismo tiempo; en la vigilancia SMART de OMV se activa el Seagate y se quita el Toshiba. Después `/operator-plugin:snapshot-config` y se actualiza `state/config/montajes.md`.

Comando:

```bash
ssh -t nas "grep -c TOSHIBA /etc/default/hd-idle"
ssh -t nas "grep -c WDZ03YJJ /etc/default/hd-idle"
```

Esperado: 0 y 1; `state/config/` refleja la nueva conf de SnapRAID y montajes.

Si falla: si hd-idle no está instalado todavía, se anota y lo recoge el RBK 09.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Discos | `ssh -t nas "lsblk -o NAME,SIZE,MODEL,SERIAL,LABEL"` | Seagate WDZ03YJJ `parity`, WD WD-WXU1EB6APMW5 `d1`, QVO `d2`; sin Toshiba |
| SnapRAID | `ssh -t nas "sudo snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf status"` | Sin errores, 0 % sin sincronizar |
| Diff | `ssh -t nas "sudo snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf diff"` | `No differences` |
| Pool | `ssh -t nas "findmnt -o TARGET,FSTYPE,SIZE /srv/mergerfs/pool"` | `fuse.mergerfs` ~1,8 T (sin el Seagate) |
| Tarea 23:30 | `ssh -t nas "grep -c omv-snapraid-diff /etc/cron.d/openmediavault-userdefined"` | 1 |
| SMART Seagate | `ssh -t nas "sudo smartctl -A /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ"` | 197 = 0, 198 = 0, 5 sin cambios |

## Vuelta atrás

- Fase A: hasta el paso 5 todo es reversible (volver a añadir parity y d1 con `setDrive`, reactivar la tarea). Desde el paso 5 la paridad vieja ya no existe; no había vuelta atrás útil de todos modos (99 % con 7 bloques malos y d1 retirado). El estado seguro es el pool sin paridad con la tarea 23:30 desactivada y los originales en los PCs.
- Fase B: si el Seagate no pasa, se saca y el NAS sigue en el estado de la fase A hasta tener un disco CMR ≥ 2 TB; nada del NAS cambia.
- Fase C: si el sync falla o el Seagate da errores, se desactiva de nuevo la tarea de las 23:30 (paso 1), se quita la unidad `parity` del array y se vuelve a la rama "no pasa". Los content antiguos `.bak` no se reutilizan.
- Los originales en los PCs no se borran hasta que la verificación final está en verde y el backup restic funcione.

## Cambios en el diseño

- HLD (`/architect-plugin:update-hld`): bahías (1 = Seagate paridad, 2 = vacía, 3 = WD d1, 4 = QVO d2); paridad de 2 TB Seagate ST2000LM007 (SMR, aceptado para paridad, ADR nuevo); Toshiba MK1059 retirado por degradación; WD pasa de paridad a datos; carpeta `Videos` eliminada; aviso de loadavg de monit desactivado; riesgo nuevo "paridad SMR usada y con historial (187 = 408)" con vigilancia mensual.
- SnapRAID: parity → Seagate (`snapraid.parity` en su raíz), d1 → WD (UUID `a31e93cf-80b6-404a-84e3-535f60c44009`, label `d1`), d2 sin cambios; content en d1, d2 y SSD (3 ≥ paridades + 1).
- MergerFS: ramas WD (d1) y QVO (d2); el Seagate nunca entra en el pool.
- hd-idle: Toshiba fuera, Seagate dentro por `/dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ`.
- SMART: vigilancia del Seagate en OMV con test corto semanal; seguimiento de 5, 187, 197 y 198 en cada MNT.
- `state/config/montajes.md` y conf de SnapRAID actualizados con `/operator-plugin:snapshot-config`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-15 | Storage Agent | Creación |
| 1.0 | 2026-10-15 | Storage Agent | Estado cambiado a Aprobado. Visto bueno del usuario 2026-10-15 ("intenta usar el hdd de 2T, puedes formatear todo"). Excepción registrada: sin backup restic (fase 11 pendiente); riesgo aceptado por el usuario porque los originales de todos los datos están en los PCs (D:\Imagenes, D:\Documentos). Aviso aceptado: sin inventario YAML de referencia |
