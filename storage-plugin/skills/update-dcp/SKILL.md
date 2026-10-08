---
name: update-dcp
description: >
  Actualiza un plan de cambio de discos (DCP): otro disco nuevo distinto del previsto, cambio de
  escenario tras más diagnóstico, o corrección tras una incidencia al ejecutarlo. Versiona con
  las reglas A/B/C, edita solo con Edit y deja el DCP En revisión.
  También llamado: corregir el plan de discos, cambiar el disco previsto.
  Entradas: DCP existente + diagnóstico u OPS con incidencia. Salida: DCP actualizado.
  Úsala cuando el usuario pida:
  - Cambiar el disco nuevo del plan
  - Corregir el DCP tras un fallo al ejecutarlo
  - Cambiar de escenario (p. ej. de preventiva a fallo)
argument-hint: "[fichero DCP]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch
context: fork
---

# Actualizar un plan de cambio de discos (DCP)

## Paso 1: Leer
DCP (`$ARGUMENTS` o el más reciente), diagnósticos de `memory/dcp/`, OPS que lo ejecutaron
(`grep -l "DCP v" outputs/ops/v*/*.md`) y su estado en `state/applied.yaml`.

## Paso 2: Puertas
- **Ejecución a medias** (OPS En curso o Parcial): antes de editar, determina en qué paso se
  quedó y el estado real del NAS con lecturas (`lsblk`, `grep` de la config de SnapRAID,
  `snapraid status`). El DCP corregido debe partir de ese estado, no del inicial.
- **Cambio de escenario a Fallo de disco de datos**: recuerda desactivar el sync programado YA.
- Disco nuevo distinto: tamaño en bytes y SMR (si va a paridad) comprobados.

## Paso 3: Preguntar y confirmar
`AskUserQuestion` para lo que no esté claro; confirma el resumen antes de editar.

## Paso 4: Versionado y edición
- **A — versión nueva** (DCP aprobado con cambio de fondo, o ejecutado Parcial/Abortado): nueva
  carpeta `outputs/dcp/v<N+1>`, se conserva el anterior.
- **B / C** como en el resto de entregables.
Solo Edit; Estado `En revisión`; fila en el historial con el motivo (cita el OPS).

## Paso 5: Validar y cerrar
`/storage-plugin:validate-dcp`; nota en `memory/dcp/session-AAAA-MM-DD.md`;
siguiente `/storage-plugin:approve-dcp`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-dcp", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/dcp/learnings-queue.jsonl
```

## Prevención de errores
1. Rehacer el plan desde el principio cuando la ejecución ya cambió la paridad o los montajes.
2. Quitar la precondición del sync programado porque "ya se hizo": se deja y se marca hecha.

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
