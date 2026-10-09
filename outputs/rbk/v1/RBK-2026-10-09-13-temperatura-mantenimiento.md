# RBK 13 — Temperatura y mantenimiento

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 13 — Temperatura y mantenimiento |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1,5 h |

## Objetivo

Comprobar las temperaturas de la Pi y los discos, confirmar la vigilancia SMART del RBK 05
(aviso 40 °C, crítica 45 °C, sin despertar discos) e instalar el vigilante `nas-temp` que apaga
el NAS tras 15 minutos con un disco ≥ 45 °C o con una lectura ≥ 50 °C; dejar el panel de OMV con
temperaturas y la línea base para el mantenimiento periódico (HLD §9, §10, ADR-014).

## Prerrequisitos

- [ ] RBK 05 (vigilancia SMART) y RBK 09 (hd-idle) completados
- [ ] Correo de avisos probado (RBK 04)

## Pasos

### Paso 1: Temperatura y throttling de la Pi

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'vcgencmd measure_temp; vcgencmd get_throttled'
```

Esperado: Pi < 70 °C y `throttled=0x0`.

Si falla: si hay throttling, revisa la alimentación de 12 V y el Active Cooler antes de seguir.

### Paso 2: Temperatura de los discos sin despertarlos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'for d in /dev/disk/by-id/ata-*; do case "$d" in *-part*) ;; *) echo "$d"; sudo smartctl -n standby -A "$d" | grep -E "^(190|194) ";; esac; done'
```

Esperado: discos entre 25 y 40 °C; los parados no responden (estado standby) y no se despiertan.

Si falla: si un disco supera 40 °C con 35 °C de ambiente o menos, revisa ventilador y filtro (paso 7).

### Paso 3: Confirmar la vigilancia SMART

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, ADR-014 |

Comando:

```bash
ssh nas "grep -v '^#' /etc/smartd.conf | grep -v '^$'"
```

Esperado: en `/etc/smartd.conf`, `-n standby` y `-W` con 40 y 45 en los tres discos SATA (RBK 05 paso 8).

Si falla: si falta, vuelve al RBK 05 paso 6.

### Paso 4: Instalar el vigilante nas-temp

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, ADR-014 |

Comando:

```bash
ssh nas 'sudo tee /usr/local/sbin/nas-temp' <<'EOF'
#!/bin/bash
# nas-temp: vigila la temperatura de los discos SATA y de la Pi (HLD §9, ADR-014).
# Disco >= 45 °C en 3 lecturas seguidas (15 min) o >= 50 °C en una: correo y apagado limpio.
# Pi > 80 °C: correo. No despierta discos parados (smartctl -n standby).
set -u
ESTADO=/run/nas-temp.cuenta
LIMITE=45; CRITICO=50; LECTURAS=3; PI_MAX=80
aviso() { printf 'Subject: [nas] %s\n\n%s\n' "$1" "$2" | /usr/sbin/sendmail root; logger -t nas-temp "$1"; }
max=0; detalle=""
for d in /dev/disk/by-id/ata-*; do
  case "$d" in *-part*) continue ;; esac
  t=$(smartctl -n standby -A "$d" | awk '$1==194 || $1==190 {print $10; exit}')
  [ -n "$t" ] || continue
  detalle="$detalle $(basename "$d")=$t"
  [ "$t" -gt "$max" ] && max=$t
done
cuenta=$(cat "$ESTADO" 2>/dev/null || echo 0)
if [ "$max" -ge "$CRITICO" ]; then
  aviso "Apagado: disco a ${max} °C" "Lecturas:$detalle"; systemctl poweroff
elif [ "$max" -ge "$LIMITE" ]; then
  cuenta=$((cuenta + 1)); echo "$cuenta" > "$ESTADO"
  if [ "$cuenta" -ge "$LECTURAS" ]; then
    aviso "Apagado: discos >= ${LIMITE} °C durante 15 min" "Lecturas:$detalle"; systemctl poweroff
  fi
else
  echo 0 > "$ESTADO"
fi
pi=$(vcgencmd measure_temp | tr -dc '0-9.' | cut -d. -f1)
[ "${pi:-0}" -gt "$PI_MAX" ] && aviso "Pi a ${pi} °C" "Revisa ventilación y Active Cooler"
exit 0
EOF
ssh nas 'sudo chmod 755 /usr/local/sbin/nas-temp && bash -n /usr/local/sbin/nas-temp'
```

Esperado: `/usr/local/sbin/nas-temp` (755, root) y `bash -n` sin errores.

Si falla: si `bash -n` falla, corrige el fichero.

### Paso 5: Servicio y temporizador cada 5 minutos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9, ADR-014 |

Comando:

```bash
ssh nas 'sudo tee /etc/systemd/system/nas-temp.service' <<'EOF'
[Unit]
Description=Vigilante de temperatura de discos y Pi (HLD §9, ADR-014)

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/nas-temp
EOF
ssh nas 'sudo tee /etc/systemd/system/nas-temp.timer' <<'EOF'
[Unit]
Description=nas-temp cada 5 minutos

[Timer]
OnBootSec=5min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF
ssh nas 'sudo systemctl daemon-reload && sudo systemctl enable --now nas-temp.timer && sudo systemctl start nas-temp.service && systemctl status nas-temp.service --no-pager | head -n 5'
```

Esperado: `nas-temp.timer` activo; `nas-temp.service` termina con `status=0/SUCCESS` en la primera ejecución.

Si falla: si el servicio falla, `ssh nas 'sudo journalctl -u nas-temp -n 20'`; para desactivarlo, `sudo systemctl disable --now nas-temp.timer`.

### Paso 6: Probar el envío de correo del vigilante

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "printf 'Subject: [nas] Prueba de nas-temp\n\nPrueba del vigilante de temperatura.\n' | /usr/sbin/sendmail root"
```

Esperado: llega a la bandeja de la familia un correo «[nas] Prueba de nas-temp».

Si falla: si no llega, comprueba que OMV reenvía el correo de root al destinatario (RBK 04 paso 8) y la carpeta de spam.

### Paso 7: Ventilador, filtro e higrómetro

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §9, §12 |

Esperado: ventilador a velocidad fija baja girando; filtro limpio; humedad del higrómetro anotada en el OPS.

Si falla: si el filtro está sucio, límpialo; si la humedad supera el 80 %, avisa al arquitecto (riesgo de condensación).

### Paso 8: Widgets de temperatura en el panel de OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §9 |

Esperado: panel de OMV con los widgets de temperatura de CPU y de estado SMART.

Si falla: si un widget no aparece, actualiza la página tras aplicar.

### Paso 9: Línea base para el mantenimiento

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §10 |

Comando:

```bash
ssh nas 'uptime; df -h / /srv/mergerfs/pool; systemctl list-timers --no-pager'
```

Esperado: inventario `state/inventory/AAAA-MM-DD.yaml` creado con `/maintainer-plugin:inventory`; servirá de referencia para la revisión semanal, mensual, semestral y de verano (HLD §10) con `/maintainer-plugin:create-mnt`.

Si falla: si el inventario falla, repítelo tras revisar `ssh nas`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Pi | `ssh nas vcgencmd get_throttled` | throttled=0x0 |
| Vigilante | `ssh nas systemctl is-active nas-temp.timer` | active |
| Último resultado | `ssh nas 'systemctl show -p Result nas-temp.service'` | Result=success |
| Correo | `bandeja de entrada` | correo de prueba de nas-temp |

## Vuelta atrás

`ssh nas 'sudo systemctl disable --now nas-temp.timer'` desactiva el vigilante; el script y las
unidades se pueden borrar después (lo hace el usuario). smartd sigue avisando a 40 y 45 °C.

## Evidencias

- Temperaturas de la Pi y los discos en el OPS (línea base)
- Copia de `nas-temp` y sus unidades en `state/config/`
- Inventario inicial en `state/inventory/`; captura 13.1

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| El vigilante lee el atributo 194 o 190 de cada disco SATA; confirmar en la primera ejecución que el QVO y el WD informan de uno de los dos | Runbook Agent | Ejecución del RBK 13 |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
