---
name: update-rbk
description: >
  Actualiza runbooks (RBK) del NAS: tras aprobar un HLD nuevo, cuando el operador encontró un
  error al ejecutar (incidencia en un OPS), cuando un comando cambió con una actualización o
  cuando el usuario corrige un paso. Versiona con las reglas A/B/C, edita solo con Edit y deja
  el RBK En revisión.
  También llamado: corregir un runbook, revisar procedimientos, adaptar pasos.
  Entradas: RBK existente + HLD aprobado + OPS con incidencias. Salida: RBK actualizado.
  Úsala cuando el usuario pida:
  - Actualizar, corregir o revisar un runbook
  - Adaptar los runbooks a un HLD nuevo
  - Arreglar un paso que falló al ejecutarlo
  - Cambiar un comando que ya no funciona tras una actualización
argument-hint: "<fichero-rbk|todas>"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Actualizar runbooks (RBK)

Eres el autor de runbooks. Corriges procedimientos sin perder la versión que se ejecutó.

## Paso 1: Leer y detectar el motivo

1. El RBK (`$ARGUMENTS`) o todos los de la última versión (`todas`).
2. HLD aprobado más reciente. Si es más nuevo que el que cita el RBK → motivo "HLD nuevo".
3. OPS con incidencias de esta fase: `grep -l "RBK <NN>" outputs/ops/v*/*.md`.
4. `memory/rbk/`.

## Paso 2: Puerta del origen

- HLD nuevo → debe estar Aprobado.
- Corrección por incidencia → la incidencia debe estar descrita en un OPS.
- Si no, para y explica qué falta.

## Paso 3: Impacto y preguntas

- **HLD nuevo**: revisa todos los runbooks; los que no cambian también deben citar la nueva
  versión del HLD tras revisarlos.
- **Incidencia**: corrige el paso, su Esperado y su Si falla; añade un paso de Lectura si el
  error vino de suponer algo del equipo.
- **Comando cambiado**: verifica el nuevo con la documentación o `--help` (puerta de comandos
  verificados de create-rbk) y cita la fuente.

Pregunta con `AskUserQuestion` lo que no esté claro y confirma el resumen antes de editar.

## Paso 4: Versionado

```bash
LATEST_DIR=$(ls -d outputs/rbk/v* | sort -V | tail -1)
CURRENT_V=$(basename "$LATEST_DIR")
TODAY=$(date +%Y-%m-%d)
```

- **A — HLD nuevo**: `mkdir outputs/rbk/v<N+1>` y copia **todos** los RBK con la fecha de hoy
  (`RBK-$TODAY-NN-<fase>.md`); los de `vN` se conservan (son los que se ejecutaron). Versión
  `<N+1>.0` y `Entregable previo` = HLD nuevo.
- **B — mismo vN, otro día**: copia el fichero con la fecha de hoy y renombra el anterior a
  `.bak`; versión menor +1.
- **C — mismo día**: edita en el sitio; versión menor +1.

## Paso 5: Editar

- Solo Edit; conserva lo que no cambia; nunca borres un paso sin aprobación (márcalo
  "Ya no aplica: motivo" si hace falta mantener la numeración).
- Metadatos: versión, Última modificación, Estado `En revisión`, Riesgo máximo recalculado.
- Historial de versiones: qué cambió y por qué (cita el OPS o el ADR).

## Paso 6: Validar y cerrar

1. `/runbook-plugin:validate-rbk` en cada fichero tocado.
2. Informa: ficheros, pasos cambiados, motivo; recuerda aprobarlos antes de ejecutarlos.
3. Nota en `memory/rbk/session-AAAA-MM-DD.md`; aprendizajes → `/runbook-plugin:apply-learnings`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-rbk", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/rbk/learnings-queue.jsonl
```

## Prevención de errores
1. **Pisar el runbook ejecutado**: en el escenario A se conserva `vN`.
2. **Arreglar el síntoma**: si un paso falló porque el disco tenía otra letra, el arreglo es un
   paso de identificación, no cambiar `sdb` por `sdc`.
3. **Bajar el riesgo de un paso** sin motivo escrito.

## Referencia: cuatro responsabilidades
Seguridad de los datos · Ejecutable · Trazable · Evidencias.

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
