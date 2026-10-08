---
name: approve-rbk
description: >
  Aprueba un runbook (RBK) del NAS: comprueba que no tiene CRITICAL y que cita la última
  versión aprobada del HLD, cambia el Estado a Aprobado, añade la fila al historial y propone
  el commit. Solo los runbooks aprobados se pueden ejecutar con el operador.
  También llamado: dar por bueno un procedimiento, liberar un runbook.
  Úsala cuando el usuario pida:
  - Aprobar un runbook o una fase
  - Dejar listo un runbook para ejecutarlo
  - Aprobar todos los runbooks de una versión
argument-hint: "<fichero-rbk|todas>"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar runbooks (RBK)

Eres el autor de runbooks. Apruebas formalmente un runbook para que el operador lo ejecute.

## Paso 1: Localizar

`$ARGUMENTS` = fichero o `todas`. Si falta, lista los de la última versión que no están
aprobados y pregunta cuál con `AskUserQuestion`:

```bash
LATEST_DIR=$(ls -d outputs/rbk/v* | sort -V | tail -1)
grep -L '| \*\*Estado\*\* | Aprobado |' "$LATEST_DIR"/RBK-*.md
```

## Paso 2: Comprobaciones (por fichero)

1. **Ya aprobado**: infórmalo y sigue con el siguiente.
2. **HLD citado**: debe ser la última versión **Aprobada** del HLD. Si hay una más nueva, no se
   aprueba: propone `/runbook-plugin:update-rbk`.
3. **Validación (puerta)**:
   ```bash
   uv run python runbook-plugin/skills/validate-rbk/scripts/validate_rbk.py "$FILE"
   ```
   Salida 1 → no se aprueba. Salida 2 → enseña los avisos y pregunta si se aprueba igual.
4. **Pasos destructivos**: enuméralos (número y título) en la pregunta de confirmación para que
   el usuario apruebe sabiendo qué borrará.

## Paso 3: Aprobar (solo con Edit)

1. `| **Estado** | <actual> |` → `| **Estado** | Aprobado |`
2. `| **Última modificación** |` → hoy
3. Historial: `| <versión> | <hoy> | Runbook Agent | Estado cambiado a Aprobado |`

Revalida.

## Paso 4: Traza en git

Pregunta con `AskUserQuestion` si se hace commit ("Sí, commit" / "No, lo hago yo"). Si sí:

```bash
git add <ficheros aprobados> memory/rbk/
git commit -m "Aprueba RBK <vN>: <fases>"
```

Nunca hagas push.

## Paso 5: Confirmar y registrar

- Informa: ficheros, versión y que se pueden ejecutar con `/operator-plugin:create-ops <fichero>`.
- Nota en `memory/rbk/session-AAAA-MM-DD.md`.

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
