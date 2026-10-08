---
name: approve-hld
description: >
  Aprueba el Diseño de Alto Nivel (HLD) del NAS: comprueba que no tiene errores CRITICAL y que
  el NRD que cita sigue aprobado, cambia el Estado a Aprobado, añade la fila al historial y
  propone el commit. Es la puerta que permite crear los runbooks.
  También llamado: dar el visto bueno a la arquitectura, cerrar el diseño.
  Úsala cuando el usuario pida:
  - Aprobar el HLD o la arquitectura
  - Dar por bueno el diseño del NAS
  - Marcar el HLD como listo para los runbooks
argument-hint: "[ruta-del-hld]"
allowed-tools: Read, Edit, Glob, Bash, AskUserQuestion
context: fork
---

# Aprobar el Diseño de Alto Nivel (HLD)

Eres el arquitecto del NAS. Apruebas formalmente el HLD para que se puedan escribir los
runbooks sobre él.

## Paso 1: Localizar

Si `$ARGUMENTS` trae una ruta, úsala. Si no:

```bash
LATEST_DIR=$(ls -d outputs/hld/v* | sort -V | tail -1)
LATEST_FILE=$(ls -t "$LATEST_DIR"/HLD-*.md 2>/dev/null | grep -v '\.bak$' | head -1)
echo "$LATEST_FILE"
```

Lee el fichero y la tabla de metadatos (Estado y Versión).

## Paso 2: Comprobaciones

1. **Ya aprobado**: informa ("HLD ya aprobado, versión X.Y") y para. Sin cambios.
2. **NRD citado**: el `Entregable previo` debe seguir siendo la última versión Aprobada del
   NRD. Si hay un NRD aprobado más nuevo, no se aprueba: propone `/architect-plugin:update-hld`.
3. **Validación (puerta)**:
   ```bash
   uv run python architect-plugin/skills/validate-hld/scripts/validate_hld.py "$LATEST_FILE"
   ```
   - Salida 1 (CRITICAL): **no se aprueba**. Indica qué falla y propone
     `/architect-plugin:validate-hld`. Para.
   - Salida 2 (WARNING): enseña los avisos y pregunta con `AskUserQuestion` si se aprueba igual
     ("Aprobar igual" / "Corregir antes").
4. **Borrador sin revisión**: si el Estado es `Borrador`, avisa de que nunca pasó por una
   revisión y confirma con `AskUserQuestion`.
5. **Pendientes**: si hay `[PENDIENTE` o el riesgo "Tamaños sin verificar con lsblk",
   enuméralos en la pregunta de confirmación para que el usuario apruebe sabiéndolo.

## Paso 3: Aprobar (solo con Edit, nunca Write)

1. `| **Estado** | <actual> |` → `| **Estado** | Aprobado |`
2. `| **Última modificación** | <fecha> |` → hoy
3. Añade al Historial de versiones:
   `| <versión actual> | <hoy> | Architect Agent | Estado cambiado a Aprobado |`

Vuelve a validar para confirmar que sigue sin CRITICAL.

## Paso 4: Traza en git

Pregunta con `AskUserQuestion` si se hace commit del HLD aprobado ("Sí, commit" / "No, lo hago
yo"). Si sí:

```bash
git add "$LATEST_FILE" memory/hld/
git commit -m "Aprueba HLD <vN> <versión>: <corto>"
```

Nunca hagas push.

## Paso 5: Confirmar y registrar

- Informa: fichero, versión y que ya se puede ejecutar `/runbook-plugin:create-rbk`.
- Nota en `memory/hld/session-AAAA-MM-DD.md`: acción, fichero, versión, estado anterior y nuevo,
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
