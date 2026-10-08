---
name: apply-learnings
description: >
  Revisa las correcciones pendientes de memory/rbk/learnings-queue.jsonl y las convierte en
  reglas generales dentro de la sección "Aprendizajes activos" de la skill correspondiente,
  con el patrón Reflexionar-Abstraer-Generalizar-Escribir. Derivada de RDEWAI.
  Úsala cuando el usuario pida:
  - Aplicar aprendizajes o correcciones de los runbooks
  - Revisar la cola de aprendizajes
  - Mejorar las skills de runbooks con lo aprendido
  - "¿Qué correcciones se han acumulado?"
argument-hint: ""
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion
---

# Aplicar aprendizajes (runbook-plugin)

## Paso 1: Leer la cola

```bash
cat memory/rbk/learnings-queue.jsonl
```

Sin entradas `"status": "pending"` → "No hay aprendizajes pendientes" y fin.

## Paso 2: Agrupar por skill

```
Pendientes:
- create-rbk: 3
- validate-rbk: 1
```

## Paso 3: Procesar cada corrección

1. **Reflexionar**: cita la corrección original del usuario.
2. **Abstraer**: ¿vale para cualquier runbook o solo para este caso? ¿Es estilo o corrección?
   ¿Choca con un aprendizaje existente?
3. **Generalizar**: directiva que empieza por "Siempre" o "Nunca", primero el problema y luego
   la solución, con un comando o ejemplo, una regla por viñeta.
4. **Confirmar** con `AskUserQuestion`:
   ```
   Aprendizaje propuesto para create-rbk:
   - **L-003** (2026-10-20): Siempre añade `--no-pager` a `systemctl status` en los pasos por SSH;
     sin él la salida se corta.
   ```
   Opciones: "Aplicar" / "Descartar" / "Editar".

## Paso 4: Escribir los aprobados

1. Abre `runbook-plugin/skills/<skill>/SKILL.md`.
2. Busca `### Aprendizajes activos`.
3. Siguiente ID: cuenta los `L-0NN` existentes.
4. Añade la viñeta (o sustituye `_Ninguno todavía…_` si es el primero) con Edit.
5. Máximo 20: si se supera, fusiona los relacionados y díselo al usuario.

## Paso 5: Actualizar la cola

Con Edit, en `memory/rbk/learnings-queue.jsonl`: `"status": "pending"` → `"applied"` o
`"rejected"` en cada entrada procesada.

## Paso 6: Informe

Aplicados por skill, descartados y conflictos resueltos. El hook de fin de sesión copiará los
pendientes que queden a CLAUDE.md.
