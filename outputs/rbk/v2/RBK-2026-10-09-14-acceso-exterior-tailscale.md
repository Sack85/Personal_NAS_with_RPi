# RBK 14 — Acceso exterior con Tailscale y horario

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 14 — Acceso exterior con Tailscale y horario |
| **Versión** | 2.0 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1,5 h |

## Objetivo

Dar acceso exterior a Nextcloud e Immich solo por Tailscale, sin abrir ningún puerto en el
router, y cortarlo automáticamente fuera del horario de uso (L-V 18:00-23:00, sábado y domingo
08:00-23:00) con los temporizadores `tailscale-on`, `tailscale-off` y el servicio de arranque
`tailscale-horario` (HLD §4, §8, ADR-005, ADR-010, ADR-018). Se ejecuta **antes del RBK 10**:
el dominio de Nextcloud apunta a la IP de Tailscale del NAS.

## Prerrequisitos

- [ ] RBK 04 completado (OMV en marcha); RBK 09 recomendado
- [ ] Cuenta de Tailscale de la familia creada por el usuario (inicio de sesión en el gestor de contraseñas)
- [ ] Acceso de administración al router

## Pasos

### Paso 1: Comprobar que el router no reenvía puertos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | Router |
| **HLD** | §8, ADR-018 |

Esperado: la tabla de reenvío de puertos (port forwarding / NAT virtual server) y UPnP sin ninguna regla hacia el NAS; UPnP desactivado si el router lo permite.

Si falla: si hay una regla hacia el NAS (por ejemplo de la v1 con 443), bórrala y anótalo en el OPS.

### Paso 2: Instalar Tailscale

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, §10 |

Comando:

```bash
ssh nas 'curl -fsSL https://tailscale.com/install.sh | sh && systemctl is-active tailscaled'
```

Fuente: https://tailscale.com/kb/1031/install-linux (script oficial).

Esperado: `tailscale` y `tailscaled` instalados desde el repositorio oficial de Tailscale; `tailscaled` activo.

Si falla: si el script falla, sigue la instalación manual de Debian Trixie de https://tailscale.com/kb/1031/install-linux.

### Paso 3: Unir el NAS a la tailnet

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §4 |

Comando:

```bash
ssh nas
sudo tailscale up
```

Esperado: `tailscale up` muestra una URL; el usuario la abre, inicia sesión y autoriza el equipo `nas`.

Si falla: si la URL caduca, repite `sudo tailscale up`.

### Paso 4: Leer la IP de Tailscale

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4 |

Comando:

```bash
ssh nas 'tailscale ip -4; tailscale status'
```

Esperado: una IP 100.x.y.z y el equipo `nas` conectado. Anota la IP en el OPS (no es pública, pero no se publica fuera del repo).

Si falla: si no hay IP, repite el paso 3.

### Paso 5: Desactivar la caducidad de la clave del NAS

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Consola de Tailscale |
| **HLD** | §4 |

Esperado: en la consola de administración de Tailscale (navegador), equipo `nas` → Disable key expiry.

Si falla: si no se desactiva, el NAS saldrá de la tailnet a los 180 días: anótalo como tarea semestral.

### Paso 6: Crear el script de horario

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-010 |

Comando:

```bash
ssh nas 'sudo tee /usr/local/sbin/tailscale-horario' <<'EOF'
#!/bin/bash
# Aplica el estado de Tailscale que toca según la hora (HLD §4, ADR-010).
# Horario de uso: L-V 18:00-23:00; sábado y domingo 08:00-23:00.
dia=$(date +%u)          # 1 = lunes ... 7 = domingo
hora=$((10#$(date +%H%M)))
if [ "$dia" -le 5 ]; then inicio=1800; else inicio=800; fi
if [ "$hora" -ge "$inicio" ] && [ "$hora" -lt 2300 ]; then
  /usr/bin/tailscale up
else
  /usr/bin/tailscale down
fi
EOF
ssh nas 'sudo chmod 755 /usr/local/sbin/tailscale-horario && bash -n /usr/local/sbin/tailscale-horario'
```

Esperado: `/usr/local/sbin/tailscale-horario` ejecutable por root.

Si falla: si `bash -n` da error, corrige el fichero antes de seguir.

### Paso 7: Crear los servicios y temporizadores

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-010 |

Comando:

```bash
ssh nas 'sudo tee /etc/systemd/system/tailscale-on.service' <<'EOF'
[Unit]
Description=Tailscale up (HLD §4, ADR-010)
After=tailscaled.service
Wants=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale up
EOF
ssh nas 'sudo tee /etc/systemd/system/tailscale-on.timer' <<'EOF'
[Unit]
Description=Tailscale up L-V 18:00, sábado y domingo 08:00

[Timer]
OnCalendar=Mon..Fri 18:00
OnCalendar=Sat,Sun 08:00

[Install]
WantedBy=timers.target
EOF
ssh nas 'sudo tee /etc/systemd/system/tailscale-off.service' <<'EOF'
[Unit]
Description=Tailscale down (HLD §4, ADR-010)
After=tailscaled.service
Wants=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale down
EOF
ssh nas 'sudo tee /etc/systemd/system/tailscale-off.timer' <<'EOF'
[Unit]
Description=Tailscale down todos los días a las 23:00

[Timer]
OnCalendar=*-*-* 23:00

[Install]
WantedBy=timers.target
EOF
ssh nas 'sudo tee /etc/systemd/system/tailscale-horario.service' <<'EOF'
[Unit]
Description=Aplica el horario de Tailscale tras arrancar (HLD §4)
After=tailscaled.service network-online.target
Wants=tailscaled.service network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/tailscale-horario

[Install]
WantedBy=multi-user.target
EOF
ssh nas 'sudo systemd-analyze verify /etc/systemd/system/tailscale-*.service /etc/systemd/system/tailscale-*.timer'
```

Esperado: cinco ficheros en `/etc/systemd/system/`: `tailscale-on.service`, `tailscale-on.timer`, `tailscale-off.service`, `tailscale-off.timer` y `tailscale-horario.service`.

Si falla: si `systemd-analyze verify` da errores, corrígelos antes del paso 8.

### Paso 8: Activar los temporizadores y el servicio de arranque

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-010 |

Comando:

```bash
ssh nas 'sudo systemctl daemon-reload && sudo systemctl enable --now tailscale-on.timer tailscale-off.timer && sudo systemctl enable tailscale-horario.service'
```

Esperado: los dos temporizadores `active (waiting)` y `tailscale-horario.service` `enabled`.

Si falla: si un temporizador no arranca, `ssh nas 'sudo journalctl -u tailscale-on.timer -n 20'`.

### Paso 9: Comprobar las próximas ejecuciones

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4 |

Comando:

```bash
ssh nas "systemctl list-timers 'tailscale-*' --no-pager"
```

Esperado: `tailscale-on.timer` con la próxima a las 18:00 (L-V) o 08:00 (sábado y domingo) y `tailscale-off.timer` a las 23:00.

Si falla: si las horas no cuadran, revisa la zona horaria (`timedatectl`, RBK 03 paso 7).

### Paso 10: Aplicar el horario ahora

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4 |

Comando:

```bash
ssh nas 'sudo systemctl start tailscale-horario.service; tailscale status | head -n 3'
```

Esperado: dentro del horario de uso `tailscale status` muestra el NAS conectado; fuera, `Tailscale is stopped.`

Si falla: si el estado no cuadra con la hora, revisa el script del paso 6.

### Paso 11: Instalar Tailscale en móviles y PC

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Móvil |
| **HLD** | §4, §8 |

Esperado: app de Tailscale en los móviles y PC de la familia, con sesión en la misma tailnet; el NAS aparece en la lista de equipos de cada uno.

Si falla: si un dispositivo no ve el NAS fuera de horario, es lo esperado: pruébalo dentro del horario.

### Paso 12: Comprobar que no se expone nada más

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §8, ADR-018 |

Comando:

```bash
ssh nas 'tailscale serve status; tailscale funnel status'
```

Esperado: `tailscale serve status` y `tailscale funnel status` sin configuración (Funnel desactivado: nada publicado a Internet).

Si falla: si hay un serve o funnel activo, bórralo con `sudo tailscale serve reset` (Cambio) y anótalo.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Temporizadores | `ssh nas "systemctl is-active tailscale-on.timer tailscale-off.timer"` | active, active |
| Arranque | `ssh nas systemctl is-enabled tailscale-horario.service` | enabled |
| Sin Funnel | `ssh nas tailscale funnel status` | sin configuración |
| Router | `tabla de reenvío de puertos` | vacía |

## Vuelta atrás

`ssh nas 'sudo systemctl disable --now tailscale-on.timer tailscale-off.timer && sudo systemctl disable tailscale-horario.service && sudo tailscale up'`
deja Tailscale siempre encendido. Para quitarlo del todo: `sudo tailscale logout` y
`sudo apt remove tailscale`, y borrar el equipo en la consola de Tailscale.

## Evidencias

- Copia de los cinco ficheros de systemd y del script en `state/config/`
- Salida de `systemctl list-timers 'tailscale-*'` en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| El runbook va numerado 14 (fase de la guía) pero se ejecuta tras el RBK 09 y antes del RBK 10. Confirmar el orden de ejecución | Persona 1 | Antes de aprobar los RBK |
| ¿Se restringe con ACL de Tailscale qué puertos del NAS ven los dispositivos de la tailnet (80, 443, 2283) para no dejar SSH ni 8000/8080 en la tailnet? El HLD no lo fija | Arquitecto | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
