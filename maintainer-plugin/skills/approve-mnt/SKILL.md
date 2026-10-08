---
name: approve-mnt
description: >
  Aprueba (da por revisado) un informe de mantenimiento (MNT): exige 0 CRITICAL, que las
  acciones de prioridad Alta tengan responsable y fecha, lo pasa a Aprobado y propone el commit.
  También llamado: cerrar la revisión periódica, dar por revisado el informe.
  Úsala cuando el usuario pida:
  - Aprobar o cerrar el informe de mantenimiento
  - Dar por hecha la revisión mensual
argument-hint: "[fichero MNT]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar un informe de mantenimiento (MNT)

## Paso 1: Localizar
`$ARGUMENTS` o el MNT más reciente sin aprobar en `outputs/mnt/v*`.

## Paso 2: Comprobaciones
1. Ya aprobado → informa y para.
2. Validación (puerta):
   ```bash
   uv run python maintainer-plugin/skills/validate-mnt/scripts/validate_mnt.py "$FILE"
   ```
   Salida 1 → no se aprueba; salida 2 → enseña avisos y pregunta.
3. Semáforo Rojo: enumera las acciones de prioridad Alta en la confirmación; aprobar el informe
   **no** las cierra.

## Paso 3: Aprobar (solo con Edit)
Estado → `Aprobado`; Última modificación → hoy; historial
`| <versión> | <hoy> | Maintainer Agent | Revisado y aprobado |`.

## Paso 4: Traza en git
Pregunta si se hace commit; si sí:
```bash
git add "$FILE" memory/mnt/
git commit -m "Aprueba MNT <periodo> <fecha>: semáforo <color>"
```
Nunca push.

## Paso 5: Informe
Fichero, semáforo y acciones Altas pendientes con su skill.

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
