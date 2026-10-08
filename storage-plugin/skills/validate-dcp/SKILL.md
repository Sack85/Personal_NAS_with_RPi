---
name: validate-dcp
description: >
  Valida un plan de cambio de discos (DCP): escenario, disposición final de discos (paridad ≥
  mayor dato, paridad fuera del pool, content suficientes), backup y sync programado
  desactivado en precondiciones, orden fix → check → sync en un fallo de datos, sync en un fallo
  de paridad, reglas por paso de los runbooks, verificación y cambios en el diseño.
  También llamado: revisar el plan de discos, comprobar un DCP.
  Entrada: DCP en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar o revisar un plan de cambio de discos
  - Saber si un DCP es seguro antes de ejecutarlo
argument-hint: "[fichero DCP]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar un plan de cambio de discos (DCP)

## Paso 1: Ejecutar el validador

```bash
uv run python storage-plugin/skills/validate-dcp/scripts/validate_dcp.py $ARGUMENTS
LATEST=$(ls -d outputs/dcp/v* | sort -V | tail -1)
uv run python storage-plugin/skills/validate-dcp/scripts/validate_dcp.py --all "$LATEST"
```

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos; escenario no válido; sin disco afectado; HLD no aprobado.
- **Situación final que incumple SnapRAID** (paridad menor que un dato —p. ej. disco mayor que
  la paridad puesto como dato—, paridad en el pool, content insuficientes).
- **Precondiciones sin backup o sin desactivar el sync programado.**
- **Fallo de datos sin `-d dN fix` o con un `sync` antes del `fix`.**
- **Fallo de paridad sin `sync`.**
- Reglas por paso (destructivo = usuario con comprobación previa y Si falla).
- Secretos.

### WARNING
- Sin `check` tras el `fix` o sin sync final; sin inventario; verificación sin SnapRAID; no se
  menciona HLD, SnapRAID, MergerFS, hd-idle o SMART en Cambios en el diseño; riesgo máximo
  incoherente; lenguaje vago.

## Paso 3: Corregir
Las reglas de orden y de disposición no se "arreglan" quitando pasos: se reordena, se cambia el
rol del disco grande a paridad o se añade el paso que falta, preguntando al usuario lo que
implique decidir. Revalida hasta 0 CRITICAL.

## Paso 4: Informe y nota
Checklist y `memory/dcp/session-AAAA-MM-DD.md`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-dcp", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/dcp/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes
Si hay `pending` en `memory/dcp/learnings-queue.jsonl`, `/storage-plugin:apply-learnings`.

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
