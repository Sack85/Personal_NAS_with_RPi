# RBK 04 — OpenMediaVault 8, plugins y correo

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 04 — OpenMediaVault 8, plugins y correo |
| **Versión** | 2.0 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 2 h |

## Objetivo

Instalar OpenMediaVault 8 con los scripts de omv-extras, cambiar la contraseña de `admin`, mover
la web al puerto 8000, instalar los plugins snapraid, mergerfs, sharerootfs y compose, y dejar
los avisos por correo de Gmail probados (HLD §3, §6, §10).

## Prerrequisitos

- [ ] RBK 03 completado: `ssh nas` funciona y los tres discos aparecen
- [ ] Contraseña de aplicación de Gmail creada y guardada en el gestor de contraseñas
- [ ] Contraseña nueva de `admin` de OMV creada en el gestor de contraseñas

## Pasos

### Paso 1: Ejecutar el script preinstall de omv-extras

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas
wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/preinstall | sudo bash
sudo reboot
```

Fuente: guía §4.1 (scripts oficiales de omv-extras). Lo ejecuta el usuario en su sesión SSH porque la conexión se corta.

Esperado: el script termina sin errores; la Pi se reinicia y vuelve a responder a `ssh nas`.

Si falla: si falla con «unsupported OS», comprueba que no hay repositorios de Ubuntu ni PPA en `/etc/apt/sources.list.d/` y repite.

### Paso 2: Ejecutar el script install de omv-extras

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas
wget -O - https://github.com/OpenMediaVault-Plugin-Developers/installScript/raw/master/install | sudo bash
```

Esperado: el script termina y reinicia solo; la sesión SSH se corta durante la instalación (normal). La IP no cambia gracias a la reserva DHCP.

Si falla: si no vuelve a responder en 30 minutos, conecta una pantalla y revisa la salida; vuelve a lanzar el script (es repetible).

### Paso 3: Comprobar que OMV está en marcha

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas 'systemctl status openmediavault-engined --no-pager | head -n 5; dpkg -l openmediavault | tail -n 1'
```

Esperado: `active (running)` y una versión 8.x de `openmediavault`.

Si falla: si no está activo, revisa `ssh nas 'sudo journalctl -u openmediavault-engined -n 50'` y para.

### Paso 4: Primer acceso y contraseña de admin

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §8 |

Esperado: entras en `http://nas.local` con `admin` y la contraseña de fábrica, y la cambias por la del gestor de contraseñas (icono de usuario → Cambiar contraseña). Barra amarilla de cambios pendientes aplicada.

Si falla: si no carga la web, comprueba el paso 3.

### Paso 5: Mover la web de OMV al puerto 8000

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §4 |

Esperado: Sistema → Área de trabajo → Puerto 8000 guardado y aplicado; la web responde en `http://nas.local:8000` y ya no en el 80.

Si falla: si se pierde el acceso, `ssh nas 'sudo omv-firstaid'` permite volver a configurar el puerto de la web.

### Paso 6: Instalar los plugins

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §3, §5, §6 |

Esperado: en Sistema → Complementos instalados `openmediavault-snapraid`, `openmediavault-mergerfs`, `openmediavault-sharerootfs` y `openmediavault-compose`. `openmediavault-nut` solo en el RBK 12.

Si falla: si un plugin no aparece, Sistema → omv-extras → recargar la lista y repetir.

### Paso 7: Comprobar los plugins instalados

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §3 |

Comando:

```bash
ssh nas "dpkg -l 'openmediavault-*' | grep -E 'snapraid|mergerfs|sharerootfs|compose'"
```

Esperado: cuatro líneas `ii` (snapraid, mergerfs, sharerootfs, compose).

Si falla: si falta alguno, repite el paso 6.

### Paso 8: Configurar el correo de avisos con Gmail

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 (Otros), §8 |

Esperado: Sistema → Notificación → Configuración: smtp.gmail.com, puerto 587, STARTTLS, remitente y usuario = la dirección completa, contraseña = la contraseña de aplicación del gestor de contraseñas, destinatario = el correo de la familia. Guardado y aplicado.

Si falla: si el guardado falla, revisa que la verificación en dos pasos de Google está activa y que la contraseña de aplicación es la de 16 caracteres sin espacios.

### Paso 9: Enviar un correo de prueba y activar avisos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6, §10 |

Esperado: llega el correo de prueba; en Notificaciones activados SMART, sistema de ficheros y actualizaciones.

Si falla: si no llega en 5 minutos, revisa `ssh nas 'sudo journalctl -u postfix -n 30'` (el agente lo lee) y la carpeta de spam.

### Paso 10: Comprobar que no hay actualizaciones automáticas con reinicio

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §10 |

Comando:

```bash
ssh nas "apt-config dump | grep -i 'Automatic-Reboot' || echo sin-reinicio-automatico"
```

Esperado: ninguna línea `Unattended-Upgrade::Automatic-Reboot "true"`. Las actualizaciones se hacen a mano con un UPD aprobado.

Si falla: si aparece a `true`, anótalo como incidencia y prepara el cambio con `/maintainer-plugin:create-upd`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| OMV en marcha | `ssh nas systemctl is-active openmediavault-engined` | active |
| Web en 8000 | `curl -s -o /dev/null -w '%{http_code}' http://nas.local:8000` | 200 |
| Puerto 80 libre | `ssh nas "sudo ss -ltnp \| grep -c ':80 '"` | 0 |
| Correo | `bandeja de entrada` | correo de prueba recibido |

## Vuelta atrás

La instalación de OMV no tiene vuelta atrás sencilla: si falla de forma irrecuperable, volver
a grabar el XG5 (RBK 02) y repetir los RBK 03 y 04. Los plugins se desinstalan desde Sistema →
Complementos. Los discos de datos no se han tocado.

## Evidencias

- Versión de `openmediavault` y de cada plugin en el OPS
- Capturas 4.1 a 4.4 (sin contraseñas) en el OPS

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
