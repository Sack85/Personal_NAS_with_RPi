---
name: validate-ops
description: >
  Valida un registro de ejecución (OPS): que ejecuta un RBK/UPD/DCP aprobado, que ningún paso
  destructivo figura hecho por el agente, que el resultado global es coherente con los pasos,
  que los fallos tienen incidencia, que hay verificación final y que no hay secretos en las
  evidencias.
  También llamado: revisar el registro, auditar una ejecución.
  Entrada: OPS en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar o revisar un OPS o una ejecución
  - Comprobar que una ejecución quedó bien registrada
  - Revisar los OPS antes de cerrarlos
argument-hint: "[fichero OPS]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar un registro de ejecución (OPS)

## Paso 1: Ejecutar el validador

```bash
uv run python operator-plugin/skills/validate-ops/scripts/validate_ops.py $ARGUMENTS
LATEST=$(ls -d outputs/ops/v* | sort -V | tail -1)
uv run python operator-plugin/skills/validate-ops/scripts/validate_ops.py --all "$LATEST"
```

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos que faltan; Resultado no válido.
- No cita `RBK|UPD|DCP vN (X.Y, Aprobado)`.
- Paso con resultado o ejecutor no válidos.
- **Paso destructivo registrado como ejecutado por el agente.**
- Resultado `Completado` con pasos en Fallo o Pendiente, o sin verificación final, o con
  verificación final no superada.
- Pasos en Fallo, o Resultado Parcial/Abortado, sin incidencia.
- Datos sensibles en evidencias.

### WARNING
- Paso OK sin evidencia; ejecución terminada sin hora de fin; secciones vacías.

### INFO
- Ejecución en curso (se reanuda con update-ops).

## Paso 3: Corregir

- Un paso destructivo registrado como del agente **no se "arregla" cambiando el nombre**: pregunta
  al usuario quién lo ejecutó realmente. Si lo ejecutó el agente, es una incidencia grave:
  regístrala y revisa el guard (`shared/hooks/ssh_guard.py`).
- Coherencia del resultado: ajusta el Resultado global a la realidad (Parcial/Abortado) y añade
  la incidencia, preguntando lo que no sepas.
- Secretos: recorta la evidencia.

## Paso 4: Informe y nota

Checklist de hallazgos y nota en `memory/ops/session-AAAA-MM-DD.md`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-ops", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/ops/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes

Si hay `pending` en `memory/ops/learnings-queue.jsonl`, invoca `/operator-plugin:apply-learnings`.

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
