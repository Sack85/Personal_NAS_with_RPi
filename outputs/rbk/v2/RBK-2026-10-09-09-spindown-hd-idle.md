# RBK 09 — Spindown con hd-idle

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 09 — Spindown con hd-idle |
| **Versión** | 2.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-14 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h + 45 min de espera + 24 h de seguimiento |

## Objetivo

Parar los dos mecánicos (WD Blue y Toshiba MK1059) tras 45 minutos sin uso con hd-idle, con
`-i 0` por defecto para no parar el XG5 ni el QVO, sin el spindown de OMV, y medir el atributo
193 del Toshiba para decidir APM 254 (HLD §9, ADR-006).

## Prerrequisitos

- [ ] RBK 08 ejecutado (el sync inicial de SnapRAID, unidad `snapraid-sync-inicial`, puede estar en curso: no impide instalar hd-idle)
- [ ] Sin sesión web: todos los pasos los hace el Agente por SSH

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
ssh nas 'sudo omv-confdbadm read conf.system.hdparm'
```

Esperado: `[]` (OMV sin spindown ni APM por disco; comprobado el 2026-10-14). Así hd-idle es el único que para los discos.

Si falla: si sale algún objeto con `spindowntime` distinto de 0, para: ponerlo a 0 requiere un cambio aprobado (con `DiskMgmt setHdParm`, como en el paso 9) antes de seguir.

### Paso 2: Localizar los nombres estables

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'ls -l /dev/disk/by-id/ | grep -v part'
```

Esperado: entre otras, `ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5`, `ata-TOSHIBA_MK1059GSM_Y1NDFAQES` y `ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F` (el QVO no se para), con las series del RBK 05. Si una serie no coincide, para.

Si falla: si no aparecen, comprueba los discos con `lsblk` (RBK 05 paso 1).

### Paso 3: Leer el atributo 193 del Toshiba (base)

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "sudo smartctl -A /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES | grep -E '^193 '"
```

Esperado: valor de `193 Load_Cycle_Count` del Toshiba anotado en el OPS con fecha y hora.

Si falla: si no aparece el 193, anótalo y salta los pasos 8 y 9.

### Paso 4: Instalar hd-idle

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'sudo apt install -y hd-idle'
```

Esperado: paquete `hd-idle` instalado.

Si falla: si no está en el repositorio, para y prepara un UPD.

### Paso 5: Configurar /etc/default/hd-idle

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "printf 'START_HD_IDLE=true\nHD_IDLE_OPTS=\"-i 0 -a /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 -i 2700 -a /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES -i 2700 -l /var/log/hd-idle.log\"\n' | sudo tee /etc/default/hd-idle"
```

Una sola línea; no pegues varias líneas tras `ssh nas`. Comprobación de duplicados:

```bash
ssh nas "grep -c '^HD_IDLE_OPTS=' /etc/default/hd-idle"
```

Esperado: el fichero con `START_HD_IDLE=true` y la línea `HD_IDLE_OPTS` con los dos by-id; el `grep -c` devuelve `1`.

Si falla: si se equivoca un nombre, hd-idle no para ese disco: corrígelo y repite el paso 6.

### Paso 6: Activar el servicio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'sudo systemctl enable --now hd-idle && systemctl is-active hd-idle'
```

Esperado: `hd-idle` `enabled` y `active`.

Si falla: si no arranca, `ssh nas 'sudo journalctl -u hd-idle -n 30'`.

### Paso 7: Comprobar el estado de los discos tras el sync inicial y 45 minutos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'systemctl is-active snapraid-sync-inicial'
ssh nas 'sudo hdparm -C /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES; sudo tail -n 20 /var/log/hd-idle.log'
```

Esperado: primero, `snapraid-sync-inicial` ya no está `active` (mientras dure el sync inicial los discos no se paran: espera sin medir). Después, tras 45 minutos sin uso, WD y Toshiba en `standby`; QVO en `active/idle`. `hdparm -C` no despierta discos.

Si falla: si un mecánico sigue `active/idle`, revisa en `/var/log/hd-idle.log` y con `sudo lsof +D /srv/mergerfs/pool` qué lo usa.

### Paso 8: Leer el atributo 193 a las 24 h

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "sudo smartctl -n standby -A /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES | grep -E '^193 '"
```

Esperado: nuevo valor anotado; diferencia con el paso 3 en el OPS.

Si falla: si el disco está parado, espera a que despierte (23:30, sync) o léelo al día siguiente: no lo despiertes solo para esto.

### Paso 9: APM 254 en el Toshiba si 193 sube más de 100 al día

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, §12 |

Solo si la diferencia del paso 8 es > 100 al día. Si es ≤ 100, no se cambia y se anota «APM sin cambio».

Comando (una orden por línea; no pegues varias tras `ssh nas`):

```bash
ssh nas "sudo omv-rpc -u admin 'DiskMgmt' 'setHdParm' '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"devicefile\":\"/dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES\",\"apm\":254,\"aam\":0,\"spindowntime\":0,\"writecache\":true}'"
ssh nas 'sudo omv-salt deploy run smartmontools'
ssh nas "sudo omv-confdbadm read conf.system.hdparm | grep -o devicefile | wc -l"
ssh nas "sudo hdparm -B /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES"
```

Fuente: `rpc.diskmgmt.sethdparm` en `/usr/share/openmediavault/datamodels/rpc.diskmgmt.json` (uuid nuevo = `OMV_CONFIGOBJECT_NEW_UUID` de `/etc/default/openmediavault`); OMV escribe `/etc/hdparm.conf` desde `deploy/smartmontools/20hdparm.sls`. `spindowntime` 0 deja el spindown a hd-idle. Alternativa si `omv-rpc` falla: `hdparm -B 254` persistente en `/etc/hdparm.conf`, solo con un cambio aprobado aparte.

Esperado: un solo objeto en `conf.system.hdparm` (`1`) y `hdparm -B` → `APM_level = 254`.

Si falla: si tras 7 días con APM 254 el 193 sigue subiendo > 100 al día, pásalo al experto en discos (`/storage-plugin:diagnose-disk`).

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Servicio | `ssh nas systemctl is-active hd-idle` | active |
| Mecánicos parados | `ssh nas 'sudo hdparm -C /dev/disk/by-id/ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5 /dev/disk/by-id/ata-TOSHIBA_MK1059GSM_Y1NDFAQES'` | standby (tras 45 min sin uso) |
| QVO y XG5 no paran | `ssh nas "grep -c 'i 0' /etc/default/hd-idle"` | 1 |
| Sin duplicados | `ssh nas "grep -c '^HD_IDLE_OPTS=' /etc/default/hd-idle"` | 1 |

## Vuelta atrás

`ssh nas 'sudo systemctl disable --now hd-idle'` y, si se desea, volver a activar el spindown
de OMV. APM (si se aplicó el paso 9): repetir `DiskMgmt setHdParm` con el `uuid` del objeto creado (`omv-confdbadm read conf.system.hdparm`) y `apm` 255, y `omv-salt deploy run smartmontools`.

## Evidencias

- Copia de `/etc/default/hd-idle` en `state/config/`
- Atributo 193 a las 0 y 24 h en el OPS
- Salida de `hdparm -C` en el OPS; salida de `hdparm -B` si se aplica el paso 9

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-14 | Runbook Agent | Escenario C (cambio menor): cita HLD v2 (2.1); prerrequisito RBK 08 ejecutado (el sync inicial puede seguir en curso), sin sesión web; paso 1 pasa a Lectura del Agente (`conf.system.hdparm` = `[]`, comprobado 2026-10-14); by-id reales de WD y Toshiba (el QVO no se para); paso 5 en una línea con `printf` y `grep -c` de duplicados; paso 7 espera a que termine `snapraid-sync-inicial`; paso 9 por el Agente con `omv-rpc DiskMgmt setHdParm`, umbral > 100/día |
| 2.1 | 2026-10-14 | Runbook Agent | Aprobado (visto bueno del usuario 2026-10-14) |
