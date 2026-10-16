# RBK 14 — Acceso exterior con Tailscale y horario

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 14 — Acceso exterior con Tailscale y horario |
| **Versión** | 2.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-16 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1,5 h |

## Objetivo

Dar acceso exterior a Nextcloud e Immich solo por Tailscale, sin abrir ningún puerto en el
router, y cortarlo automáticamente fuera del horario de uso (hora local Indian/Reunion:
conectado L-V de 11:30 a 14:30 y de 18:00 a 23:00, y sábado y domingo de 08:00 a 23:00) con los temporizadores `tailscale-on`, `tailscale-off` y el servicio de arranque
`tailscale-horario` (HLD §4, §8, ADR-005, ADR-010, ADR-018). Se ejecuta **antes del RBK 10**:
el dominio de Nextcloud apunta a la IP de Tailscale del NAS. `tailscale down` conserva la sesión:
el `tailscale up` siguiente reconecta sin volver a autenticar.

> Pega **una sola línea** cada vez: cada orden es un `ssh nas "…"` o `ssh -t nas "…"` completo;
> no abras `ssh nas` para pegar después varias líneas.

## Prerrequisitos

- [ ] RBK 04 completado (OMV en marcha); RBK 09 recomendado. El pool sin paridad (DCP de
      retirada de d1 en curso) no afecta: Tailscale solo toca el SSD del sistema
- [x] Cuenta de Tailscale de la familia creada por el usuario con Google (2026-10-16; acceso en el gestor de contraseñas)
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
ssh -t nas "sudo tailscale up --hostname=nas"
```

Fuente: https://tailscale.com/kb/1241/tailscale-up (`--hostname`).

Esperado: la orden muestra una URL `https://login.tailscale.com/a/…`; el usuario la abre en el
navegador, inicia sesión con la cuenta de Google de la familia y autoriza el equipo `nas`; la
orden termina sola con `Success.` o sin error.

Si falla: si la URL caduca, repite la misma línea. Si el equipo aparece con otro nombre, renómbralo a `nas` en la consola.

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

El contenido se genera en el PC (copia versionada en `state/config/usr/local/sbin/tailscale-horario`)
y se envía con `cat … | ssh nas "sudo tee …"`, lo que evita los problemas de comillas y de `#!` con `printf`.
Contenido, con los valores ya puestos:

```bash
#!/bin/bash
# Aplica el estado de Tailscale que toca según la hora local (HLD §4, ADR-010).
# Conectado: L-V 11:30-14:30 y 18:00-23:00; sábado y domingo 08:00-23:00.
dia=$(date +%u)
hora=$((10#$(date +%H%M)))
if [ "$dia" -le 5 ]; then
  if { [ "$hora" -ge 1130 ] && [ "$hora" -lt 1430 ]; } || { [ "$hora" -ge 1800 ] && [ "$hora" -lt 2300 ]; }; then dentro=1; else dentro=0; fi
else
  if [ "$hora" -ge 800 ] && [ "$hora" -lt 2300 ]; then dentro=1; else dentro=0; fi
fi
if [ "$dentro" -eq 1 ]; then /usr/bin/tailscale up --hostname=nas; else /usr/bin/tailscale down; fi
```

`--hostname=nas` es obligatorio: sin él `tailscale up` falla porque exige repetir los flags no
por defecto usados en el paso 3 (Fuente: https://tailscale.com/kb/1241/tailscale-up).

Comando (desde la raíz del repo en el PC; una línea para enviar el fichero, otra para comprobarlo):

```bash
cat state/config/usr/local/sbin/tailscale-horario | ssh nas "sudo tee /usr/local/sbin/tailscale-horario >/dev/null"
ssh nas "sudo chmod 755 /usr/local/sbin/tailscale-horario && sudo bash -n /usr/local/sbin/tailscale-horario && sudo grep -c '^if \\[' /usr/local/sbin/tailscale-horario && sudo grep -c 'hostname=nas' /usr/local/sbin/tailscale-horario && sudo cat /usr/local/sbin/tailscale-horario"
```

Esperado: `/usr/local/sbin/tailscale-horario` empieza por `#!/bin/bash`, con permisos 755, `bash -n` sin salida, el
primer `grep -c` devuelve `2` y el segundo `1` (sin líneas duplicadas) y `cat` muestra exactamente las 11 líneas
del bloque de arriba, con `$dia` y `$hora` literales.

Si falla: si un recuento no cuadra o el `cat` difiere del bloque, vuelve a enviar el fichero con la primera línea (`tee` lo sobrescribe).

### Paso 7: Crear los servicios y temporizadores

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-010 |

Los cinco ficheros se generan en el PC (copias versionadas en `state/config/etc/systemd/system/`) y se
envían con `cat … | ssh nas "sudo tee …"`. Contenido, con los valores ya puestos:

`tailscale-on.service`:

```ini
[Unit]
Description=Tailscale up (HLD §4, ADR-010)
After=tailscaled.service
Wants=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale up --hostname=nas
```

`tailscale-on.timer`:

```ini
[Unit]
Description=Tailscale up L-V 11:30 y 18:00, sábado y domingo 08:00

[Timer]
OnCalendar=Mon..Fri 11:30
OnCalendar=Mon..Fri 18:00
OnCalendar=Sat,Sun 08:00

[Install]
WantedBy=timers.target
```

`tailscale-off.service`:

```ini
[Unit]
Description=Tailscale down (HLD §4, ADR-010)
After=tailscaled.service
Wants=tailscaled.service

[Service]
Type=oneshot
ExecStart=/usr/bin/tailscale down
```

`tailscale-off.timer`:

```ini
[Unit]
Description=Tailscale down L-V 14:30 y todos los días 23:00

[Timer]
OnCalendar=Mon..Fri 14:30
OnCalendar=*-*-* 23:00

[Install]
WantedBy=timers.target
```

`tailscale-horario.service`:

```ini
[Unit]
Description=Aplica el horario de Tailscale tras arrancar (HLD §4)
After=tailscaled.service network-online.target
Wants=tailscaled.service network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/tailscale-horario

[Install]
WantedBy=multi-user.target
```

Comando (desde la raíz del repo en el PC; una línea por fichero, pégalas de una en una):

```bash
cat state/config/etc/systemd/system/tailscale-on.service | ssh nas "sudo tee /etc/systemd/system/tailscale-on.service >/dev/null"
cat state/config/etc/systemd/system/tailscale-on.timer | ssh nas "sudo tee /etc/systemd/system/tailscale-on.timer >/dev/null"
cat state/config/etc/systemd/system/tailscale-off.service | ssh nas "sudo tee /etc/systemd/system/tailscale-off.service >/dev/null"
cat state/config/etc/systemd/system/tailscale-off.timer | ssh nas "sudo tee /etc/systemd/system/tailscale-off.timer >/dev/null"
cat state/config/etc/systemd/system/tailscale-horario.service | ssh nas "sudo tee /etc/systemd/system/tailscale-horario.service >/dev/null"
ssh nas "cd /etc/systemd/system && grep -c '^ExecStart=' tailscale-on.service tailscale-off.service tailscale-horario.service && grep -c '^OnCalendar=' tailscale-on.timer tailscale-off.timer && grep -c 'hostname=nas' tailscale-on.service"
ssh nas "sudo systemd-analyze verify /etc/systemd/system/tailscale-on.service /etc/systemd/system/tailscale-on.timer /etc/systemd/system/tailscale-off.service /etc/systemd/system/tailscale-off.timer /etc/systemd/system/tailscale-horario.service"
```

Esperado: cinco ficheros en `/etc/systemd/system/`; `grep -c` devuelve `tailscale-on.service:1`,
`tailscale-off.service:1`, `tailscale-horario.service:1`, `tailscale-on.timer:3` y
`tailscale-off.timer:2`, y `1` para `hostname=nas` (sin duplicados); `systemd-analyze verify` sin errores.

Si falla: si un recuento es mayor, vuelve a enviar ese fichero (`tee` lo sobrescribe); si `systemd-analyze verify` da errores, corrígelos antes del paso 8.

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

Esperado: `tailscale-on.timer` con la próxima a las 11:30 o 18:00 (L-V) o 08:00 (sábado y domingo) y `tailscale-off.timer` a las 14:30 (L-V) o 23:00.

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

`ssh nas 'sudo systemctl disable --now tailscale-on.timer tailscale-off.timer && sudo systemctl disable tailscale-horario.service && sudo tailscale up --hostname=nas'`
deja Tailscale siempre encendido. Para quitarlo del todo: `sudo tailscale logout` y
`sudo apt remove tailscale`, y borrar el equipo en la consola de Tailscale.

## Evidencias

- Copia de los cinco ficheros de systemd y del script en `state/config/`
- Salida de `systemctl list-timers 'tailscale-*'` en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ~~Orden de ejecución~~ Resuelta 2026-10-16: se ejecuta tras el RBK 09 y antes del RBK 10 | Persona 1 | — |
| El NRD §6.1 y el HLD (ADR-010) deben recoger la franja 11:30-14:30 de L-V decidida por el usuario el 2026-10-16 (`/requirements-plugin:update-nrd` y `/architect-plugin:update-hld`) | Persona 1 / Arquitecto | Próxima revisión del NRD y del HLD |
| ¿Se restringe con ACL de Tailscale qué puertos del NAS ven los dispositivos de la tailnet (80, 443, 2283) para no dejar SSH ni 8000/8080 en la tailnet? El HLD no lo fija | Arquitecto | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-16 | Runbook Agent | Escenario C (en sitio, cambio menor): cita HLD v2 (2.1); prerrequisito aclarado (el pool sin paridad no afecta); paso 3 como una sola orden `ssh -t nas "sudo tailscale up --hostname=nas"`; pasos 6-7 sin heredoc, una orden `printf … \| sudo tee` por fichero con `grep -c` y `systemd-analyze verify` (aprendizajes de CLAUDE.md); horario en hora local Indian/Reunion |
| 2.1 | 2026-10-16 | Runbook Agent | Aprobado (visto bueno del usuario 2026-10-16) |
| 2.2 | 2026-10-16 | Runbook Agent | Escenario C (en sitio): nueva franja L-V 11:30-14:30 (decisión del usuario 2026-10-16; pendiente de reflejar en NRD §6.1 y ADR-010): `tailscale-on.timer` Mon..Fri 11:30, `tailscale-off.timer` Mon..Fri 14:30, script con las dos franjas; `tailscale up --hostname=nas` en script, servicio y vuelta atrás (sin el flag falla, corrección ya aplicada en el NAS); pasos 6-7 envían el contenido generado en el PC con `cat … \| ssh nas "sudo tee …"` desde `state/config/` |
| 2.2 | 2026-10-16 | Runbook Agent | Aprobado (visto bueno del usuario 2026-10-16) |
