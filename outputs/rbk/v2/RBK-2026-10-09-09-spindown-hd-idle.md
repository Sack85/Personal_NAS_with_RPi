# RBK 09 — Spindown con hd-idle

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 09 — Spindown con hd-idle |
| **Versión** | 2.0 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h + 45 min de espera + 24 h de seguimiento |

## Objetivo

Parar los dos mecánicos (WD Blue y Toshiba MK1059) tras 45 minutos sin uso con hd-idle, con
`-i 0` por defecto para no parar el XG5 ni el QVO, sin el spindown de OMV, y medir el atributo
193 del Toshiba para decidir APM 254 (HLD §9, ADR-006).

## Prerrequisitos

- [ ] RBK 08 completado
- [ ] Sesión iniciada por el usuario en la web de OMV

## Pasos

### Paso 1: Desactivar el spindown de OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §9 |

Esperado: Almacenamiento → Discos → Editar en cada disco SATA: tiempo de spindown desactivado y APM sin tocar. Aplicado.

Si falla: si un disco no deja editar, anótalo y sigue.

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

Esperado: una entrada `ata-WDC_…` y otra `ata-TOSHIBA_MK1059…` sin `-part`, con las series del RBK 05. Anota las dos rutas en el OPS.

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
ssh nas "sudo smartctl -A /dev/disk/by-id/ata-TOSHIBA_MK1059XXXX | grep -E '^193 '"
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
ssh nas 'sudo tee /etc/default/hd-idle' <<'EOF'
START_HD_IDLE=true
HD_IDLE_OPTS="-i 0 -a /dev/disk/by-id/ata-WDC_XXXX -i 2700 -a /dev/disk/by-id/ata-TOSHIBA_MK1059XXXX -i 2700 -l /var/log/hd-idle.log"
EOF
```

Sustituye `ata-WDC_XXXX` y `ata-TOSHIBA_MK1059XXXX` por los nombres del paso 2 antes de ejecutar.

Esperado: el fichero con `START_HD_IDLE=true` y las opciones del HLD con los dos nombres del paso 2.

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

### Paso 7: Comprobar el estado de los discos tras 45 minutos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'sudo hdparm -C /dev/disk/by-id/ata-WDC_XXXX /dev/disk/by-id/ata-TOSHIBA_MK1059XXXX; sudo tail -n 20 /var/log/hd-idle.log'
```

Esperado: tras 45 minutos sin uso, WD y Toshiba en `standby`; QVO en `active/idle`. `hdparm -C` no despierta discos.

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
ssh nas "sudo smartctl -n standby -A /dev/disk/by-id/ata-TOSHIBA_MK1059XXXX | grep -E '^193 '"
```

Esperado: nuevo valor anotado; diferencia con el paso 3 en el OPS.

Si falla: si el disco está parado, espera a que despierte (23:30, sync) o léelo al día siguiente: no lo despiertes solo para esto.

### Paso 9: APM 254 en el Toshiba si 193 sube más de 100 al día

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §9, §12 |

Esperado: solo si la diferencia del paso 8 es > 100: Almacenamiento → Discos → Editar Toshiba → APM 254. Si es ≤ 100, no se cambia y se anota «APM sin cambio».

Si falla: si tras 7 días con APM 254 el 193 sigue subiendo > 100 al día, pásalo al experto en discos (`/storage-plugin:diagnose-disk`).

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Servicio | `ssh nas systemctl is-active hd-idle` | active |
| Mecánicos parados | `ssh nas 'sudo hdparm -C /dev/disk/by-id/ata-WDC_XXXX'` | standby (tras 45 min sin uso) |
| QVO y XG5 no paran | `ssh nas "grep -c 'i 0' /etc/default/hd-idle"` | 1 |

## Vuelta atrás

`ssh nas 'sudo systemctl disable --now hd-idle'` y, si se desea, volver a activar el spindown
de OMV. APM vuelve a su valor anterior en Almacenamiento → Discos → Editar.

## Evidencias

- Copia de `/etc/default/hd-idle` en `state/config/`
- Atributo 193 a las 0 y 24 h en el OPS
- Salida de `hdparm -C` en el OPS; captura 9.1

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
