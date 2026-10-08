---
name: create-role-plugin
description: >
  Genera un plugin de rol completo para la cadena de entregables del NAS: skills
  create/update/validate/approve/apply-learnings, plantilla Jinja2, ejemplo, validador,
  evals, hooks, tests y su alta en registry.yaml, marketplace.json y CLAUDE.md.
  Derivada de create-role-plugin de RDEWAI (modificada).
  Úsala cuando el usuario pida crear, añadir o generar un plugin o rol nuevo
  (p. ej. "crea el plugin de runbooks", "añade un rol de seguridad").
argument-hint: "<rol> <abbr> \"<Nombre del entregable>\""
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, AskUserQuestion
---

# Crear un plugin de rol

## Paso 0: Argumentos y rama

De `$ARGUMENTS`: `{rol}` (minúsculas con guiones), `{abbr}` (minúsculas), `{nombre}`.
Deriva `{plugin}` = `{rol}-plugin`, `{ABBR}` = mayúsculas. Si falta alguno, pregúntalo con
`AskUserQuestion`.

Cada plugin se construye en su propia rama y con un commit al final de cada etapa:

```bash
git checkout main && git checkout -b plugin/{rol}
```

## Paso 1: Preguntas al usuario

Con `AskUserQuestion` (máx. 4 preguntas por ronda, cabeceras ≤ 12 caracteres):
1. Entregables previos que deben estar **Aprobados** (opciones: los de `registry.yaml`).
2. Secciones del entregable (propuesta derivada del dominio + "Las indico yo").
3. Si el rol actúa en el NAS por SSH (solo lectura / con cambios / no).
4. Skills extra además de las cinco estándar (p. ej. `inventory`, `diagnose-disk`).

## Paso 2: Leer el plugin canónico

Si ya existe `requirements-plugin/`, es la referencia: lee sus SKILL.md, plantilla,
validador, evals, hooks.json, README y `tests/test_validate_nrd.py`. Si no existe, sigue
solo las convenciones de abajo.

## Paso 3: Ficheros a generar

| Fichero | Contenido |
|---|---|
| `{plugin}/.claude-plugin/plugin.json` | name, version 0.1.0, description, author Sack85, keywords |
| `{plugin}/README.md` | skills, uso, entradas y salidas |
| `{plugin}/hooks/hooks.json` | ver abajo |
| `{plugin}/skills/create-{abbr}/SKILL.md` | `context: fork`; fases 0–5 (ver abajo) |
| `{plugin}/skills/create-{abbr}/{ABBR}_template.j2` | todas las secciones obligatorias del validador |
| `{plugin}/skills/create-{abbr}/examples/sample-{abbr}.md` | ejemplo completo que pasa el validador sin avisos |
| `{plugin}/skills/update-{abbr}/SKILL.md` | `context: fork`; reglas de versionado A/B/C |
| `{plugin}/skills/validate-{abbr}/SKILL.md` | sin fork; ejecuta el validador y corrige CRITICAL |
| `{plugin}/skills/validate-{abbr}/scripts/validate_{abbr}.py` | ver abajo |
| `{plugin}/skills/approve-{abbr}/SKILL.md` | Borrador/En revisión → Aprobado, solo con Edit |
| `{plugin}/skills/apply-learnings/SKILL.md` | copia la de requirements-plugin cambiando rutas |
| `{plugin}/skills/*/evals/eval-cases.yaml` | ≥ 3 casos por skill salvo approve y apply-learnings |
| `memory/{abbr}/learnings-queue.jsonl` | vacío |
| `outputs/{abbr}/v1/.gitkeep`, `inputs/{abbr}/v1/.gitkeep` | vacíos (inputs solo si el rol tiene entradas propias) |
| `tests/test_validate_{abbr}.py` | casos negativos específicos del validador |

### hooks.json

```json
{
  "description": "{ROL}: guard SSH, validación de {ABBR}, secretos y learnings",
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
      "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ssh_guard.py", "timeout": 10}]}],
    "PostToolUse": [{"matcher": "Write|Edit", "hooks": [
      {"type": "command", "timeout": 30, "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_output_hook.py {abbr} skills/validate-{abbr}/scripts/validate_{abbr}.py"},
      {"type": "command", "timeout": 10, "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/secrets_guard.py"},
      {"type": "command", "timeout": 10, "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check_learnings_queue.py {plugin} {abbr}"}
    ]}]
  }
}
```

Los scripts de `{plugin}/scripts/` y `doc_validation.py` **no se escriben a mano**: tras dar de
alta el plugin en `registry.yaml`, ejecuta `make sync`.

### Validador

```python
from doc_validation import (base_report, check_required_sections, check_upstream_reference,
                            common_checks, run_cli, ...)

REQUIRED_SECTIONS = [...]   # títulos sin numeración, en el orden del documento
CONTENT_SECTIONS = [...]

def validate(path: Path) -> ValidationReport:
    report, content, sections = base_report(path)
    report.results += check_required_sections(sections, REQUIRED_SECTIONS)
    report.results += common_checks(content, sections)   # metadatos, historial, secretos, vaguedad
    report.results += check_upstream_reference(content, "<abbr previo>")  # si tiene previo
    report.results += <checks propios del dominio>
    return report

if __name__ == "__main__":
    sys.exit(run_cli(validate, "Valida un {ABBR}"))
```

Salida: 0 ok, 1 CRITICAL, 2 WARNING, 3 error. Las reglas de seguridad del dominio (orden de
pasos, rollback, comandos destructivos marcados para el usuario) son CRITICAL.

### Convenciones de las skills

- Frontmatter: `name` = carpeta; `description` con sinónimos y "Úsala cuando …" (5+ frases);
  `allowed-tools`; `argument-hint`.
- Metadatos del entregable: `| **Documento** |`, `| **Versión** | N.M |`,
  `| **Estado** | Borrador / En revisión / Aprobado |`, `| **Última modificación** |`,
  `| **Autor** |`, `| **Entregable previo** | {ABBR previo} vN (X.Y, Aprobado) |`.
- Última sección del entregable: `## Historial de versiones` con tabla.
- Ruta: `outputs/{abbr}/vN/{ABBR}-AAAA-MM-DD-<corto>.md`; última versión con
  `ls -d outputs/{abbr}/v* | sort -V | tail -1`.
- create: Fase 0 *puerta de aprobación* del entregable previo (si no está Aprobado: parar y
  pedir `/<plugin-previo>:approve-<abbr>`, sin excepción) → Fase 1 leer entradas → Fase 2
  lista de huecos COMPLETO/PARCIAL/FALTA → Fase 3 preguntas con `AskUserQuestion` hasta
  cerrar huecos → Fase 4 escribir desde la plantilla → Fase 5 validar y aplicar learnings.
- Toda corrección del usuario se registra:
  `echo '{"skill":"…","date":"…","correction":"…","pattern":"Siempre/Nunca …","status":"pending"}' >> memory/{abbr}/learnings-queue.jsonl`
- Las skills invocan a otras con `/{plugin}:{skill}`; nunca leen ficheros de otro plugin.
- Al final del cuerpo:

```markdown
## Aprendizajes y correcciones

Meta-reglas para añadir aprendizajes: empiezan por "Siempre" o "Nunca", primero el problema
y luego la solución, con un comando o ejemplo concreto, una regla por viñeta, máximo 20.

### Aprendizajes activos

_Ninguno todavía._
```

## Paso 4: Registrar

1. `registry.yaml`: rol, entregables, prefijo y entregables previos. Se añade **en la primera
   etapa con `wip: true`** (así `make sync` copia los scripts y los tests de estructura lo
   ignoran mientras se construye); en la última etapa se quita `wip`.
2. `.claude-plugin/marketplace.json` (última etapa): `{"name": "{plugin}", "source": "./{plugin}", "description": "…"}`.
3. `.claude/settings.json` → `enabledPlugins`: `"{plugin}@nas2rbpi-plugins": true`.
4. `CLAUDE.md`: fila en la tabla de roles y sección del plugin.
5. `make sync`.

## Paso 5: Verificar y cerrar la rama

```bash
uv run pytest && uv run ruff check . && uv run ruff format --check . && make check-sync
```

Un commit por etapa (esqueleto → plantilla + ejemplo → validador + tests → skills → hooks +
evals → registro). Al terminar: `git checkout main && git merge --no-ff plugin/{rol}`.
Sin push salvo que el usuario lo pida.
