# RBK 08 — Usuarios y Samba

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 08 — Usuarios y Samba |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 2 h + carga de datos (horas, según volumen) |

## Objetivo

Crear el grupo `familia`, los usuarios `persona1`, `persona2` y `descargas`, sus privilegios, los
recursos SMB sin invitados con papelera `.recycle` de 30 días y `force user = www-data` en
Documentos e Imágenes; después cargar los datos iniciales desde los PC y lanzar el primer sync
con datos (HLD §6, §8).

## Prerrequisitos

- [ ] RBK 07 completado: pool y carpetas compartidas
- [ ] Contraseñas de `persona1`, `persona2` y `descargas` creadas en el gestor de contraseñas
- [ ] Sesión iniciada por el usuario en la web de OMV

## Pasos

### Paso 1: Crear el grupo familia

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6, §8 |

Esperado: Usuarios → Grupos → Crear `familia`.

Si falla: si ya existe, sigue.

### Paso 2: Crear los usuarios

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6, §8 |

Esperado: Usuarios → Usuarios: `persona1` y `persona2` en `familia`; `descargas` fuera de `familia`. Contraseñas tecleadas por el usuario desde el gestor de contraseñas.

Si falla: si un nombre ya existe en el sistema, usa el sufijo del gestor y anótalo en el OPS.

### Paso 3: Privilegios por carpeta

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 (tabla de carpetas), §8 |

Esperado: `Documentos_persona1`: persona1 lectura y escritura, persona2 solo lectura. `Documentos_persona2`: a la inversa. `Imagenes`: familia lectura y escritura. `Videos`: familia solo lectura, descargas lectura y escritura. `Archivo`: sin acceso para todos.

Si falla: si se asigna mal, corrígelo antes del paso 5.

### Paso 4: Activar Samba

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 |

Esperado: Servicios → SMB/CIFS → Configuración: activado; el resto por defecto.

Si falla: si no arranca, revisa Diagnósticos → Registros.

### Paso 5: Crear los recursos SMB

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §6 |

Esperado: Recursos compartidos: `Documentos_persona1`, `Documentos_persona2`, `Imagenes` y `Videos`; invitados no permitidos; papelera de reciclaje activada con antigüedad máxima 30 días. En `Documentos_persona1`, `Documentos_persona2` e `Imagenes`, Opciones extra: `force user = www-data` y `force group = www-data`. `Archivo` sin recurso SMB.

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
ssh nas 'testparm -s 2>/dev/null'
```

Esperado: cuatro recursos, `guest ok = No`, `vfs objects` con `recycle` en los cuatro y `force user = www-data` en los tres de Documentos e Imagenes.

Si falla: si falta una opción, vuelve al paso 5.

### Paso 7: Probar el acceso desde los PC

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §6, §8 |

Borra los ficheros de prueba al terminar.

Esperado: persona1 escribe en `\\nas\Documentos_persona1` y en `\\nas\Imagenes`; persona2 abre `\\nas\Documentos_persona1` pero no puede escribir; `\\nas\Archivo` no existe. En Linux: `smb://nas.local/Imagenes`.

Si falla: si persona2 puede escribir en Documentos_persona1, revisa el paso 3.

### Paso 8: Cargar los datos iniciales

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3 (capacidad), §6 |

Esperado: Documentos de cada persona en su recurso; fotos (incluidas las de WhatsApp antiguas) en `Imagenes`, fuera de `Imagenes/Moviles`; películas en `Videos`. Ningún error de copia.

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
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync && sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'
```

Lánzalo de día, lejos de la ventana 23:00-01:00.

Esperado: el sync termina con `Everything OK` (horas con ~1,2 TB) y `status` dice `No error detected`.

Si falla: si el sync se para por el umbral o por errores de lectura, guarda la salida en el OPS y llama a `/storage-plugin:diagnose-disk`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Recursos SMB | `ssh nas "testparm -s 2>/dev/null \| grep -c '^\['"` | 5 (global + 4 recursos) |
| Sin invitados | `ssh nas "testparm -s 2>/dev/null \| grep -ci 'guest ok = yes'"` | 0 |
| SnapRAID | `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'` | No error detected |

## Vuelta atrás

Los recursos, privilegios y usuarios se borran en OMV en orden inverso. Los datos copiados
siguen en los PC de origen hasta terminar el RBK 11 (primer backup); no los borres de los PC antes.

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
