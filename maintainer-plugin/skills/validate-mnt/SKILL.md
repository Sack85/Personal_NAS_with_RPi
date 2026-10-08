---
name: validate-mnt
description: >
  Valida un informe de mantenimiento (MNT): periodo, semáforo e inventario; tareas del periodo
  según la guía §13.3; que un semáforo Verde no oculte fallos; que todo disco que se degrada
  tenga acción hacia el experto en discos; temperaturas; acciones con responsable y fecha.
  También llamado: revisar el informe de mantenimiento.
  Entrada: MNT en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar o revisar un informe de mantenimiento
  - Comprobar que la revisión mensual está completa
argument-hint: "[fichero MNT]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar un informe de mantenimiento (MNT)

## Paso 1: Ejecutar el validador

```bash
uv run python maintainer-plugin/skills/validate-mnt/scripts/validate_mnt.py $ARGUMENTS
LATEST=$(ls -d outputs/mnt/v* | sort -V | tail -1)
uv run python maintainer-plugin/skills/validate-mnt/scripts/validate_mnt.py --all "$LATEST"
```

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos; periodo, semáforo o inventario no válidos; HLD no aprobado.
- Sin checklist o con resultados no válidos; semáforo Verde con tareas en Fallo.
- **Disco con atributos 5/197/198 distintos de 0 o que crecen sin acción hacia
  `/storage-plugin:diagnose-disk`.**
- Disco por encima de 45 °C sin ninguna acción.

### WARNING
- Falta una tarea del periodo; disco por encima de 40 °C sin acción de aire/filtro; acciones sin
  responsable o fecha; lenguaje vago.

## Paso 3: Corregir
Añade la acción que falta (con skill, responsable y fecha) preguntando al usuario lo necesario;
nunca bajes el semáforo ni quites un Fallo para que pase. Revalida.

## Paso 4: Informe y nota
Checklist y `memory/mnt/session-AAAA-MM-DD.md`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-mnt", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/mnt/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes
Si hay `pending` en `memory/mnt/learnings-queue.jsonl`, `/maintainer-plugin:apply-learnings`.

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
