---
name: approve-dcp
description: >
  Aprueba un plan de cambio de discos (DCP): exige 0 CRITICAL, HLD citado vigente y, salvo en
  un fallo de disco de datos, backup restic de menos de 7 días; enumera los pasos destructivos
  y el punto sin vuelta atrás; lo pasa a Aprobado y propone el commit.
  También llamado: dar luz verde al cambio de disco.
  Úsala cuando el usuario pida:
  - Aprobar el plan de cambio de discos
  - Dar el visto bueno para cambiar o reconstruir un disco
argument-hint: "[fichero DCP]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar un plan de cambio de discos (DCP)

## Paso 1: Localizar
`$ARGUMENTS` o el DCP más reciente sin aprobar en `outputs/dcp/v*`.

## Paso 2: Comprobaciones
1. Ya aprobado → informa y para.
2. HLD citado = última versión Aprobada.
3. Validación (puerta):
   ```bash
   uv run python storage-plugin/skills/validate-dcp/scripts/validate_dcp.py "$FILE"
   ```
   Salida 1 → no se aprueba; salida 2 → enseña avisos y pregunta.
4. Backup: salvo en `Fallo de disco de datos` (donde no se puede esperar), el último restic debe
   tener menos de 7 días; si no, propone hacerlo antes (RBK 11).
5. En la confirmación con `AskUserQuestion`, enumera los pasos Destructivos y di cuál es el
   **último punto con vuelta atrás completa** según la sección Vuelta atrás.

## Paso 3: Aprobar (solo con Edit)
Estado → `Aprobado`; Última modificación → hoy; historial
`| <versión> | <hoy> | Storage Agent | Estado cambiado a Aprobado |`. Revalida.

## Paso 4: Traza en git
Pregunta si se hace commit; si sí:
```bash
git add "$FILE" memory/dcp/
git commit -m "Aprueba DCP <vN>: <escenario> <disco>"
```
Nunca push.

## Paso 5: Informe
Fichero y siguiente paso: `/operator-plugin:create-ops <DCP>`; al cerrar el OPS,
`/architect-plugin:update-hld` y `/operator-plugin:snapshot-config`.

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
