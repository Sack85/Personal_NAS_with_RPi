# RBK 07 — MergerFS y carpetas compartidas

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 07 — MergerFS y carpetas compartidas |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 1 h |

## Objetivo

Unir D1 y D2 en el pool MergerFS `pool` (`/srv/mergerfs/pool`) con política `mfs`, 20G libres y las
opciones del HLD, y crear las carpetas compartidas y las subcarpetas de Documentos, Imágenes y
Archivo con el propietario `www-data` donde Nextcloud debe escribir (HLD §5 MergerFS, §6, ADR-016).

## Prerrequisitos

- [ ] RBK 06 completado: array `nas` sin errores
- [ ] Sesión iniciada por el usuario en la web de OMV

## Pasos

### Paso 1: Crear el pool

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 MergerFS, ADR-016 |

Esperado: Almacenamiento → mergerfs → Crear: nombre `pool`; sistemas de archivos D1 y D2 (nunca la paridad); política de creación `mfs`; espacio libre mínimo `20G`; opciones `cache.files=off,dropcacheonclose=true,category.search=ff`. Guardado y aplicado.

Si falla: si OMV no acepta una opción, guarda sin ella, anótala y avisa al arquitecto.

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
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 |

Esperado: Almacenamiento → Carpetas compartidas, sobre el sistema de archivos `pool`: `Documentos_persona1` (ruta `Documentos/persona1/`), `Documentos_persona2` (ruta `Documentos/persona2/`), `Imagenes` (`Imagenes/`), `Videos` (`Videos/`) y `Archivo` (`Archivo/`).

Si falla: si OMV crea la ruta con otro nombre, renómbrala antes de seguir: los RBK 08, 10, 11 y 15 usan estas rutas.

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

Borrar el pool y las carpetas compartidas en OMV (en orden inverso a su creación); los ficheros
de cada disco siguen en sus ramas. Las subcarpetas vacías se dejan o las borra el usuario.

## Evidencias

- Salida de `ps -eo args | grep mergerfs` en el OPS
- Capturas 7.1 y 7.2 en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| Para que el «otro» tenga solo lectura por SMB en `Documentos/personaN` (HLD §6 tabla de carpetas), el runbook crea una carpeta compartida por persona (`Documentos_persona1/2`) en lugar de una sola `Documentos`. Confirmar con el arquitecto y reflejar en el HLD | Persona 1 | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
