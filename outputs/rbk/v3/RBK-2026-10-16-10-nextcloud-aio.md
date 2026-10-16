# RBK 10 — Nextcloud AIO

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 10 — Nextcloud AIO |
| **Versión** | 3.0 |
| **Estado** | En revisión |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-16 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 3,5 h |

## Objetivo

Instalar Nextcloud AIO en modo reverse proxy detrás de Caddy (HLD §4, §6, ADR-024): Nextcloud en
`https://nas.<tailnet>.ts.net` con el certificado de `tailscale cert` (renovado cada sábado a las
12:00, dentro de la franja con Tailscale activo), Caddy en :443 solo en 192.168.1.11 y en la IP de
Tailscale, Apache de AIO en `127.0.0.1:11000`, panel de AIO en `192.168.1.11:8080` (solo LAN).
Datos internos en `/srv/ncdata` del SSD, `NEXTCLOUD_MOUNT=/srv/mergerfs/pool`, subida de 16G,
solo Imaginary (ADR-007). Cuentas `carlos` y `sabrina`, Documentos e Imágenes como almacenamiento
externo Local con permisos cruzados (ADR-009), papelera y versiones a 30 días (ADR-008). En casa
cada PC resuelve el nombre a 192.168.1.11 por su fichero hosts (ADR-026). El **backup de AIO no se
configura** en esta fase: se activa cuando haya paridad válida (ADR-027).

> Pega **una sola línea** cada vez: cada orden es un `ssh nas "…"` o `ssh -t nas "…"` completo;
> no abras `ssh nas` para pegar después varias líneas. Los ficheros se envían desde la raíz del
> repo en el PC con `cat state/config/<ruta> | ssh nas "sudo tee <ruta> >/dev/null"`.

## Prerrequisitos

- [ ] RBK 07 y 08 completados (pool `/srv/mergerfs/pool` y carpetas)
- [ ] RBK 14 (2.2) ejecutado: Tailscale con `--hostname=nas` y temporizadores de horario
- [ ] Ejecutar los pasos 3 a 9 **dentro de la franja con Tailscale activo** (L-V 11:30-14:30 o 18:00-23:00; S-D 08:00-23:00)
- [ ] El pool sin paridad (DCP-2026-10-15 en curso) no impide instalar: solo se omite el backup de AIO (ADR-027)
- [ ] Gestor de contraseñas listo para la frase de acceso de AIO, la contraseña del admin de Nextcloud y las de `carlos` y `sabrina`

## Pasos

### Paso 1: Comprobar pool, carpetas y puertos libres

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, §6 |

Comando:

```bash
ssh nas "findmnt -n /srv/mergerfs/pool && ls -ld /srv/mergerfs/pool/Documentos/persona1 /srv/mergerfs/pool/Documentos/persona2 /srv/mergerfs/pool/Imagenes && df -h / && sudo ss -ltnp | grep -E ':(443|8080|11000) ' || echo 'puertos libres'"
```

Esperado: pool montado, las tres carpetas presentes (propietario `www-data`, RBK 07), más de 50 GB
libres en `/` y `puertos libres` (nada escucha en 443, 8080 ni 11000; la web de OMV está en 8000).

Si falla: si falta una carpeta, vuelve al RBK 07; si un puerto está ocupado, para e identifica el proceso de la salida de `ss`.

### Paso 2: Comprobar Docker y el plugin compose

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas "dpkg -l openmediavault-compose docker-ce docker-compose-plugin 2>&1 | grep -E '^(ii|un|dpkg)'; sudo docker info --format '{{.ServerVersion}} {{.DockerRootDir}}' 2>&1; apt-cache policy docker-ce | head -4"
```

Esperado: `openmediavault-compose` y `docker-ce` en estado `ii` y `docker info` devuelve versión y
`/var/lib/docker` (en el SSD). En ese caso, salta al paso 4.

Si falla: si `docker-ce` no está instalado pero `apt-cache policy` muestra un candidato del
repositorio de Docker (lo añade omv-extras), sigue con el paso 3. Si no hay candidato, activa el
repositorio Docker en Sistema → omv-extras (Usuario, web de OMV) y repite este paso.

### Paso 3: Instalar Docker con el plugin compose (solo si falta)

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh -t nas "sudo apt-get update && sudo apt-get install -y openmediavault-compose docker-ce docker-compose-plugin"
ssh nas "systemctl is-active docker && sudo docker info --format '{{.ServerVersion}} {{.DockerRootDir}}'"
```

Fuente: el plugin `openmediavault-compose` (omv-extras) usa `docker-ce` del repositorio de Docker;
comprobar antes con `apt-cache depends openmediavault-compose` si el paso 2 dio dudas.

Esperado: `active` y la versión del servidor Docker con `/var/lib/docker`.

Si falla: `ssh nas "sudo journalctl -u docker -n 30 --no-pager"`; no sigas sin Docker activo.

### Paso 4: Activar MagicDNS y HTTPS en la consola de Tailscale

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Navegador (login.tailscale.com) |
| **HLD** | §4, ADR-024 |

Esperado: en la consola de administración → DNS: **MagicDNS** activado y **HTTPS Certificates**
activado (Enable HTTPS). Anota en el OPS el nombre de la tailnet que muestra la página (termina en `.ts.net`).

Si falla: si no aparece la opción HTTPS, activa antes MagicDNS y recarga la página.

### Paso 5: Leer el nombre MagicDNS y la IP de Tailscale

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-024 |

Comando:

```bash
ssh nas "sudo apt-get install -y jq >/dev/null; tailscale status --json | jq -r '.Self.DNSName, .Self.Online, .CurrentTailnet.MagicDNSEnabled' && tailscale ip -4"
```

Esperado: `nas.<tailnet>.ts.net.` (con punto final), `true`, `true` y una IP `100.x.y.z`. El agente
anota en el OPS el nombre (sin el punto final) y la IP; desde aquí `<nombre>` y `<IP-TS>` son esos valores.

Si falla: si el nombre no empieza por `nas.` revisa el `--hostname=nas` del RBK 14; si `MagicDNSEnabled` es `false`, vuelve al paso 4.

### Paso 6: Instalar Caddy y permitir escuchar en la IP de Tailscale aunque esté cortado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-024 |

Fichero `state/config/etc/sysctl.d/90-caddy-nonlocal.conf` (ya en el repo):

```ini
net.ipv4.ip_nonlocal_bind = 1
```

Sin él, Caddy no arrancaría fuera de horario ni tras un reinicio con Tailscale cortado, porque la
IP de Tailscale no existe con `tailscale down`.

Comando (una línea cada vez):

```bash
cat state/config/etc/sysctl.d/90-caddy-nonlocal.conf | ssh nas "sudo tee /etc/sysctl.d/90-caddy-nonlocal.conf >/dev/null"
ssh nas "sudo sysctl --system >/dev/null && sysctl -n net.ipv4.ip_nonlocal_bind && grep -c nonlocal_bind /etc/sysctl.d/90-caddy-nonlocal.conf"
ssh -t nas "sudo apt-get install -y caddy && sudo install -d -m 750 -o root -g caddy /etc/caddy/certs"
ssh nas "caddy version && ls -ld /etc/caddy/certs"
```

Fuente: paquete `caddy` de Debian Trixie (servicio `caddy.service`, usuario `caddy`, `/etc/caddy/Caddyfile`).

Esperado: `1` y `1` (sin duplicados); versión de Caddy 2.x; `/etc/caddy/certs` con `drwxr-x--- root caddy`.

Si falla: si el paquete arranca con el Caddyfile de ejemplo en :80, no pasa nada: el paso 8 lo sustituye.

### Paso 7: Script y temporizador de renovación del certificado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, ADR-024, ADR-010 |

Ficheros ya en el repo: `state/config/usr/local/sbin/tailscale-cert-renovar` (lee el nombre con
`tailscale status --json`, ejecuta `tailscale cert --cert-file /etc/caddy/certs/nas.crt --key-file
/etc/caddy/certs/nas.key <nombre>`, da el grupo `caddy` con permisos 640 y recarga Caddy),
`state/config/etc/systemd/system/tailscale-cert.service` y `tailscale-cert.timer`
(`OnCalendar=Sat *-*-* 12:00:00`, `Persistent=false` para que no se dispare fuera de la franja).

Comando (una línea cada vez):

```bash
cat state/config/usr/local/sbin/tailscale-cert-renovar | ssh nas "sudo tee /usr/local/sbin/tailscale-cert-renovar >/dev/null"
cat state/config/etc/systemd/system/tailscale-cert.service | ssh nas "sudo tee /etc/systemd/system/tailscale-cert.service >/dev/null"
cat state/config/etc/systemd/system/tailscale-cert.timer | ssh nas "sudo tee /etc/systemd/system/tailscale-cert.timer >/dev/null"
ssh nas "sudo chmod 755 /usr/local/sbin/tailscale-cert-renovar && sudo bash -n /usr/local/sbin/tailscale-cert-renovar && grep -c '^tailscale cert' /usr/local/sbin/tailscale-cert-renovar && grep -c '^OnCalendar=' /etc/systemd/system/tailscale-cert.timer && sudo systemd-analyze verify /etc/systemd/system/tailscale-cert.service /etc/systemd/system/tailscale-cert.timer"
```

Esperado: `bash -n` sin salida, `1` y `1` (sin duplicados), `systemd-analyze verify` sin errores.

Si falla: vuelve a enviar el fichero con su línea `cat … | ssh nas "sudo tee …"` (sobrescribe).

### Paso 8: Obtener el certificado y configurar Caddy

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | PC y NAS por SSH |
| **HLD** | §4, ADR-024 |

El agente genera en el PC `state/config/etc/caddy/Caddyfile` con los valores del paso 5 ya
puestos (aquí `<nombre>` y `<IP-TS>` se sustituyen al escribirlo; el fichero no lleva marcadores):

```caddyfile
{
	auto_https off
}

https://<nombre>:443 {
	bind 192.168.1.11 <IP-TS>
	tls /etc/caddy/certs/nas.crt /etc/caddy/certs/nas.key
	reverse_proxy 127.0.0.1:11000
}
```

Comando (una línea cada vez; Tailscale activo):

```bash
ssh nas "sudo /usr/local/sbin/tailscale-cert-renovar; sudo ls -l /etc/caddy/certs; sudo openssl x509 -in /etc/caddy/certs/nas.crt -noout -subject -enddate"
cat state/config/etc/caddy/Caddyfile | ssh nas "sudo tee /etc/caddy/Caddyfile >/dev/null"
ssh nas "grep -c '^https://' /etc/caddy/Caddyfile && grep -c 'reverse_proxy' /etc/caddy/Caddyfile && sudo caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile"
ssh nas "sudo systemctl restart caddy && sudo systemctl enable --now tailscale-cert.timer && systemctl is-active caddy && systemctl list-timers tailscale-cert.timer --no-pager"
```

El primer `tailscale-cert-renovar` puede dar un error al recargar Caddy si aún no tiene este
Caddyfile; el certificado queda igualmente escrito.

Esperado: `nas.crt` y `nas.key` con grupo `caddy` y `-rw-r-----`; `subject=CN = <nombre>` y fecha de
caducidad a unos 90 días; `1` y `1`; `Valid configuration`; Caddy `active`; próximo disparo del
temporizador el sábado a las 12:00.

Si falla: si `tailscale cert` dice que HTTPS no está activado, vuelve al paso 4; si `caddy validate`
falla, corrige el fichero en `state/config/` y reenvíalo.

### Paso 9: Arrancar el contenedor maestro de AIO

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, ADR-007, ADR-024 |

`NEXTCLOUD_DATADIR` no se puede cambiar después de la instalación: comprueba la ruta antes de la
segunda línea. Comando (una línea cada vez):

```bash
ssh nas "sudo install -d -m 750 /srv/ncdata && ls -ld /srv/ncdata && findmnt -n -T /srv/ncdata -o SOURCE,TARGET"
ssh nas "sudo docker run --detach --init --sig-proxy=false --name nextcloud-aio-mastercontainer --restart always --publish 192.168.1.11:8080:8080 --env APACHE_PORT=11000 --env APACHE_IP_BINDING=127.0.0.1 --env APACHE_ADDITIONAL_NETWORK= --env SKIP_DOMAIN_VALIDATION=true --env NEXTCLOUD_DATADIR=/srv/ncdata --env NEXTCLOUD_MOUNT=/srv/mergerfs/pool --env NEXTCLOUD_UPLOAD_LIMIT=16G --volume nextcloud_aio_mastercontainer:/mnt/docker-aio-config --volume /var/run/docker.sock:/var/run/docker.sock:ro ghcr.io/nextcloud-releases/all-in-one:latest"
ssh nas "sudo docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' && sudo ss -ltnp | grep -E ':(8080|11000) '"
```

Fuente: README de nextcloud/all-in-one y `reverse-proxy.md` (variables `APACHE_PORT`,
`APACHE_IP_BINDING`, `SKIP_DOMAIN_VALIDATION`, `NEXTCLOUD_DATADIR`, `NEXTCLOUD_MOUNT`,
`NEXTCLOUD_UPLOAD_LIMIT`). Se usa `docker run` (no un fichero compose) para el maestro; Docker lo
gestiona el plugin compose.

Esperado: `/srv/ncdata` en el sistema de archivos raíz (SSD, `/`); `nextcloud-aio-mastercontainer`
`Up` con `192.168.1.11:8080->8080/tcp`; `ss` muestra 8080 solo en `192.168.1.11` (nunca en `0.0.0.0`
ni en la IP de Tailscale).

Si falla: si se reinicia en bucle, `ssh nas "sudo docker logs --tail 50 nextcloud-aio-mastercontainer"`.
Si la ruta de datos estaba mal: `ssh nas "sudo docker rm -f nextcloud-aio-mastercontainer && sudo docker volume rm nextcloud_aio_mastercontainer"` y repite.

### Paso 10: Panel de AIO: frase de acceso, dominio y contenedores

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Panel de AIO (`https://192.168.1.11:8080`) |
| **HLD** | §6, §8, ADR-024, ADR-027 |

Esperado: panel abierto por IP aceptando el certificado autofirmado; frase de acceso guardada en el
gestor de contraseñas; dominio `<nombre>` aceptado (sin validación, `SKIP_DOMAIN_VALIDATION`);
contenedores opcionales: solo **Imaginary** (Office, Talk, ClamAV, búsqueda de texto completo
apagados); zona horaria `Indian/Reunion`; contenedores iniciados; contraseña inicial del admin de
Nextcloud guardada en el gestor de contraseñas. **No configurar el backup** (ADR-027).

Si falla: si un contenedor no arranca, mira su registro en el panel y reinicia los contenedores.

### Paso 11: Comprobar contenedores, puerto 11000 y el montaje del pool

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §4, §6 |

Comando:

```bash
ssh nas "sudo docker ps --format '{{.Names}} {{.Status}}' | grep nextcloud-aio && sudo ss -ltnp | grep ':11000 ' && sudo docker exec nextcloud-aio-nextcloud ls /srv/mergerfs/pool"
```

Esperado: maestro, apache, nextcloud, database, redis e imaginary `Up`; 11000 solo en `127.0.0.1`;
el pool visible dentro del contenedor en `/srv/mergerfs/pool` (Documentos, Imagenes, Archivo).

Si falla: si el pool no se ve en esa ruta, busca la ruta real con `ssh nas "sudo docker inspect nextcloud-aio-nextcloud --format '{{json .Mounts}}'"` y úsala en el paso 15.

### Paso 12: Papelera y versiones a 30 días

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, ADR-008 |

Comando (una línea cada vez):

```bash
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:set trashbin_retention_obligation --value='30, 35'"
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:set versions_retention_obligation --value='30, auto'"
ssh nas "sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:get trashbin_retention_obligation; sudo docker exec --user www-data nextcloud-aio-nextcloud php occ config:system:get versions_retention_obligation"
```

Fuente: documentación de AIO (`docker exec --user www-data nextcloud-aio-nextcloud php occ`).

Esperado: `30, 35` y `30, auto`.

Si falla: si `occ` falla, comprueba que `nextcloud-aio-nextcloud` está `Up` (paso 11).

### Paso 13: Activar la app External storage

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

Esperado: `files_external enabled` (o `already enabled`).

Si falla: si la app no existe, actualiza los contenedores desde el panel de AIO y repite.

### Paso 14: Grupo y cuentas `carlos` y `sabrina`

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de Nextcloud (`https://<nombre>` desde el PC, tras el paso 18) o panel de AIO → «Open Nextcloud» |
| **HLD** | §6, §8 |

Esperado: como admin → Cuentas: grupo `familia`; cuentas `carlos` y `sabrina` en él, con
contraseñas que pone el usuario y guarda en el gestor de contraseñas.

Si falla: si la cuenta ya existe, revisa su grupo.

### Paso 15: Montajes externos por persona

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de Nextcloud |
| **HLD** | §6, ADR-009 |

Esperado: Administración → Almacenamiento externo, tipo **Local**, «Comprobar cambios: una vez por acceso directo»:

| Nombre | Ruta | Aplicable a | Opción |
|---|---|---|---|
| `Documentos persona1` | `/srv/mergerfs/pool/Documentos/persona1` | `carlos` | lectura y escritura |
| `Documentos persona1 (lectura)` | `/srv/mergerfs/pool/Documentos/persona1` | `sabrina` | Solo lectura |
| `Documentos persona2` | `/srv/mergerfs/pool/Documentos/persona2` | `sabrina` | lectura y escritura |
| `Documentos persona2 (lectura)` | `/srv/mergerfs/pool/Documentos/persona2` | `carlos` | Solo lectura |
| `Imagenes` | `/srv/mergerfs/pool/Imagenes` | grupo `familia` | lectura y escritura |

Cinco montajes en verde.

Si falla: si un montaje sale en rojo, comprueba la ruta del paso 11 y que el propietario es `www-data` (RBK 07).

### Paso 16: Comprobar los montajes externos

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

Esperado: cinco montajes con las rutas y aplicables de la tabla; los dos «(lectura)» con `readonly: true`; ningún duplicado.

Si falla: si falta uno o sobra uno, vuelve al paso 15 y borra el duplicado en la web.

### Paso 17: Línea en el fichero hosts de cada PC Windows

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Cada PC Windows (Bloc de notas como administrador) |
| **HLD** | §4, ADR-026 |

Esperado: al final de `C:\Windows\System32\drivers\etc\hosts`, una sola línea con el nombre del paso 5:

```text
192.168.1.11 <nombre>
```

Comprobación en PowerShell: `Resolve-DnsName <nombre> -Type A` devuelve `192.168.1.11` y
`(Select-String -Path C:\Windows\System32\drivers\etc\hosts -Pattern 'ts.net').Count` devuelve `1`.

Si falla: si Windows no deja guardar, abre el Bloc de notas con «Ejecutar como administrador»; si
resuelve a 100.x, Tailscale del PC tiene prioridad: ejecuta `ipconfig /flushdns` y repite.

### Paso 18: Cliente de escritorio en los dos PC

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §6 |

Esperado: cliente de Nextcloud con `https://<nombre>` y la cuenta de cada persona: sincroniza completas
su carpeta de Documentos y todo Imagenes en `D:`; los Documentos del otro no se sincronizan.

Si falla: si no conecta, revisa el paso 17 y que Caddy está `active`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| HTTPS en la LAN | PC en casa: navegador a `https://<nombre>` | Login de Nextcloud, candado sin aviso |
| HTTPS por Tailscale | Móvil con datos y Tailscale, dentro del horario: `https://<nombre>` | Login de Nextcloud, candado sin aviso |
| Certificado | `ssh nas "echo \| openssl s_client -connect 192.168.1.11:443 -servername <nombre> 2>/dev/null \| openssl x509 -noout -subject -issuer -enddate"` | CN = `<nombre>`, emisor Let's Encrypt, caducidad futura |
| Puertos | `ssh nas "sudo ss -ltnp \| grep -E ':(443\|8080\|11000) '"` | 443 en 192.168.1.11 y `<IP-TS>`; 8080 solo en 192.168.1.11; 11000 solo en 127.0.0.1 |
| Fuera de horario | Móvil fuera de casa fuera del horario | No conecta; en el PC de casa sigue funcionando |
| Contenedores | `ssh nas "sudo docker ps --format '{{.Names}}' \| grep -c nextcloud-aio"` | ≥ 6 |
| Papelera y versiones | paso 12, tercera línea | `30, 35` y `30, auto` |
| Montajes | paso 16 | 5 montajes, 2 de solo lectura |
| Renovación | `ssh nas "systemctl list-timers tailscale-cert.timer --no-pager"` | Próximo sábado 12:00 |
| Prueba SMB → Nextcloud | Fichero copiado a `\\nas\Imagenes` | Aparece en la web y en `D:` del otro PC; `sabrina` ve los Documentos de persona1 y no puede editarlos |

## Vuelta atrás

- Antes del paso 10: `ssh nas "sudo docker rm -f nextcloud-aio-mastercontainer && sudo docker volume rm nextcloud_aio_mastercontainer"`.
- Después: parar los contenedores desde el panel, borrar maestro y volumen como arriba y los
  contenedores `nextcloud-aio-*`; `/srv/ncdata` se vacía a mano por el usuario (borrado recursivo
  bloqueado al agente). Documentos e Imágenes del pool no se tocan.
- Caddy: `ssh nas "sudo systemctl disable --now caddy tailscale-cert.timer"`; el sysctl se retira con `ssh nas "sudo rm /etc/sysctl.d/90-caddy-nonlocal.conf && sudo sysctl --system"`.
- Línea de hosts: borrarla en cada PC.

## Evidencias

- `state/config/etc/caddy/Caddyfile`, `tailscale-cert-renovar`, `tailscale-cert.service/.timer` y `90-caddy-nonlocal.conf` versionados
- Orden `docker run` usada y salida de `docker ps` en el OPS
- Salida de `files_external:list` (sin contraseñas) y de `ss -ltnp` en el OPS
- Captura del candado del navegador en LAN y por Tailscale

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| Ninguna (las de v2 quedan cerradas por ADR-024 y ADR-026) | — | — |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado) |
| 3.0 | 2026-10-16 | Runbook Agent | Escenario A por HLD v3 (3.0, Aprobado): deSEC sustituido por `nas.<tailnet>.ts.net` con `tailscale cert` y renovación semanal (ADR-024); Caddy en :443 con `ip_nonlocal_bind`; AIO en modo reverse proxy con `docker run` (11000 en 127.0.0.1, 8080 solo LAN); backup de AIO no configurado hasta tener paridad (ADR-027); fichero hosts en los PC (ADR-026); cuentas `carlos` y `sabrina`; ficheros enviados desde `state/config/` |
