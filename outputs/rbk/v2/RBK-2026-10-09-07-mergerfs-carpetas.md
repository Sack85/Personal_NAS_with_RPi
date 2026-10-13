# RBK 07 — MergerFS y carpetas compartidas

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 07 — MergerFS y carpetas compartidas |
| **Versión** | 2.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h |

## Objetivo

Unir D1 y D2 en el pool MergerFS `pool` (`/srv/mergerfs/pool`) con política `mfs`, 20G libres y las
opciones del HLD, y crear las carpetas compartidas y las subcarpetas de Documentos, Imágenes y
Archivo con el propietario `www-data` donde Nextcloud debe escribir (HLD §5 MergerFS, §6, ADR-016).

## Prerrequisitos

- [ ] RBK 06 completado: array `nas` sin errores (OPS-2026-10-13-rbk06-snapraid, Aprobado)
- [ ] Sin sesión web: la configuración se hace por SSH con `omv-rpc` (desviación aceptada en las fases 04-06)
- [ ] Mntentref de los discos: D1 `16149efb-1cfa-413c-9299-f76789695e51`, D2 `96abea2b-3167-46f5-9aef-5901943d833d`; la paridad (`1901249d…`) nunca entra en el pool

## Pasos

### Paso 1: Crear el pool

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc` del plugin mergerfs; desviación aceptada en las fases 04-06) |
| **HLD** | §5 MergerFS, ADR-016 |

Comando (una orden por línea; no pegues varias líneas tras `ssh nas`):

```bash
ssh -t nas "sudo omv-rpc -u admin Mergerfs set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"pool\",\"mntentref\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"filesystems\":[\"16149efb-1cfa-413c-9299-f76789695e51\",\"96abea2b-3167-46f5-9aef-5901943d833d\"],\"paths\":null,\"sharedfolderrefs\":[],\"createpolicy\":\"mfs\",\"minfreespace\":20,\"minfreespaceunit\":\"G\",\"options\":\"cache.files=off,dropcacheonclose=true,category.search=ff\"}'"
ssh -t nas "sudo omv-salt deploy run mergerfs"
ssh -t nas "sudo omv-salt deploy run fstab"
ssh -t nas "sudo omv-rpc -u admin Mergerfs getList '{\"start\":0,\"limit\":-1}'"
```

Esperado: `set` devuelve el objeto con un `uuid` y un `mntentref` nuevos (no el uuid de plantilla); `filesystems` contiene solo los mntentref de D1 y D2; los dos `deploy` terminan sin `Failed`; `getList` muestra un único pool `pool` con `createpolicy` `mfs`, `minfreespace` 20 G y las opciones del HLD. El `deploy run fstab` solo hace falta si el pool no queda montado tras el de mergerfs (ver paso 2).

Si falla: si `omv-rpc` rechaza un campo, lee la firma con `sudo omv-rpc -u admin Mergerfs getList '{"start":0,"limit":-1}'`, anótalo en el OPS y para. Si `filesystems` incluye `1901249d…` (paridad), borra el pool y repite.

### Paso 2: Comprobar el pool montado y sus opciones

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 MergerFS |

Comando:

```bash
ssh nas 'findmnt /srv/mergerfs/pool; df -h /srv/mergerfs/pool; ps -eo args | grep "[m]ergerfs"'
```

Esperado: `/srv/mergerfs/pool` montado de tipo `fuse.mergerfs`, ~1,8 T de tamaño y el proceso con `category.create=mfs`, `minfreespace=20G`, `cache.files=off`, `dropcacheonclose=true` y `category.search=ff`, solo con las ramas de D1 y D2.

Si falla: si aparece la rama de la paridad, borra el pool y vuelve al paso 1.

### Paso 3: Crear las carpetas compartidas

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH (`omv-rpc`; desviación aceptada en las fases 04-06) |
| **HLD** | §6 |

Comando: primero lee el mntentref del pool; después, una orden `ShareMgmt set` por carpeta con ese valor en `<mntent-pool>` (una orden por línea; no pegues varias líneas tras `ssh nas`):

```bash
ssh -t nas "sudo omv-confdbadm read conf.system.filesystem.mountpoint | grep -B2 -A2 mergerfs"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"Documentos_persona1\",\"mntentref\":\"<mntent-pool>\",\"reldirpath\":\"Documentos/persona1/\",\"mode\":\"775\",\"comment\":\"\"}'"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"Documentos_persona2\",\"mntentref\":\"<mntent-pool>\",\"reldirpath\":\"Documentos/persona2/\",\"mode\":\"775\",\"comment\":\"\"}'"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"Imagenes\",\"mntentref\":\"<mntent-pool>\",\"reldirpath\":\"Imagenes/\",\"mode\":\"775\",\"comment\":\"\"}'"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"Videos\",\"mntentref\":\"<mntent-pool>\",\"reldirpath\":\"Videos/\",\"mode\":\"775\",\"comment\":\"\"}'"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt set '{\"uuid\":\"fa4b1c66-ef79-11e5-87a0-0002b3a176b4\",\"name\":\"Archivo\",\"mntentref\":\"<mntent-pool>\",\"reldirpath\":\"Archivo/\",\"mode\":\"775\",\"comment\":\"\"}'"
ssh -t nas "sudo omv-salt deploy run sharedfolders"
ssh -t nas "sudo omv-rpc -u admin ShareMgmt getList '{\"start\":0,\"limit\":-1}' | grep -o '\"name\":\"[^\"]*\"' | sort | uniq -c"
```

Esperado: el `read` muestra una sola entrada con `fsname` del pool mergerfs y `dir` `/srv/mergerfs/pool`, y su `uuid` es `<mntent-pool>` (nunca un mntentref de D1, D2 o la paridad); cada `set` devuelve un `uuid` nuevo; `deploy run sharedfolders` sin `Failed` (si el módulo no existe en esta versión, se anota y se sigue: las carpetas quedan en la base de datos); el último `grep` da exactamente 5 nombres, cada uno con `1` (sin duplicados): `Archivo`, `Documentos_persona1`, `Documentos_persona2`, `Imagenes`, `Videos`.

Si falla: si algún nombre sale con `2`, borra el duplicado con `ShareMgmt delete` antes de seguir; si OMV crea la ruta con otro nombre, corrígela antes de seguir: los RBK 08, 10, 11 y 15 usan estas rutas.

### Paso 4: Crear subcarpetas y propietario www-data

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, §7 |

Comando:

```bash
ssh nas 'sudo mkdir -p /srv/mergerfs/pool/Documentos/persona1 /srv/mergerfs/pool/Documentos/persona2 /srv/mergerfs/pool/Imagenes/Moviles /srv/mergerfs/pool/Videos /srv/mergerfs/pool/Archivo/nextcloud-aio-backup /srv/mergerfs/pool/Archivo/immich-db'
ssh nas 'sudo chown -R www-data:www-data /srv/mergerfs/pool/Documentos /srv/mergerfs/pool/Imagenes'
```

Esperado: carpetas creadas; Documentos e Imagenes con propietario `www-data:www-data` (lo exige Nextcloud y el `force user` de Samba).

Si falla: si `chown` falla, comprueba que el pool está montado (paso 2).

### Paso 5: Comprobar el árbol de carpetas

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando:

```bash
ssh nas 'ls -la /srv/mergerfs/pool /srv/mergerfs/pool/Documentos /srv/mergerfs/pool/Imagenes /srv/mergerfs/pool/Archivo'
```

Esperado: `Documentos/persona1`, `Documentos/persona2`, `Imagenes/Moviles` de `www-data`; `Videos`, `Archivo/nextcloud-aio-backup` y `Archivo/immich-db` presentes.

Si falla: si falta una, repite el paso 4.

### Paso 6: Prueba de escritura en el pool

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 MergerFS |

Comando:

```bash
ssh nas 'sudo touch /srv/mergerfs/pool/Videos/.prueba && ls /srv/dev-disk-by-uuid-*/Videos/.prueba'
ssh nas 'sudo rm /srv/mergerfs/pool/Videos/.prueba'
```

Esperado: el fichero aparece en una sola rama (D1 o D2) y se borra sin error.

Si falla: si la escritura falla con «No space left», revisa `minfreespace` en el paso 2.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Pool montado | `ssh nas 'findmnt -n -o FSTYPE /srv/mergerfs/pool'` | fuse.mergerfs |
| Tamaño | `ssh nas 'df -h /srv/mergerfs/pool'` | ~1,8T |
| Propietario | `ssh nas 'stat -c %U /srv/mergerfs/pool/Imagenes'` | www-data |

## Vuelta atrás

Borrar las carpetas compartidas (`ShareMgmt delete`) y después el pool (`Mergerfs delete` + `omv-salt deploy run mergerfs fstab`) (en orden inverso a su creación); los ficheros
de cada disco siguen en sus ramas. Las subcarpetas vacías se dejan o las borra el usuario.

## Evidencias

- Salida de `ps -eo args | grep mergerfs` en el OPS
- Salidas de `Mergerfs getList` y `ShareMgmt getList` en el OPS (sin capturas: no hay sesión web)

## Preguntas abiertas

Ninguna. Cerrada el 2026-10-13: el usuario acepta dos carpetas compartidas `Documentos_persona1` y `Documentos_persona2` (requisito: cada persona escribe en la suya y lee la del otro; los permisos SMB se ponen en el RBK 08).

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-13 | Runbook Agent | Cita HLD v2 (2.1); prerrequisito OPS-2026-10-13-rbk06 Aprobado, sin sesión web. Pasos 1 y 3 pasan a Agente por SSH con `omv-rpc` (`Mergerfs set`, `ShareMgmt set`, `omv-salt deploy`), desviación aceptada como en 04-06; paridad excluida. Cerrada la pregunta de `Documentos_persona1/2` (aceptada por el usuario) |
| 2.1 | 2026-10-13 | Runbook Agent | Estado cambiado a Aprobado (visto bueno del usuario 2026-10-13) |
