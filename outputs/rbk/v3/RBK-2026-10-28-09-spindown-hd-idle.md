# RBK 09 — Spindown con hd-idle

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 09 — Spindown con hd-idle |
| **Versión** | 3.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-28 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h + 45 min de espera + 24 h de seguimiento (+ 7 días si se aplica APM) |

## Objetivo

Parar los dos mecánicos —paridad Seagate ST2000LM007 (serie WDZ03YJJ) y d1 WD Blue WD10JPVX
(serie WD-WXU1EB6APMW5)— tras 45 minutos sin uso con hd-idle, con `-i 0` por defecto para no
parar el XG5 ni el QVO (d2), sin el spindown de OMV, y medir el atributo 193 de los dos para
decidir APM 254 (HLD v3 §9, ADR-006, ADR-025). El Toshiba MK1059 ya no está (ADR-025).

Reparto de mecanismos, sin duplicar (comprobado en el NAS el 2026-10-28):

| Mecanismo | Quién lo gestiona | Valor |
|---|---|---|
| Parada del motor (standby) | **solo hd-idle** | 2 700 s en Seagate y WD; `-i 0` el resto |
| Temporizador de standby del disco (`-S`) | OMV `conf.system.hdparm` → `smartctl --set=standby,off` | apagado (`spindowntime` 0) |
| Aparcado de cabezales (APM) | OMV `conf.system.hdparm` → `smartctl --set=apm,254` | solo si el 193 sube > 100 al día (paso 10); si no, se deja el 128 de fábrica |

Punto de partida (2026-10-28 22:38, inventario y lectura): Seagate 193 = 116 618 (valor
normalizado 042), WD 193 = 82 146; los dos con APM 128 de fábrica (aparcan los cabezales a los
pocos segundos sin uso), `conf.system.hdparm` = `[]`, `hdparm` y `hd-idle` sin instalar. OMV 8
aplica APM y standby con `smartctl --set` desde `/etc/smartmontools/hdparm.d/` (servicio
`smartctl-hdparm`), así que **no hace falta instalar `hdparm`**: el estado se lee con
`smartctl -n standby`, que no despierta discos.

## Prerrequisitos

- [ ] UPD-2026-10-28-apt-immich ejecutado y su OPS cerrado (este RBK va después)
- [ ] DCP-2026-10-15 fase C hecha: paridad Seagate sincronizada (`snapraid status` sin errores)
- [ ] Fuera de la ventana 23:00-01:00 (tarea SnapRAID diff+sync de OMV a las 23:30) para que los pasos 8 y 9 midan sin el sync en curso
- [ ] Sin sesión web: todos los pasos los hace el Agente por SSH, una orden por línea; no pegues varias líneas tras `ssh nas`

## Pasos

### Paso 1: Comprobar que OMV no gestiona spindown ni APM

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'sudo omv-confdbadm read conf.system.hdparm; ls /etc/smartmontools/hdparm.d/'
```

Esperado: `[]` y ningún fichero `openmediavault-<uuid>` en `hdparm.d` (comprobado el 2026-10-28). Así hd-idle será el único que pare los discos.

Si falla: si sale algún objeto con `spindowntime` distinto de 0, para: ponerlo a 0 requiere un cambio aprobado (`DiskMgmt setHdParm`, como en el paso 10) antes de seguir; dos mecanismos de parada a la vez se pisan.

### Paso 2: Localizar los nombres estables

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, §9 |

Comando:

```bash
ssh nas 'ls -l /dev/disk/by-id/ | grep -v part | grep ^l | grep ata-'
```

Esperado: `ata-ST2000LM007-1R8174_WDZ03YJJ`, `ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5` y `ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F` (el QVO no se para), más el XG5 de arranque. Se comparan por número de serie (WDZ03YJJ, WD-WXU1EB6APMW5) con el HLD §5; la letra `sdX` no importa. Si una serie no coincide, para. No debe aparecer `TOSHIBA_MK1059GSM`.

Si falla: si no aparecen, comprueba los discos con `ssh nas 'lsblk -o NAME,SIZE,MODEL,SERIAL'`.

### Paso 3: Comprobar que nada más despierta los mecánicos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, §10 |

Comando:

```bash
ssh nas "grep -c 'n standby' /etc/smartd.conf; grep -E '^[0-9]' /etc/cron.d/openmediavault-userdefined | cut -c1-40; systemctl list-timers --all --no-pager | grep -E 'snapraid|nas-temp'"
```

Esperado: `1` (smartd con `-n standby,q`: no despierta discos); la tarea `30 23 * * *` (SnapRAID diff+sync); si ya está aplicado el RBK 16, `snapraid-content-vigila.timer` a las 12:00 (solo lee `/snapraid.content` del SSD: no despierta los mecánicos) y `nas-temp` si existe (usa `smartctl -n standby`). Los tests SMART de smartd (corto el sábado a las 10:00, largo el día 15) sí los despiertan: es lo previsto.

Si falla: si smartd no tiene `-n standby` o hay otra tarea que lea el pool o la paridad fuera de 23:00-01:00, para y anótalo: los discos no pararán y hay que corregirlo antes (UPD o RBK aparte).

### Paso 4: Leer el atributo 193 y el APM de los dos mecánicos (base)

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, §12 |

Comandos (uno por línea):

```bash
ssh nas "date '+%F %H:%M'; sudo smartctl -n standby -g apm -A /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ | grep -E 'APM|^ *(4|9|193) '"
ssh nas "date '+%F %H:%M'; sudo smartctl -n standby -g apm -A /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 | grep -E 'APM|^ *(4|9|193) '"
```

Esperado: `APM level is: 128` en los dos y los valores de 4 (Start_Stop_Count), 9 (horas) y 193 (Load_Cycle_Count) anotados en el OPS con fecha y hora. Referencia del 2026-10-28 22:38: Seagate 193 = 116 618, WD 193 = 82 146.

Si falla: si el disco está en standby, `smartctl` sale con código 2 sin leer: anótalo y repite tras el sync de las 23:30 (no lo despiertes solo para esto). Si no aparece el 193 o `APM` sale `Unavailable`, anótalo: el paso 10 no se aplica a ese disco.

### Paso 5: Instalar hd-idle

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, §11 |

Comando:

```bash
ssh nas 'sudo apt-get install -y hd-idle && dpkg-query -W hd-idle'
```

Esperado: `hd-idle 1.21+ds-1+b8` (candidato de Trixie el 2026-10-28; versión en Go de adelolmo). No se instala `hdparm`.

Si falla: si no está en el repositorio o la versión es otra, para y prepara un UPD.

### Paso 6: Comprobar las opciones de esta versión de hd-idle

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "hd-idle -h 2>&1 | grep -E -- '^ *-(a|i|l|c) '; systemctl is-active hd-idle; grep -c '^START_HD_IDLE=false' /etc/default/hd-idle"
```

Esperado: aparecen `-a` (acepta enlaces simbólicos, como `/dev/disk/by-id/…`), `-i`, `-l` y `-c`; el servicio `inactive` (el paquete trae `START_HD_IDLE=false`, `1`). Fuente: `hd-idle -h` del paquete instalado y README de https://github.com/adelolmo/hd-idle.

Si falla: si `-a` no acepta enlaces o falta alguna opción, para: no se configura con `/dev/sdX` (HLD §5); corrige el runbook.

### Paso 7: Enviar /etc/default/hd-idle desde el repo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | PC (repo) → NAS por SSH |
| **HLD** | §9 |

Fichero `state/config/etc/default/hd-idle` (valores ya puestos):

```text
START_HD_IDLE=true
HD_IDLE_OPTS="-i 0 -a /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ -i 2700 -a /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 -i 2700 -l /var/log/hd-idle.log"
```

Comandos (desde la raíz del repo, uno por línea):

```bash
cat state/config/etc/default/hd-idle | ssh nas "sudo tee /etc/default/hd-idle >/dev/null"
ssh nas "grep -c '^HD_IDLE_OPTS=' /etc/default/hd-idle; grep -c '^START_HD_IDLE=true$' /etc/default/hd-idle; grep -o 'by-id/[^ ]*' /etc/default/hd-idle"
ssh nas 'sudo systemctl enable hd-idle && sudo systemctl restart hd-idle && systemctl is-active hd-idle'
```

Esperado: `1`, `1` y los dos by-id (Seagate y WD); `active`. El QVO, el XG5 y cualquier otro disco quedan con `-i 0`.

Si falla: si se equivoca un nombre, hd-idle no para ese disco: corrige el fichero del repo y repite. Si no arranca, `ssh nas 'sudo journalctl -u hd-idle -n 30 --no-pager'`.

### Paso 8: Comprobar el standby tras 45 minutos sin uso

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Esperar ≥ 50 minutos sin uso del pool (sin subidas de Immich, sin Nextcloud desde un PC). Comandos (uno por línea):

```bash
ssh nas "sudo smartctl -n standby -i /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ | grep -E 'STANDBY|Power mode'"
ssh nas "sudo smartctl -n standby -i /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 | grep -E 'STANDBY|Power mode'"
ssh nas "sudo smartctl -n standby -i /dev/disk/by-id/ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F | grep -E 'STANDBY|Power mode'"
ssh nas 'sudo tail -n 20 /var/log/hd-idle.log'
```

Esperado: Seagate y WD `Device is in STANDBY mode`; QVO `Power mode is: ACTIVE or IDLE`; el registro de hd-idle con la parada de los dos. `smartctl -n standby` no despierta discos.

Si falla: si un mecánico sigue activo, mira qué lo usa con `ssh nas 'sudo lsof +D /srv/mergerfs/pool 2>/dev/null | head'` y el registro de hd-idle. Si hd-idle anota la parada pero el disco vuelve a girar enseguida, o no llega a pararse, añade `-c ata` antes de su `-a` en el fichero del repo, repite el paso 7 y vuelve a medir.

### Paso 9: Leer el atributo 193 a las 24 h

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, §12 |

Comandos: los dos del paso 4, 24 h después (fuera de 23:00-01:00).

Esperado: nuevos valores en el OPS y la subida de 193 en 24 h de cada disco (y la de 4, que cuenta las paradas de hd-idle). Decisión por disco: subida > 100 → paso 10; ≤ 100 → «APM sin cambio».

Si falla: si un disco está parado (código 2), espera a que despierte con el sync de las 23:30 o léelo al día siguiente y prorratea: no lo despiertes solo para esto.

### Paso 10: APM 254 en el mecánico cuyo 193 suba más de 100 al día

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | PC (repo) → NAS por SSH |
| **HLD** | §9, §12 |

Solo para el disco (o los dos) con subida > 100 en el paso 9; si ninguno, se anota «APM sin cambio» y se salta a la verificación. APM 254 deja de aparcar los cabezales mientras el disco gira; la parada sigue siendo de hd-idle (`spindowntime` 0 hace que OMV ponga `--set=standby,off`, sin segundo mecanismo). Ficheros ya preparados con los valores puestos (`uuid` nuevo = `OMV_CONFIGOBJECT_NEW_UUID`):

- `state/config/omv/hdparm-seagate-setHdParm.json`
- `state/config/omv/hdparm-wd-setHdParm.json`

Comandos (desde la raíz del repo, uno por línea; la primera solo si toca el Seagate, la segunda solo si toca el WD):

```bash
cat state/config/omv/hdparm-seagate-setHdParm.json | ssh nas 'sudo omv-rpc -u admin DiskMgmt setHdParm "$(cat)" >/dev/null && echo set-ok'
cat state/config/omv/hdparm-wd-setHdParm.json | ssh nas 'sudo omv-rpc -u admin DiskMgmt setHdParm "$(cat)" >/dev/null && echo set-ok'
ssh nas 'sudo omv-salt deploy run smartmontools'
ssh nas "sudo omv-confdbadm read conf.system.hdparm | grep -o '\"devicefile\"' | wc -l; sudo omv-confdbadm read conf.system.hdparm | grep -o 'ata-[A-Z0-9_-]*' | sort | uniq -d | wc -l; ls /etc/smartmontools/hdparm.d/ | grep -c '^openmediavault-'"
ssh nas "sudo smartctl -n standby -g apm /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ | grep APM; sudo smartctl -n standby -g apm /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 | grep APM"
```

Fuente: `rpc.diskmgmt.sethdparm` en `/usr/share/openmediavault/datamodels/rpc.diskmgmt.json` (uuid, devicefile, apm 0-255, aam 0/128/254, spindowntime 0-254, writecache) y `/srv/salt/omv/deploy/smartmontools/20hdparm.sls`, que genera `/etc/smartmontools/hdparm.d/openmediavault-<uuid>` con `smartctl --set=aam,off --set=apm,254 --set=standby,off --set=wcache,on` y reinicia `smartctl-hdparm` (también corre en cada arranque); leídos en el NAS el 2026-10-28. Si el comando `omv-rpc` se repite para el mismo disco crea un segundo objeto: el primer recuento lo detecta.

Esperado: `set-ok` por disco aplicado; recuentos = nº de discos aplicados (1 o 2), `0` duplicados, mismo nº de ficheros en `hdparm.d`; `APM level is: 254` en los discos aplicados y `128` en el que no.

Si falla: si sale un by-id duplicado, borra el objeto sobrante desde la web de OMV (Almacenamiento → Discos → editar) o con la vuelta atrás y redeploy. Si tras 7 días con APM 254 el 193 sigue subiendo > 100 al día, o el valor normalizado del 193 del Seagate (042 el 2026-10-28) baja de 030, pásalo al experto en discos (`/storage-plugin:diagnose-disk`).

### Paso 11: Comprobar que el APM sobrevive al standby

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Solo si se aplicó el paso 10. Al día siguiente, con los discos despiertos tras el sync de las 23:30 (o tras un acceso normal), repite la última orden del paso 10.

Esperado: `APM level is: 254` en los discos aplicados tras una parada y un despertar de hd-idle.

Si falla: si vuelve a `128`, el disco pierde el APM al despertar: anótalo como incidencia en el OPS y para; hace falta un cambio aparte (reaplicar al despertar) aprobado en un RBK nuevo.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Servicio | `ssh nas systemctl is-active hd-idle` | active |
| Arranca solo | `ssh nas systemctl is-enabled hd-idle` | enabled |
| Mecánicos parados | `ssh nas "sudo smartctl -n standby -i /dev/disk/by-id/ata-ST2000LM007-1R8174_WDZ03YJJ \| grep -c STANDBY"` y lo mismo con el WD | 1 y 1 (tras 45 min sin uso) |
| QVO y XG5 no paran | `ssh nas "grep -c 'OPTS=\"-i 0 ' /etc/default/hd-idle"` | 1 |
| Sin duplicados | `ssh nas "grep -c '^HD_IDLE_OPTS=' /etc/default/hd-idle"` | 1 |
| Igual que el repo | `cat state/config/etc/default/hd-idle \| ssh nas "sudo diff - /etc/default/hd-idle && echo igual"` | igual |
| Un solo mecanismo de parada | `ssh nas "sudo omv-confdbadm read conf.system.hdparm \| grep -o '\"spindowntime\": *[1-9]' \| wc -l"` | 0 |
| Sync nocturno sigue | `ssh nas "sudo snapraid status \| tail -3"` tras la noche | sin errores |

## Vuelta atrás

`ssh nas 'sudo systemctl disable --now hd-idle'` (los discos vuelven a girar siempre, como antes
de este RBK). APM (si se aplicó el paso 10): repetir `DiskMgmt setHdParm` con el `uuid` del
objeto creado (`sudo omv-confdbadm read conf.system.hdparm`) y `apm` 128 (el valor de fábrica),
y `ssh nas 'sudo omv-salt deploy run smartmontools'`.

## Evidencias

- `/etc/default/hd-idle` igual a `state/config/etc/default/hd-idle`
- Atributos 4 y 193 de Seagate y WD a las 0 y 24 h en el OPS (y a los 7 días si se aplica APM)
- Salida de `smartctl -n standby -i` (standby) y de `/var/log/hd-idle.log` en el OPS
- Salida de `smartctl -g apm` antes y después del paso 10 y del paso 11, si se aplica

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-14 | Runbook Agent | Escenario C (cambio menor): cita HLD v2 (2.1); prerrequisito RBK 08 ejecutado (el sync inicial puede seguir en curso), sin sesión web; paso 1 pasa a Lectura del Agente (`conf.system.hdparm` = `[]`, comprobado 2026-10-14); by-id reales de WD y Toshiba (el QVO no se para); paso 5 en una línea con `printf` y `grep -c` de duplicados; paso 7 espera a que termine `snapraid-sync-inicial`; paso 9 por el Agente con `omv-rpc DiskMgmt setHdParm`, umbral > 100/día |
| 2.1 | 2026-10-14 | Runbook Agent | Aprobado (visto bueno del usuario 2026-10-14) |
| 3.0 | 2026-10-28 | Runbook Agent | Escenario A contra HLD v3 (3.0, Aprobado; ADR-025): Toshiba retirado; hd-idle para Seagate (paridad, WDZ03YJJ) y WD (d1); QVO (d2) sin parar. El RBK 2.1 no se llegó a ejecutar (inventario 2026-10-28: hd-idle sin instalar). Comprobado en el NAS: `hdparm` no está instalado y OMV 8 aplica APM/standby con `smartctl --set` (`20hdparm.sls`, servicio `smartctl-hdparm`), así que el estado se lee con `smartctl -n standby` y no se instala `hdparm`. Nuevos pasos 3 (nada más despierta los discos: smartd `-n standby`, tarea 23:30, vigilante del content), 6 (opciones de hd-idle 1.21) y 11 (APM tras despertar). Fichero de hd-idle en `state/config/` enviado con `cat \| ssh nas sudo tee`; APM 254 por disco con JSON en `state/config/omv/` y recuentos contra duplicados. 193 de partida: Seagate 116 618 (norm. 042), WD 82 146, APM 128 en ambos |
| 3.0 | 2026-10-28 | Runbook Agent | Estado cambiado a Aprobado ("go" del usuario 2026-10-28) |
