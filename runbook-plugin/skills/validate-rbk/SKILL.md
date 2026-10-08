---
name: validate-rbk
description: >
  Valida runbooks (RBK) del NAS: secciones, metadatos, cita del HLD aprobado, fase, y por cada
  paso riesgo, quién ejecuta, dónde, esperado y si falla; detecta comandos destructivos (con la
  misma lista que el guard SSH) en pasos no marcados como Destructivo o asignados al agente.
  Corrige los CRITICAL antes de presentar.
  También llamado: revisar un runbook, auditar procedimientos.
  Entrada: RBK en Markdown o carpeta. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar, comprobar o revisar un runbook
  - Saber si un runbook es seguro de ejecutar
  - Revisar todos los runbooks de una versión
  - Comprobar un runbook antes de aprobarlo
argument-hint: "<fichero-rbk|carpeta>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar runbooks (RBK)

Eres el autor de runbooks. Compruebas que un runbook se puede ejecutar sin poner en peligro
los datos.

## Paso 1: Ejecutar el validador

```bash
uv run python runbook-plugin/skills/validate-rbk/scripts/validate_rbk.py $ARGUMENTS
# todos los de la última versión:
LATEST=$(ls -d outputs/rbk/v* | sort -V | tail -1)
uv run python runbook-plugin/skills/validate-rbk/scripts/validate_rbk.py --all "$LATEST"
```

Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 fichero no encontrado.

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos que faltan; sin `Fase`; no cita `HLD vN (X.Y, Aprobado)`.
- Sin pasos; sin tabla de verificación final.
- Paso con Riesgo, Ejecuta o Dónde no válidos.
- **Comando destructivo en un paso que no es Destructivo.**
- **Paso destructivo ejecutado por el agente.**
- **Paso destructivo sin comprobación previa o sin "Si falla".**
- Datos sensibles en claro.

### WARNING
- Numeración de pasos; Riesgo máximo que no coincide con el peor paso.
- Paso de Cambio sin "Si falla"; paso sin "Esperado"; secciones vacías; lenguaje vago.

### INFO
- Marcadores `[PENDIENTE]` sin responsable ni fecha.

## Paso 3: Corregir los CRITICAL

- **Nunca bajes el riesgo** para que pase: si un comando es destructivo, el paso pasa a
  Destructivo, Ejecuta Usuario, con comprobación previa (modelo y serie) y Si falla.
- Lo que requiera decidir (cómo deshacer un paso) se pregunta con `AskUserQuestion`.
- Revalida hasta 0 CRITICAL.

## Paso 4: Informe

Checklist por fichero; pregunta qué WARNING corregir.

## Paso 5: Nota de sesión

`memory/rbk/session-AAAA-MM-DD.md`: ficheros, recuentos antes/después, arreglos.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-rbk", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/rbk/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes

Si hay `pending` en `memory/rbk/learnings-queue.jsonl`, invoca `/runbook-plugin:apply-learnings`.

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
