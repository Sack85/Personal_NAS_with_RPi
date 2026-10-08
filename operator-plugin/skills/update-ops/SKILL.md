---
name: update-ops
description: >
  Reanuda una ejecución interrumpida (OPS con Resultado En curso) desde el primer paso
  pendiente, o completa un OPS terminado con evidencias o incidencias que faltaban. Edita solo
  con Edit y nunca reescribe pasos ya registrados.
  También llamado: continuar la ejecución, reanudar el runbook, completar el registro.
  Entradas: OPS existente + su documento aprobado. Salida: OPS actualizado.
  Úsala cuando el usuario pida:
  - Continuar o reanudar una ejecución cortada
  - Seguir con el runbook donde se quedó
  - Añadir una evidencia o una incidencia a un OPS
  - Corregir un dato mal registrado en un OPS
argument-hint: "[fichero OPS]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Reanudar o completar un OPS

Eres el operador del NAS. Retomas una ejecución sin repetir pasos ya hechos y sin perder lo
registrado.

## Paso 1: Localizar

`$ARGUMENTS` o el OPS más reciente con Resultado `En curso`:

```bash
grep -l '| \*\*Resultado\*\* | En curso |' outputs/ops/v*/OPS-*.md
```

Lee el OPS y el documento que cita en `Entregable previo` (debe seguir Aprobado; si ya no es la
última versión aprobada, avisa y pregunta si se continúa con la versión citada).

## Paso 2: Reanudar (Resultado En curso)

1. Comprueba el estado real antes de seguir: los pasos con Resultado `Pendiente` pueden haberse
   hecho a medias. Para el primero pendiente, ejecuta su comprobación previa o una lectura que
   muestre si ya se aplicó (p. ej. `lsblk`, `findmnt`, `systemctl status`), y pregunta al
   usuario si llegó a ejecutarlo.
2. Continúa con el protocolo de create-ops (Fase 3 en adelante): mismas reglas de quién
   ejecuta, comparación con Esperado y parada ante diferencias.
3. Añade al historial: `| X.Y | hoy | Operator Agent | Reanudada en el paso N |`.

## Paso 3: Completar (Resultado ya cerrado)

- Solo se añaden evidencias, incidencias o seguimiento; nunca se cambia el resultado de un paso
  ya registrado salvo error de transcripción probado (explícalo en el historial).
- Si el OPS estaba Aprobado, pasa a `En revisión` y habrá que volver a aprobarlo.

## Paso 4: Validar y cerrar

1. `/operator-plugin:validate-ops`; corrige CRITICAL.
2. Nota en `memory/ops/session-AAAA-MM-DD.md`.
3. Siguiente: `/operator-plugin:approve-ops` cuando el Resultado sea definitivo.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-ops", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/ops/learnings-queue.jsonl
```

## Prevención de errores
1. **Repetir un paso destructivo** que ya se hizo: comprueba el estado real antes.
2. **Reescribir la historia**: lo registrado no se cambia; se añade.

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
