# RBK 08 — Usuarios y Samba

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 08 — Usuarios y Samba |
| **Versión** | 2.1 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 2 h + carga de datos (horas, según volumen) |

## Objetivo

Crear el grupo `familia`, los usuarios `carlos` (persona1) y `sabrina` (persona2), sus
privilegios, los recursos SMB sin invitados con papelera `.recycle` de 30 días y
`force user = www-data` en Documentos e Imágenes; después cargar los datos iniciales desde los PC
y lanzar el primer sync con datos (HLD §6, §8). El usuario `descargas` se pospone al proyecto
Pi 4: hasta entonces `Videos` es de solo lectura para `familia`.

## Prerrequisitos

- [ ] RBK 07 completado (OPS-2026-10-13-rbk07-mergerfs-carpetas.md, Aprobado)
- [ ] Contraseñas de `carlos` y `sabrina` creadas en el gestor de contraseñas
- No hace falta sesión web de OMV: los pasos de configuración van por SSH con `omv-rpc`.

## Pasos

Cada comando es **una sola línea**: pégala entera y no pegues varias líneas seguidas tras `ssh nas`.

### Paso 1: Crear el grupo familia

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, §8 |

Comando:

```bash
ssh nas "sudo omv-rpc -u admin UserMgmt setGroup '{\"name\":\"familia\",\"comment\":\"\",\"members\":[]}' && getent group familia"
```

Esperado: `familia:x:<gid>:`.

Si falla: si ya existe, sigue.

### Paso 2: Crear los usuarios

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH (desde el PC) |
| **HLD** | §6, §8 |

La contraseña se teclea en el NAS con `read -rsp` (no se ve, no queda en el PC ni en el repo);
cópiala del gestor de contraseñas. Una línea por usuario:

```bash
ssh -t nas 'read -rsp "Contraseña de carlos: " P; echo; J=$(jq -nc --arg password "$P" "{name:\"carlos\",\$password,shell:\"/usr/sbin/nologin\",groups:[\"users\",\"familia\"],email:\"\",comment:\"\",disallowusermod:false,sshpubkeys:[]}"); unset P; sudo omv-rpc -u admin UserMgmt setUser "$J"; unset J'
```

```bash
ssh -t nas 'read -rsp "Contraseña de sabrina: " P; echo; J=$(jq -nc --arg password "$P" "{name:\"sabrina\",\$password,shell:\"/usr/sbin/nologin\",groups:[\"users\",\"familia\"],email:\"\",comment:\"\",disallowusermod:false,sshpubkeys:[]}"); unset P; sudo omv-rpc -u admin UserMgmt setUser "$J"; unset J'
```

Esperado: cada orden termina sin error; `ssh nas 'id carlos; id sabrina'` muestra los grupos `users` y `familia`.

Si falla: si un nombre ya existe en el sistema, usa el sufijo del gestor y anótalo en el OPS.

### Paso 3: Privilegios por carpeta

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 (tabla de carpetas), §8 |

Comando (uno por carpeta; el `uuid` se obtiene de `ShareMgmt getList`):

```bash
ssh nas "sudo omv-rpc -u admin ShareMgmt getList '{\"start\":0,\"limit\":-1}' | jq -r '.data[] | .name + \" \" + .uuid'"
```

```bash
ssh nas "sudo omv-rpc -u admin ShareMgmt setPrivileges '{\"uuid\":\"<uuid>\",\"privileges\":[{\"type\":\"user\",\"name\":\"carlos\",\"perms\":7},{\"type\":\"user\",\"name\":\"sabrina\",\"perms\":5}]}'"
```

Valores (perms 7 = lectura y escritura, 5 = solo lectura): `Documentos_persona1`: carlos 7, sabrina 5. `Documentos_persona2`: sabrina 7, carlos 5. `Imagenes`: grupo `familia` 7. `Videos`: grupo `familia` 5. `Archivo`: sin privilegios.

Esperado: `ShareMgmt getPrivileges` de cada carpeta devuelve los valores de la tabla.

Si falla: si se asigna mal, corrígelo antes del paso 5.

### Paso 4: Activar Samba

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando: leer `SMB getSettings`, cambiar solo `enable` a `true` y enviarlo con `SMB setSettings`
(el resto por defecto).

Esperado: `SMB getSettings` muestra `"enable": true`.

Si falla: revisa `journalctl -u smbd -n 50`.

### Paso 5: Crear los recursos SMB y aplicar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6 |

Comando: `SMB setShare` para `Documentos_persona1`, `Documentos_persona2`, `Imagenes` y `Videos`
con `guest` = `no`, `recyclebin` = `true`, `recyclemaxage` = `30`, `hidedotfiles` = `true`; en
`Documentos_persona1`, `Documentos_persona2` e `Imagenes`, `extraoptions` =
`force user = www-data` y `force group = www-data`. `Archivo` sin recurso SMB. Después:

```bash
ssh nas 'sudo omv-salt deploy run samba'
```

Esperado: el deploy de `samba` termina con todos los estados correctos (0 fallidos).

Si falla: si la papelera no ofrece antigüedad, anótalo: el borrado de `.recycle` de más de 30 días queda para el mantenimiento.

### Paso 6: Leer la configuración de Samba

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §6, §8 |

Comando:

```bash
ssh nas 'testparm -s 2>/dev/null; sudo pdbedit -L; systemctl is-active smbd'
```

Esperado: cuatro recursos, `guest ok = No`, `vfs objects` con `recycle` en los cuatro, `force user = www-data` en los tres de Documentos e Imagenes; `pdbedit` lista `carlos` y `sabrina`; `smbd` `active`.

Si falla: si falta una opción, vuelve al paso 5.

### Paso 7: Probar el acceso desde los PC

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §6, §8 |

NetBIOS está desactivado en OMV 8: desde Windows usa la IP, no `\\nas`. Borra los ficheros de prueba al terminar.

Esperado: carlos escribe en `\\192.168.1.11\Documentos_persona1` y en `\\192.168.1.11\Imagenes`; sabrina abre `\\192.168.1.11\Documentos_persona1` pero no puede escribir; `\\192.168.1.11\Videos` es de solo lectura; `\\192.168.1.11\Archivo` no existe. En Linux: `smb://192.168.1.11/Imagenes`.

Si falla: si sabrina puede escribir en Documentos_persona1, revisa el paso 3.

### Paso 8: Cargar los datos iniciales

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3 (capacidad), §6 |

Esperado: Documentos de cada persona en su recurso (`\\192.168.1.11\Documentos_persona1`, `\\192.168.1.11\Documentos_persona2`); fotos (incluidas las de WhatsApp antiguas) en `\\192.168.1.11\Imagenes`, fuera de `Imagenes/Moviles`. Ningún error de copia. Las películas de `Videos` no se pueden copiar por SMB (solo lectura para `familia`): quedan para el proyecto Pi 4 o se copian con el agente a `/srv/mergerfs/pool/Videos` en un paso aparte anotado en el OPS.

Si falla: si la copia se corta, repítela: el Explorador o `rsync` en Linux saltan lo ya copiado.

### Paso 9: Comprobar el reparto entre D1 y D2

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 MergerFS, ADR-016 |

Comando:

```bash
ssh nas 'df -h /srv/dev-disk-by-uuid-* /srv/mergerfs/pool'
```

Esperado: D1 y D2 con uso parecido (diferencia menor de 100 GB, política `mfs`) y al menos 20G libres en cada uno.

Si falla: si un disco tiene menos de 20G libres, para y avisa al arquitecto (riesgo «Pool lleno»).

### Paso 10: Primer sync de SnapRAID con datos

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, §7 |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf sync && sudo snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf status'
```

Lánzalo de día, lejos de la ventana 23:00-01:00.

Esperado: el sync termina con `Everything OK` (horas con ~1,2 TB) y `status` dice `No error detected`.

Si falla: si el sync se para por el umbral o por errores de lectura, guarda la salida en el OPS y llama a `/storage-plugin:diagnose-disk`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Recursos SMB | `ssh nas "testparm -s 2>/dev/null \| grep -c '^\['"` | 5 (global + 4 recursos) |
| Sin invitados | `ssh nas "testparm -s 2>/dev/null \| grep -ci 'guest ok = yes'"` | 0 |
| Usuarios Samba | `ssh nas 'sudo pdbedit -L \| wc -l'` | 2 |
| SnapRAID | `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-358857d2-7c5b-415d-a2e0-3997c6f6b385.conf status'` | No error detected |

## Vuelta atrás

Los recursos, privilegios y usuarios se borran en orden inverso (`SMB deleteShare`,
`ShareMgmt setPrivileges` vacío, `UserMgmt deleteUser`, `UserMgmt deleteGroup`) y se aplica con
`omv-salt deploy run samba`. Los datos copiados siguen en los PC de origen hasta terminar el
RBK 11 (primer backup); no los borres de los PC antes.

## Evidencias

- Salida de `testparm -s` en `state/config/`
- `df -h` tras la carga en el OPS
- Salida del primer sync con datos en el OPS
- Capturas 8.1 a 8.3 en el OPS

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.1 | 2026-10-13 | Runbook Agent | Escenario C (cambio menor, fuente memory/ops/session-2026-10-13.md): cita HLD v2 (2.1); prerrequisito RBK 07 por su OPS aprobado, sin sesión web; persona1 = `carlos`, persona2 = `sabrina`; `descargas` pospuesto al proyecto Pi 4 (`Videos`: familia solo lectura); pasos 1 y 3-5 por el Agente con `omv-rpc` y `omv-salt deploy run samba`; paso 2 por el Usuario con `read -rsp` en el NAS y `UserMgmt setUser`; rutas `\\192.168.1.11\<recurso>` (NetBIOS desactivado en OMV 8); conf exacta de SnapRAID en el paso 10. Los pasos 1-6 se ejecutaron el 2026-10-13 antes de esta aprobación (incidencia registrada en el OPS del RBK 08) |
| 2.1 | 2026-10-13 | Runbook Agent | Aprobado (visto bueno del usuario 2026-10-13) |
