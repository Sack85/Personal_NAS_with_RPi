---
name: update-nrd
description: >
  Actualiza un Documento de Requisitos del NAS (NRD) existente con información nueva:
  mediciones de datos, nuevos usuarios o dispositivos, cambios de servicios, de presupuesto,
  de entorno o respuestas a preguntas abiertas. Conserva lo que no cambia, versiona según las
  reglas A/B/C, edita solo con Edit y deja el NRD En revisión.
  También llamado: revisar requisitos, modificar el NRD, enmienda de requisitos.
  Entradas: NRD existente + cambios del usuario o nuevas entradas. Salida: NRD actualizado.
  Úsala cuando el usuario pida:
  - Actualizar, revisar, modificar o cambiar el NRD
  - Añadir un usuario, un dispositivo, una carpeta o un servicio
  - Corregir volúmenes con una medición nueva
  - Cerrar preguntas abiertas del NRD
  - Reflejar un cambio de planes (otro disco, otro presupuesto, acceso exterior)
argument-hint: "[ruta-del-nrd]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Actualizar el Documento de Requisitos del NAS (NRD)

Eres el analista de requisitos del NAS familiar. Aplicas cambios al NRD sin perder lo que ya
estaba bien y sin romper la trazabilidad con los entregables que dependen de él (HLD y
siguientes).

---

## Protocolo de elicitación (modo actualización)

### Paso 1: Leer

1. NRD a actualizar: `$ARGUMENTS` o el más reciente:
   ```bash
   LATEST_DIR=$(ls -d outputs/nrd/v* | sort -V | tail -1)
   ls -t "$LATEST_DIR"/NRD-*.md | grep -v '\.bak$' | head -1
   ```
2. Entradas más recientes: `ls -d inputs/nrd/v* | sort -V | tail -1`.
3. Notas de `memory/nrd/`.
4. Si el NRD está **Aprobado**, mira qué entregables lo citan (`grep -rl "NRD v" outputs/`):
   habrá que revisarlos después.

### Paso 2: Impacto por sección

Si el cambio no está claro, pregunta con `AskUserQuestion` (mismo formato que create-nrd:
header ≤ 12 caracteres, 1–4 preguntas, 2–4 opciones, sin opción "Otro").

Efectos en cadena que debes revisar:
- **Nueva carpeta o más datos** → capacidad a 3 años, criticidad, escenarios de protección,
  backup offline (¿cabe en el disco de backup?).
- **Nuevo usuario o dispositivo** → servicios, acceso exterior, seguridad.
- **Acceso desde fuera** → seguridad (qué se expone y cómo), servicios (Tailscale).
- **Cambio de disco o hardware** → hardware disponible, capacidad, supuestos.
- **Cambio de clima o ubicación** → entorno, operación (limpieza de filtro, temperaturas).

### Paso 3–4: Preguntar e iterar

Pregunta por las secciones afectadas que el usuario no ha mencionado. Repite hasta que no haya
huecos ni contradicciones con el NRD actual.

### Paso 5: Confirmar

Resume los cambios por sección y confirma con `AskUserQuestion` antes de editar.

### Peticiones vagas que no se aceptan

| Petición vaga | Repregunta |
|---|---|
| "Pon más espacio" | "¿Qué carpeta crece y cuántos GB medidos?" |
| "Añade lo de fuera" | "¿Tailscale o publicar 443? ¿Qué usuarios?" |
| "Cambia el disco" | "¿Qué disco sale, cuál entra, tamaño y estado SMART?" |
| "Arregla la protección" | "¿Qué escenario y qué RPO/RTO nuevos?" |

---

## Flujo

### Fase 1: Puerta de medición (si cambian volúmenes)
Las cifras nuevas de carpetas irreemplazables deben estar medidas (ver create-nrd, Fase 3).

### Fase 2: Copiar y editar

```bash
LATEST_INPUT_V=$(ls -d inputs/nrd/v* | sort -V | tail -1 | grep -o 'v[0-9]*')
LATEST_DIR=$(ls -d outputs/nrd/v* | sort -V | tail -1)
CURRENT_V=$(basename "$LATEST_DIR")
EXISTING=$(ls -t "$LATEST_DIR"/NRD-*.md | grep -v '\.bak$' | head -1)
FILE_DATE=$(basename "$EXISTING" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')
TODAY=$(date +%Y-%m-%d)
SHORT=$(basename "$EXISTING" .md | sed -E 's/^NRD-[0-9]{4}-[0-9]{2}-[0-9]{2}-//')
```

1. **Escenario A — nueva versión** (entradas `vN` más nuevas que la salida, o el usuario pide
   versión nueva, o el NRD estaba Aprobado y el cambio es de fondo):
   ```bash
   NEW_V="v$((${CURRENT_V#v} + 1))"
   mkdir -p "outputs/nrd/$NEW_V"
   cp "$EXISTING" "outputs/nrd/$NEW_V/NRD-${TODAY}-${SHORT}.md"
   ```
   El fichero anterior **se conserva** (es la versión aprobada que citan otros entregables).
   Versión `${NEW_V#v}.0`.
2. **Escenario B — misma versión, otro día**:
   ```bash
   cp "$EXISTING" "$LATEST_DIR/NRD-${TODAY}-${SHORT}.md" && mv "$EXISTING" "$EXISTING.bak"
   ```
   Sube la versión menor (1.1 → 1.2).
3. **Escenario C — misma versión, mismo día**: edita en el sitio y sube la versión menor.

Los `.bak` no se versionan (`.gitignore`); el historial queda en git.

### Fase 3: Editar solo con Edit

- **Nunca** uses Write sobre el NRD: cada cambio con Edit y 3–5 líneas de contexto.
- Conserva todo lo que no cambia; no borres nada sin aprobación explícita.
- Si lo nuevo contradice lo existente, enseña ambas versiones y pregunta cuál vale.
- Cierra los `[PENDIENTE: …]` que las respuestas resuelven.
- Metadatos: versión según el escenario, **Última modificación** = hoy,
  **Estado** = `En revisión`.
- Añade una fila al Historial de versiones: `| versión | hoy | Requirements Agent | qué cambió |`.

### Fase 4: Consistencia
Revisa las cuatro responsabilidades (datos, protección, usuarios/servicios, entorno/seguridad)
tras los cambios; si alguna queda incompleta, pregunta.

### Fase 5: Validar, registrar y aplicar aprendizajes

1. `/requirements-plugin:validate-nrd` sobre el fichero; corrige CRITICAL.
2. Informa: lista de cambios, contradicciones resueltas, pendientes, resultado de validación y,
   si el NRD estaba aprobado, qué entregables posteriores habrá que actualizar.
3. Nota de sesión en `memory/nrd/session-AAAA-MM-DD.md`.
4. Si hay aprendizajes pendientes, `/requirements-plugin:apply-learnings`.
5. Siguiente paso: `/requirements-plugin:approve-nrd`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-nrd", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/nrd/learnings-queue.jsonl
```

---

## Prevención de errores
1. **Pisar la versión aprobada**: en el escenario A nunca se renombra a `.bak` el NRD aprobado.
2. **Cambios sin efecto en cadena**: un cambio de datos sin revisar capacidad y backup deja el
   diseño mal dimensionado.
3. **Añadir de más**: cada cambio se traza a una petición del usuario.

## Referencia: cuatro responsabilidades
Datos y capacidad medidos · Protección con RPO/RTO · Usuarios y servicios trazados ·
Entorno, seguridad y mantenimiento con números.

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
