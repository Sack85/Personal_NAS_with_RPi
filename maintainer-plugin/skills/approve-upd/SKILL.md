---
name: approve-upd
description: >
  Aprueba un plan de actualización (UPD): exige 0 CRITICAL, HLD citado vigente, inventario de
  menos de 3 días y ninguna alerta CRITICAL nueva en el inventario; lo pasa a Aprobado, añade la
  fila al historial y propone el commit. Solo un UPD aprobado se puede ejecutar.
  También llamado: dar luz verde a la actualización.
  Úsala cuando el usuario pida:
  - Aprobar el plan de actualización
  - Dar el visto bueno para actualizar el NAS
argument-hint: "[fichero UPD]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar un plan de actualización (UPD)

## Paso 1: Localizar
`$ARGUMENTS` o el UPD más reciente de `outputs/upd/v*` sin aprobar.

## Paso 2: Comprobaciones
1. Ya aprobado → informa y para.
2. HLD citado = última versión Aprobada; si no, `/maintainer-plugin:update-upd`.
3. Validación (puerta):
   ```bash
   uv run python maintainer-plugin/skills/validate-upd/scripts/validate_upd.py "$FILE"
   ```
   Salida 1 → no se aprueba; salida 2 → enseña avisos y pregunta.
4. Frescura: el inventario citado tiene menos de 3 días. Si no, pide un inventario nuevo
   (`/maintainer-plugin:inventory`) y `update-upd` antes de aprobar.
5. Salud: `uv run python tools/inventory_diff.py <inventario citado>`; con alertas CRITICAL no
   se aprueba salvo decisión explícita del usuario por seguridad, que se anota en el historial.
6. Enumera en la confirmación los pasos de Cambio con reinicio y la ventana.

## Paso 3: Aprobar (solo con Edit)
Estado → `Aprobado`; Última modificación → hoy; historial
`| <versión> | <hoy> | Maintainer Agent | Estado cambiado a Aprobado |`. Revalida.

## Paso 4: Traza en git
Pregunta si se hace commit; si sí:
```bash
git add "$FILE" memory/upd/
git commit -m "Aprueba UPD <vN>: <corto>"
```
Nunca push.

## Paso 5: Informe
Fichero, ventana y siguiente paso: `/operator-plugin:create-ops <UPD>` dentro de la ventana.

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
