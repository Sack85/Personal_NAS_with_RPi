---
name: approve-nrd
description: >
  Aprueba el Documento de Requisitos del NAS (NRD): comprueba que no tiene errores CRITICAL,
  cambia el Estado a Aprobado, añade la fila al historial y propone el commit. Es la puerta
  que permite crear el HLD.
  También llamado: dar el visto bueno al NRD, cerrar requisitos, firmar requisitos.
  Úsala cuando el usuario pida:
  - Aprobar el NRD o los requisitos
  - Dar por buenos los requisitos
  - Marcar el NRD como listo para el arquitecto
argument-hint: "[ruta-del-nrd]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar el Documento de Requisitos del NAS (NRD)

Eres el analista de requisitos. Apruebas formalmente el NRD para que el arquitecto pueda
diseñar sobre él.

## Paso 1: Localizar

Si `$ARGUMENTS` trae una ruta, úsala. Si no:

```bash
LATEST_DIR=$(ls -d outputs/nrd/v* | sort -V | tail -1)
LATEST_FILE=$(ls -t "$LATEST_DIR"/NRD-*.md 2>/dev/null | grep -v '\.bak$' | head -1)
echo "$LATEST_FILE"
```

Lee el fichero y la tabla de metadatos (Estado y Versión).

## Paso 2: Comprobaciones

1. **Ya aprobado**: informa ("NRD ya aprobado, versión X.Y") y para. Sin cambios.
2. **Validación (puerta)**:
   ```bash
   uv run python requirements-plugin/skills/validate-nrd/scripts/validate_nrd.py "$LATEST_FILE"
   ```
   - Salida 1 (CRITICAL): **no se aprueba**. Indica qué falla y propone
     `/requirements-plugin:validate-nrd`. Para.
   - Salida 2 (WARNING): enseña los avisos y pregunta con `AskUserQuestion` si se aprueba igual
     ("Aprobar igual" / "Corregir antes").
3. **Borrador sin revisión**: si el Estado es `Borrador`, avisa de que nunca pasó por una
   revisión y confirma con `AskUserQuestion`.
4. **Pendientes**: si hay `[PENDIENTE` o volúmenes `Estimado` en carpetas irreemplazables,
   enuméralos en la pregunta de confirmación para que el usuario apruebe sabiéndolo.

## Paso 3: Aprobar (solo con Edit, nunca Write)

1. `| **Estado** | <actual> |` → `| **Estado** | Aprobado |`
2. `| **Última modificación** | <fecha> |` → hoy
3. Añade al Historial de versiones:
   `| <versión actual> | <hoy> | Requirements Agent | Estado cambiado a Aprobado |`

Vuelve a validar para confirmar que sigue sin CRITICAL.

## Paso 4: Traza en git

Pregunta con `AskUserQuestion` si se hace commit del NRD aprobado ("Sí, commit" / "No, lo hago
yo"). Si sí:

```bash
git add "$LATEST_FILE" memory/nrd/
git commit -m "Aprueba NRD <vN> <versión>: <corto>"
```

Nunca hagas push.

## Paso 5: Confirmar y registrar

- Informa: fichero, versión y que ya se puede ejecutar `/architect-plugin:create-hld`.
- Nota en `memory/nrd/session-AAAA-MM-DD.md`: acción, fichero, versión, estado anterior y nuevo,
  avisos aceptados.

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
