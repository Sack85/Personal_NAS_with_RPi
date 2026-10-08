---
name: snapshot-config
description: >
  Copia en solo lectura los ficheros de configuración del NAS que hay que poder reconstruir
  (config.txt, hd-idle, SnapRAID, compose de Nextcloud AIO, fstab, NUT sin contraseñas) a
  state/config/ para versionarlos en git. Usa una lista blanca: nunca copia config.xml de OMV,
  upsd.users ni nada con contraseñas.
  También llamado: copia de la configuración, foto de la configuración, backup de configs.
  Entrada: NAS accesible por SSH. Salida: state/config/ actualizado.
  Úsala cuando el usuario pida:
  - Guardar o versionar la configuración del NAS
  - Copiar los ficheros de configuración al repo
  - Ver qué ha cambiado en la configuración desde la última vez
  - Después de ejecutar un runbook, un UPD o un DCP que cambia configuración
argument-hint: ""
allowed-tools: Read, Write, Bash, Glob
---

# Foto de la configuración del NAS

Copias al repo, en solo lectura, la configuración necesaria para reconstruir el NAS o para ver
qué cambió tras una actualización.

## Paso 1: Comprobar acceso

```bash
ssh -o ConnectTimeout=5 nas true || echo "NAS no accesible"
```

Si no responde, para.

## Paso 2: Lista blanca

| Fichero en el NAS | Destino en el repo |
|---|---|
| `/boot/firmware/config.txt` | `state/config/boot/firmware/config.txt` |
| `/etc/default/hd-idle` | `state/config/etc/default/hd-idle` |
| `/etc/snapraid/omv-snapraid-*.conf` | `state/config/etc/snapraid/` |
| `/etc/fstab` | `state/config/etc/fstab` |
| `/etc/nut/ups.conf`, `/etc/nut/nut.conf` | `state/config/etc/nut/` |
| Compose de Nextcloud AIO (`<carpeta compose>/nextcloud-aio/*.yml`) | `state/config/compose/nextcloud-aio/` |

**Nunca**: `/etc/openmediavault/config.xml`, `/etc/nut/upsd.users`, `/etc/nut/upsmon.conf`
(contiene la contraseña del monitor), `/etc/shadow`, claves SSH, nada de `/root`. Si el usuario
pide otro fichero, revisa antes que no tenga secretos.

## Paso 3: Copiar

Para cada fichero de la lista:

```bash
ssh nas 'sudo cat /etc/default/hd-idle'
```

Escribe la salida con Write en su destino. El guard de secretos revisa cada fichero: si bloquea,
recorta la línea sensible y sustitúyela por `# <secreto omitido: en el gestor de contraseñas>`.

Para el compose, localiza la carpeta en solo lectura:

```bash
ssh nas 'ls -d /srv/*/compose/nextcloud-aio 2>/dev/null; ls /srv/*/compose 2>/dev/null'
```

## Paso 4: Índice y diferencias

1. Escribe `state/config/README.md` con fecha, versión de OMV (`ssh nas 'dpkg-query -W openmediavault'`)
   y la lista de ficheros copiados.
2. Enseña al usuario `git diff --stat state/config/` y, si hay cambios, `git diff state/config/`
   resumido: qué cambió desde la última foto.

## Paso 5: Traza

Propón el commit (`git add state/config/ && git commit -m "Foto de configuración AAAA-MM-DD"`)
con `AskUserQuestion`. Nunca hagas push.

## Aprendizajes y correcciones

> **Meta-reglas para añadir aprendizajes:**
> 1. Cada aprendizaje es una directiva absoluta ("Siempre X", "Nunca Y").
> 2. Primero el problema y luego la solución.
> 3. Con un comando o ejemplo concreto.
> 4. Una regla por viñeta.
> 5. Si dos se contradicen, borra la antigua.
> 6. Máximo 20 por skill.

### Aprendizajes activos

_Ninguno todavía._
