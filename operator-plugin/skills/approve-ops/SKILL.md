---
name: approve-ops
description: >
  Cierra y aprueba un registro de ejecución (OPS): exige que no tenga CRITICAL y que el
  Resultado sea Completado (o Parcial aceptado por el usuario), lo pasa a Aprobado, actualiza
  state/applied.yaml con lo que queda aplicado en el NAS y propone el commit.
  También llamado: cerrar la ejecución, dar por aplicada una fase.
  Úsala cuando el usuario pida:
  - Aprobar o cerrar un OPS
  - Dar por terminada una fase, una actualización o un cambio de disco
  - Registrar qué está aplicado en el NAS
argument-hint: "[fichero OPS]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Cerrar y aprobar un OPS

## Paso 1: Localizar

`$ARGUMENTS` o el OPS más reciente en `En revisión`:

```bash
grep -l '| \*\*Estado\*\* | En revisión |' outputs/ops/v*/OPS-*.md
```

## Paso 2: Comprobaciones

1. Ya aprobado → informa y para.
2. Validación (puerta):
   ```bash
   uv run python operator-plugin/skills/validate-ops/scripts/validate_ops.py "$FILE"
   ```
   Salida 1 → no se aprueba.
3. Resultado:
   - `En curso` → no se aprueba; propone `/operator-plugin:update-ops`.
   - `Parcial` o `Abortado` → enseña las incidencias y pregunta con `AskUserQuestion` si se
     cierra así ("Cerrar como Parcial" / "Seguir antes"). Un Abortado **no** marca nada como
     aplicado.

## Paso 3: Aprobar (solo con Edit)

1. Estado → `Aprobado`; Última modificación → hoy.
2. Historial: `| X.Y | hoy | Operator Agent | Ejecución cerrada y aprobada |`.

## Paso 4: Actualizar `state/applied.yaml` (solo si Completado o Parcial aceptado)

Con Edit, en la clave del tipo de documento:

```yaml
rbk:
  "05":
    version: v1
    fichero: RBK-2026-10-12-05-discos.md
    ops: OPS-2026-10-13-rbk05-discos.md
    fecha: 2026-10-13
    resultado: Completado
```

- RBK: clave = número de fase (sustituye la entrada anterior de esa fase).
- UPD y DCP: añade un elemento a la lista con fichero, OPS, fecha y resultado.
- `hld`: versión del HLD que citan los documentos aplicados.

## Paso 5: Traza en git

Pregunta si se hace commit ("Sí, commit" / "No, lo hago yo"). Si sí:

```bash
git add "$FILE" state/ memory/ops/
git commit -m "Cierra OPS <doc>: <resultado>"
```

Nunca hagas push.

## Paso 6: Informe

Fichero, resultado, qué queda aplicado, incidencias con seguimiento abierto y siguiente paso
lógico (siguiente fase, o `/maintainer-plugin:inventory` tras una actualización).

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
