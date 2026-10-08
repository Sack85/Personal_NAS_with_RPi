---
name: validate-upd
description: >
  Valida un plan de actualización (UPD): secciones, metadatos, HLD aprobado, inventario de
  referencia, cambios con fuente, precondiciones de SnapRAID y backup, reglas por paso (como los
  runbooks), comprobación de discos y PCIe si cambia el kernel o el firmware, y vuelta atrás.
  También llamado: revisar el plan de actualización.
  Entrada: UPD en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar o revisar un plan de actualización
  - Saber si un UPD es seguro
  - Comprobar un UPD antes de aprobarlo
argument-hint: "[fichero UPD]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar un plan de actualización (UPD)

## Paso 1: Ejecutar el validador

```bash
uv run python maintainer-plugin/skills/validate-upd/scripts/validate_upd.py $ARGUMENTS
LATEST=$(ls -d outputs/upd/v* | sort -V | tail -1)
uv run python maintainer-plugin/skills/validate-upd/scripts/validate_upd.py --all "$LATEST"
```

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos; no cita `HLD vN (X.Y, Aprobado)`; sin `state/inventory/AAAA-MM-DD.yaml`.
- Sin cambios listados; sin precondiciones de SnapRAID y backup; sin vuelta atrás.
- **Kernel o firmware sin comprobar después `lsblk` y `LnkSta` 8GT/s.**
- Reglas por paso: comando destructivo en paso no Destructivo, destructivo por el agente, sin
  comprobación previa o sin Si falla; riesgo, ejecuta o dónde no válidos.
- Secretos.

### WARNING
- Cambio sin fuente; decisión no válida; riesgo máximo incoherente; paso sin Esperado;
  lenguaje vago.

## Paso 3: Corregir
- Nunca se quita una precondición ni una comprobación para que pase.
- Lo que requiera decisión se pregunta con `AskUserQuestion`.
- Revalida hasta 0 CRITICAL.

## Paso 4: Informe y nota
Checklist y `memory/upd/session-AAAA-MM-DD.md`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-upd", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/upd/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes
Si hay `pending` en `memory/upd/learnings-queue.jsonl`, `/maintainer-plugin:apply-learnings`.

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
