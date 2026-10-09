# RBK 10 — Nextcloud AIO

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 10 — Nextcloud AIO |
| **Versión** | 2.0 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 3 h |

## Objetivo

Instalar Nextcloud AIO con el plugin compose: datos internos en `ncdata` del SSD,
`NEXTCLOUD_MOUNT=/srv/mergerfs/pool`, subida de 16G, solo Imaginary, dominio de deSEC que apunta a la IP de
Tailscale del NAS, backup diario a las 23:05 en `Archivo/nextcloud-aio-backup` con actualización
automática tras el backup, papelera y versiones a 30 días, y Documentos e Imágenes como
almacenamiento externo Local con permisos por persona (HLD §6, §7, ADR-005, ADR-007, ADR-008, ADR-009).

## Prerrequisitos

- [ ] RBK 07, 08 y 14 completados (pool, usuarios y Tailscale con su IP)
- [ ] Sesión iniciada por el usuario en la web de OMV
- [ ] Gestor de contraseñas listo para guardar la frase de acceso de AIO, la contraseña del admin de Nextcloud y la del backup de AIO

## Pasos

### Paso 1: Comprobar pool y carpetas

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas 'findmnt -n /srv/mergerfs/pool && ls -ld /srv/mergerfs/pool/Documentos/persona1 /srv/mergerfs/pool/Documentos/persona2 /srv/mergerfs/pool/Imagenes /srv/mergerfs/pool/Archivo/nextcloud-aio-backup'
```

Esperado: `/srv/mergerfs/pool` montado y `Documentos/persona1`, `Documentos/persona2`, `Imagenes` y `Archivo/nextcloud-aio-backup` presentes.

Si falla: si falta algo, vuelve al RBK 07.

### Paso 2: Carpetas compose y ncdata en el SSD

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6, ADR-007 |

Esperado: Almacenamiento → Carpetas compartidas → Crear sobre el sistema de archivos raíz (`/`): `compose` y `ncdata` (vacía). Ruta absoluta de `ncdata` anotada en el OPS.

Si falla: si `/` no aparece, revisa `openmediavault-sharerootfs` (RBK 04).

### Paso 3: Configurar el plugin compose y Docker

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 |

Esperado: Servicios → Compose → Configuración: carpeta `compose`; Docker instalado si el plugin lo ofrece. Aplicado.

Si falla: si Docker no se instala, revisa el registro de la instalación en la web y repite.

### Paso 4: Comprobar Docker

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas "sudo docker version --format '{{.Server.Version}}'; systemctl is-active docker"
```

Esperado: versión del servidor Docker y `active`.

Si falla: si Docker no responde, `ssh nas 'sudo journalctl -u docker -n 30'`.

### Paso 5: Crear el compose de Nextcloud AIO

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 |

Comando:

```bash
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
      NEXTCLOUD_DATADIR: /RUTA/ABSOLUTA/DE/ncdata     # la del paso 2
      NEXTCLOUD_MOUNT: /srv/mergerfs/pool
      NEXTCLOUD_UPLOAD_LIMIT: 16G
volumes:
  nextcloud_aio_mastercontainer:
    name: nextcloud_aio_mastercontainer
```

`NEXTCLOUD_DATADIR` no se puede cambiar después de instalar: comprueba la ruta dos veces.

Esperado: Servicios → Compose → Ficheros → Crear `nextcloud-aio` con este contenido (compose oficial de AIO, guía §10.2, con las variables del HLD), guardado y Arriba (Up).

Si falla: si el contenedor no arranca, revisa los registros en el plugin compose.

### Paso 6: Comprobar el contenedor maestro

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas "sudo docker ps --format '{{.Names}} {{.Status}}'"
```

Esperado: `nextcloud-aio-mastercontainer` en estado `Up`.

Si falla: si se reinicia en bucle, `ssh nas 'sudo docker logs --tail 50 nextcloud-aio-mastercontainer'`.

### Paso 7: Abrir el panel de AIO y guardar la frase de acceso

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO |
| **HLD** | §6, §8 |

Esperado: panel abierto en `https://<IP reservada>:8080` (siempre por IP, aceptando el certificado autofirmado); frase de acceso guardada en el gestor de contraseñas, fuera del NAS.

Si falla: si el panel no carga, revisa el paso 6 y que el 8080 no lo usa otro servicio.

### Paso 8: Dominio de deSEC apuntando a la IP de Tailscale

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO |
| **HLD** | §4, ADR-005 |

Esperado: dominio gratuito registrado con «Get a free one from deSEC»; en deSEC el registro A del dominio apunta a la IP de Tailscale del NAS (RBK 14 paso 4); AIO acepta el dominio.

Si falla: si AIO rechaza el dominio porque no es alcanzable desde Internet, para y resuelve la pregunta abierta de este RBK antes de seguir (no se abre ningún puerto).

### Paso 9: Contenedores opcionales, zona horaria e inicio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO |
| **HLD** | §6 |

Esperado: solo **Imaginary** activado (Office, Talk, ClamAV y búsqueda de texto completo apagados); zona horaria la de casa; contenedores iniciados y contraseña inicial del admin de Nextcloud guardada en el gestor de contraseñas.

Si falla: si un contenedor no arranca, mira su registro en el panel y reinicia los contenedores.

### Paso 10: Backup diario de AIO a las 23:05

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO |
| **HLD** | §6, §7, ADR-015 |

Esperado: ruta de backup `/srv/mergerfs/pool/Archivo/nextcloud-aio-backup`, backup diario a las 23:05 hora local (si el panel pide UTC, convertir), actualizaciones automáticas de contenedores tras el backup activadas; contraseña del backup guardada en el gestor de contraseñas. Primer backup manual correcto.

Si falla: si el backup falla por permisos, revisa la carpeta del paso 1 y repite.

### Paso 11: Papelera y versiones a 30 días

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, ADR-008 |

Comando:

```bash
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:set trashbin_retention_obligation --value='30, 35'"
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:set versions_retention_obligation --value='30, auto'"
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:get trashbin_retention_obligation; sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:get versions_retention_obligation"
```

Fuente: documentación de AIO (ejecutar `occ` con `docker exec --user www-data nextcloud-aio-nextcloud php occ`).

Esperado: los dos valores guardados; `config:system:get` devuelve `30, 35` y `30, auto`.

Si falla: si `occ` falla, comprueba que `nextcloud-aio-nextcloud` está en marcha.

### Paso 12: Activar el almacenamiento externo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ app:enable files_external"
```

Esperado: `files_external enabled`.

Si falla: si la app no existe, actualiza los contenedores desde el panel de AIO y repite.

### Paso 13: Usuarios y grupo en Nextcloud

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de Nextcloud |
| **HLD** | §6, §8 |

Esperado: en Nextcloud (navegador, como admin) → Usuarios: grupo `familia` y usuarios `persona1` y `persona2` en él, con contraseñas del gestor.

Si falla: si el usuario ya existe, revisa su grupo.

### Paso 14: Montajes externos por persona

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de Nextcloud |
| **HLD** | §6, ADR-009 |

Esperado: Administración → Almacenamiento externo, tipo Local, «Comprobar cambios: una vez por acceso directo»: `Documentos persona1` → `/srv/mergerfs/pool/Documentos/persona1` para persona1; `Documentos persona1 (lectura)` → misma ruta para persona2 con «Solo lectura»; `Documentos persona2` y `Documentos persona2 (lectura)` a la inversa; `Imagenes` → `/srv/mergerfs/pool/Imagenes` para el grupo `familia`. Cinco montajes en verde.

Si falla: si un montaje sale en rojo, comprueba la ruta y que el propietario es `www-data` (RBK 07 paso 4).

### Paso 15: Comprobar los montajes externos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, ADR-009 |

Comando:

```bash
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ files_external:list --show-password=false"
```

Esperado: cinco montajes con sus rutas y aplicables; los dos «(lectura)» con `readonly: true`.

Si falla: si falta uno o el solo lectura, vuelve al paso 14.

### Paso 16: Cliente de escritorio en los dos PC

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §6 |

Esperado: cliente de Nextcloud con el dominio de deSEC (Tailscale activo en el PC): sincroniza completas la carpeta de Documentos propia y todo Imagenes en `D:`; los Documentos del otro no se sincronizan.

Si falla: si el cliente no conecta, comprueba Tailscale en el PC (dentro del horario de uso) y el dominio.

### Paso 17: Prueba SMB → Nextcloud

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §6 |

Esperado: un fichero copiado por SMB a `\\nas\Imagenes` aparece en la web de Nextcloud y en `D:` del otro PC; persona2 ve los Documentos de persona1 y no puede editarlos.

Si falla: si no aparece en Nextcloud, revisa la opción de comprobar cambios del montaje (paso 14).

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Contenedores | `ssh nas "sudo docker ps --format '{{.Names}}' \| grep -c nextcloud-aio"` | ≥ 6 (maestro, apache, nextcloud, database, redis, imaginary y los de AIO) |
| Papelera | `ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:get trashbin_retention_obligation"` | 30, 35 |
| Montajes | `ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ files_external:list"` | 5 montajes |
| Backup | `ssh nas 'ls -la /srv/mergerfs/pool/Archivo/nextcloud-aio-backup'` | repositorio borg con fecha de hoy |

## Vuelta atrás

Antes del paso 9: borrar el fichero compose en OMV (Abajo y Eliminar) y el volumen
`nextcloud_aio_mastercontainer`. Después: restaurar desde el backup de AIO con la frase de acceso o
reinstalar desde el paso 5 con `ncdata` vacía. Los ficheros de Documentos e Imágenes del pool no
los toca la desinstalación.

## Evidencias

- Copia del compose de AIO en `state/config/` (`/operator-plugin:snapshot-config`)
- Salida de `files_external:list` (sin contraseñas) en el OPS
- Capturas 10.1 a 10.4 en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Cómo obtiene AIO el certificado de un dominio de deSEC que apunta a una IP de Tailscale (no alcanzable desde Internet)? Verificar en la documentación de AIO (reto DNS de deSEC o `SKIP_DOMAIN_VALIDATION`) antes de ejecutar el paso 8 | Runbook Agent | Antes de aprobar este RBK |
| Pregunta abierta del HLD: si el router permite DNS local, el dominio funcionaría en casa sin Tailscale activo; hoy el PC necesita Tailscale encendido para el cliente de Nextcloud | Persona 1 | 2026-10-31 |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
