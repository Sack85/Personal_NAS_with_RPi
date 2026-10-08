---
name: update-mnt
description: >
  Actualiza un informe de mantenimiento (MNT): marcar acciones hechas, añadir una evidencia o un
  resultado que faltaba (filtro, SAI, copia exterior), o corregir el semáforo. Edita solo con
  Edit y deja el MNT En revisión.
  También llamado: completar la revisión, cerrar acciones del mantenimiento.
  Entradas: MNT existente. Salida: MNT actualizado.
  Úsala cuando el usuario pida:
  - Completar o corregir el informe de mantenimiento
  - Marcar como hecha una acción del MNT
  - Añadir el resultado de una tarea pendiente
argument-hint: "[fichero MNT]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Actualizar un informe de mantenimiento (MNT)

## Paso 1: Leer
MNT (`$ARGUMENTS` o el más reciente), OPS y DCP posteriores que cierren acciones, `memory/mnt/`.

## Paso 2: Cambios permitidos
- Resultado de una tarea que estaba pendiente de confirmar, con evidencia.
- Acción hecha: añade "Hecho AAAA-MM-DD (OPS/DCP …)" en la fila; no se borra.
- Semáforo: solo baja (Rojo → Ámbar → Verde) cuando todas las acciones de prioridad Alta están
  hechas y verificadas; si no, se mantiene.
- Los valores SMART y de temperatura registrados **no se cambian**: son la foto de esa fecha.

Confirma con `AskUserQuestion` antes de editar.

## Paso 3: Versionado y edición
Mismo día: en el sitio; otro día: copia con la fecha de hoy y anterior a `.bak`. Versión menor
+1, Estado `En revisión`, fila en el historial.

## Paso 4: Validar y cerrar
`/maintainer-plugin:validate-mnt`; nota en `memory/mnt/session-AAAA-MM-DD.md`; siguiente
`/maintainer-plugin:approve-mnt`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-mnt", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/mnt/learnings-queue.jsonl
```

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
