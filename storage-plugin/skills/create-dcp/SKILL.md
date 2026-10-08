---
name: create-dcp
description: >
  Escribe el plan de cambio de discos (DCP) del NAS para un escenario: fallo de un disco de
  datos (reconstrucción con snapraid fix), fallo de la paridad, sustitución preventiva de un
  disco que se degrada, ampliación con un disco más grande (que pasa a paridad si supera a la
  actual) o retirada de un disco. Incluye diagnóstico, situación de partida y final,
  precondiciones (backup, sync programado desactivado), pasos con riesgo y quién ejecuta,
  verificación, vuelta atrás y cambios en el diseño. Sigue DCP_template.j2.
  También llamado: cambiar un disco, reconstruir un disco, añadir disco, plan de discos.
  Entradas: diagnóstico + HLD aprobado + inventario. Salida: DCP en outputs/dcp/vN/.
  Úsala cuando el usuario pida:
  - Cambiar, sustituir o reemplazar un disco
  - Recuperar los datos de un disco muerto
  - Añadir un disco más grande o ampliar el pool
  - Retirar un disco del NAS
  - Preparar el plan tras un diagnóstico de disco
argument-hint: "[escenario] [disco]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Crear un plan de cambio de discos (DCP)

Eres el experto en discos del NAS. Un DCP mal hecho es la forma más rápida de perder datos en
un NAS con SnapRAID: el orden de los pasos importa más que los comandos. Escribes planes que se
pueden ejecutar con calma, en los que cada paso destructivo lo hace el usuario tras comprobar
el número de serie, y en los que siempre hay una vuelta atrás hasta el último momento posible.

---

## Fase 0: Puertas

1. **HLD aprobado** (tabla de almacenamiento y bahías). Sin él, para.
2. **Diagnóstico**: debe existir `memory/dcp/diagnostico-*.md` reciente para el disco; si no,
   `/storage-plugin:diagnose-disk` primero. Excepción: Ampliación o Retirada planificadas sin
   problema de salud (basta el inventario).
3. **Disco de datos muerto**: confirma que el sync programado ya está desactivado.

## Fase 1: Escenario y disco nuevo

Confirma con `AskUserQuestion` (header ≤ 12 caracteres):
- Escenario: `Fallo de disco de datos`, `Fallo de paridad`, `Sustitución preventiva`,
  `Ampliación` o `Retirada`.
- Disco nuevo: modelo y tamaño **en bytes** si ya está instalado (`lsblk -b`). Comprueba con
  WebSearch que no es SMR si va a ser paridad.
- Si el disco nuevo es mayor que la paridad actual, el plan lo hace paridad y la antigua
  paridad pasa a datos (el validador bloquea lo contrario).

## Fase 2: Reglas por escenario

### Fallo de disco de datos
1. Desactivar el sync programado (primer paso si no se hizo).
2. Confirmar estado con `snapraid status` (lectura). **Ningún sync antes del fix.**
3. Cambiar el disco (físico) e identificarlo (`lsblk` + SMART).
4. Formatear ext4 (OMV, usuario, con comprobación de serie).
5. En SnapRAID, el disco nuevo con **el mismo nombre** (`d1`, `d2`…) y content; en MergerFS,
   sustituir la rama.
6. `snapraid -d dN -l fix.log fix` (destructivo, usuario, comprobación previa de la config).
7. `snapraid -d dN -a check` (lectura), restaurar desde restic lo no recuperable.
8. `sync`; reactivar programación; vigilancia SMART.

### Fallo de paridad
Los datos están intactos. Disco nuevo ≥ mayor disco de datos; ext4 y `tune2fs -m 0`
(usuario); `parity` apuntando al nuevo; `sync` completo; reactivar programación. Mientras no
termine el sync, no hay protección: evita escribir en el pool.

### Sustitución preventiva
Backup restic reciente y sync correcto; desactivar sync programado; instalar e identificar el
nuevo; formatear; copiar con `rsync -aHAX` del viejo al nuevo (cambio, agente); apuntar `dN` al
nuevo en SnapRAID y MergerFS; `diff` sin borrados masivos y `sync`; hd-idle y SMART; retirar el
viejo y guardarlo 30 días.

### Ampliación
- Nuevo ≤ paridad: nuevo `dN+1` en SnapRAID (datos + content) y rama nueva en MergerFS; `sync`.
- Nuevo > paridad: mover la paridad al nuevo (`sync` completo), liberar y formatear la antigua
  paridad y añadirla como dato. Revisa que el disco de backup restic sigue cabiendo con el pool
  más grande (NRD §3) y avísalo si no.

### Retirada
Vaciar el disco hacia el resto del pool con `rsync -aHAX --remove-source-files` solo si cabe
(compruébalo con `df`), quitarlo de MergerFS y de SnapRAID, `sync`, quitar de hd-idle y SMART.

### En todos
Content files ≥ paridades + 1 en discos distintos; hd-idle por `/dev/disk/by-id`; vigilancia
SMART en OMV; actualizar el HLD; foto de configuración al terminar; colocación física (los dos
mecánicos separados, el más caliente en la bahía con más aire).

## Fase 3: Escribir

1. Plantilla: `storage-plugin/skills/create-dcp/DCP_template.j2`.
   Ejemplos: [examples/sample-dcp-fallo-datos.md](examples/sample-dcp-fallo-datos.md) y
   [examples/sample-dcp-ampliacion.md](examples/sample-dcp-ampliacion.md).
2. Reglas por paso de los runbooks: Riesgo (Lectura/Cambio/Destructivo), Ejecuta
   (Agente/Usuario), Dónde, comprobación previa en destructivos, Esperado, Si falla.
   `snapraid fix`, `wipefs`, `mkfs`, `tune2fs -m` y borrados son **siempre del usuario**.
3. Situación final con la tabla exacta de la plantilla (la valida la regla de paridad).
4. Guarda en `$(ls -d outputs/dcp/v* | sort -V | tail -1)/DCP-AAAA-MM-DD-<escenario>-<disco>.md`.

## Fase 4: Validar, registrar y aplicar aprendizajes

1. `/storage-plugin:validate-dcp`; corrige CRITICAL.
2. Nota en `memory/dcp/session-AAAA-MM-DD.md`.
3. Aprendizajes pendientes → `/storage-plugin:apply-learnings`.
4. Siguiente: `/storage-plugin:approve-dcp`, luego `/operator-plugin:create-ops <DCP>` y, al
   cerrar, `/architect-plugin:update-hld` con el cambio.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-dcp", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/dcp/learnings-queue.jsonl
```

---

## Cuatro responsabilidades

1. **Proteger la paridad**: sync programado desactivado; ningún sync antes de un fix.
2. **Tocar el disco correcto**: serie comprobada justo antes de cada paso destructivo.
3. **Mantener las reglas de SnapRAID**: paridad ≥ datos, paridad fuera del pool, content.
4. **Dejar el diseño al día**: HLD, hd-idle, SMART, MergerFS, `state/config/`.

## Prevención de errores

1. **El sync de las 04:00** durante un fallo: el error más caro; por eso es precondición.
2. **"1 TB" no es igual a "1 TB"**: compara bytes; una paridad unos MB menor ya no vale.
3. **Renombrar el disco en SnapRAID** al sustituirlo: el `fix` necesita el mismo nombre `dN`.
4. **Formatear el viejo antes de copiar** en una sustitución preventiva.

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
