---
name: update-upd
description: >
  Actualiza un plan de actualización (UPD): nuevas versiones aparecidas antes de ejecutarlo,
  cambio de decisión (aplicar/posponer), ventana distinta, o corrección tras un fallo en la
  ejecución (incidencia en un OPS). Versiona con las reglas A/B/C, edita solo con Edit y deja
  el UPD En revisión.
  También llamado: revisar el plan de actualización, posponer un paquete.
  Entradas: UPD existente + inventario nuevo u OPS con incidencia. Salida: UPD actualizado.
  Úsala cuando el usuario pida:
  - Cambiar o revisar un plan de actualización
  - Posponer o añadir un paquete al UPD
  - Rehacer el plan tras un fallo al actualizar
  - Ajustar la ventana de mantenimiento
argument-hint: "[fichero UPD]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Actualizar un plan de actualización (UPD)

Eres el mantenedor del NAS. Ajustas un plan sin perder la versión que se aprobó o ejecutó.

## Paso 1: Leer
1. UPD (`$ARGUMENTS` o el más reciente de `outputs/upd/v*`).
2. Inventario más reciente; si es posterior al del UPD, ejecuta `tools/inventory_diff.py` entre
   ambos para ver qué apareció.
3. OPS que ejecutaron este UPD (`grep -l "UPD v" outputs/ops/v*/*.md`) e incidencias.
4. `memory/upd/`.

## Paso 2: Puertas
- Si el UPD ya se ejecutó con Resultado Completado, no se edita: se crea uno nuevo con
  `/maintainer-plugin:create-upd`.
- Si el motivo es una incidencia, debe estar en un OPS.
- Componentes nuevos de kernel, firmware u OMV: notas de versión obligatorias (como en create-upd).

## Paso 3: Preguntar y confirmar
`AskUserQuestion` para decisiones (Aplicar / Posponer / Descartar) y confirma el resumen.

## Paso 4: Versionado y edición
- **A — versión nueva** (UPD aprobado con cambio de fondo, o ejecutado Parcial/Abortado):
  `mkdir outputs/upd/v<N+1>` y copia con la fecha de hoy; se conserva el anterior.
- **B — mismo vN, otro día**: copia con fecha de hoy, anterior a `.bak`; versión menor +1.
- **C — mismo día**: en el sitio; versión menor +1.

Solo Edit; Inventario actualizado si cambió; Estado `En revisión`; fila en el historial con el
motivo (cita el OPS si viene de un fallo).

## Paso 5: Validar y cerrar
1. `/maintainer-plugin:validate-upd`; corrige CRITICAL.
2. Nota en `memory/upd/session-AAAA-MM-DD.md`; aprendizajes → `/maintainer-plugin:apply-learnings`.
3. Siguiente: `/maintainer-plugin:approve-upd`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-upd", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/upd/learnings-queue.jsonl
```

## Prevención de errores
1. Editar un UPD ya ejecutado: rompe la trazabilidad con su OPS.
2. Añadir un kernel "de paso" sin notas de versión ni comprobación de PCIe.

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
