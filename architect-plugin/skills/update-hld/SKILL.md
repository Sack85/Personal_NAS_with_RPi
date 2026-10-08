---
name: update-hld
description: >
  Actualiza el HLD del NAS cuando cambia algo del diseño: un disco nuevo o retirado, otro rol
  de paridad, una carpeta nueva, acceso exterior, un cambio tras una actualización, o un NRD
  nuevo aprobado. Versiona con las reglas A/B/C, edita solo con Edit, registra un ADR por cada
  decisión nueva y deja el HLD En revisión.
  También llamado: revisar la arquitectura, modificar el HLD, nuevo ADR.
  Entradas: HLD existente + cambio (o NRD nuevo, o DCP aprobado). Salida: HLD actualizado.
  Úsala cuando el usuario pida:
  - Actualizar, revisar o modificar el HLD
  - Reflejar en el diseño un cambio de disco (tras un DCP)
  - Añadir una decisión de arquitectura
  - Adaptar el diseño a un NRD nuevo
  - Cambiar puertos, servicios o la política de actualizaciones
argument-hint: "[ruta-del-hld]"
allowed-tools: Read, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch
context: fork
---

# Actualizar el Diseño de Alto Nivel (HLD)

Eres el arquitecto del NAS. Cambias el diseño sin perder la historia de por qué era como era.

## Paso 1: Leer

1. HLD a actualizar (`$ARGUMENTS` o el más reciente de `outputs/hld/v*`).
2. NRD aprobado más reciente: si es **más nuevo** que el citado en `Entregable previo`, el
   cambio es de escenario A (versión nueva del HLD).
3. Si el cambio viene de un disco: el DCP aprobado más reciente en `outputs/dcp/v*` (si existe).
4. `memory/hld/` y qué entregables citan este HLD (`grep -rl "HLD v" outputs/`).

## Paso 2: Puerta de aprobación del origen

- Si el cambio viene de un NRD nuevo, ese NRD debe estar **Aprobado**.
- Si viene de un cambio de disco, el DCP debe estar **Aprobado**.
- Si no, para e indica qué aprobar primero.

## Paso 3: Impacto y preguntas

Efectos en cadena:
- **Disco nuevo o retirado** → tabla de Almacenamiento (rol, tamaño, conexión, montaje, pool,
  content), regla paridad ≥ datos, MergerFS, hd-idle, SMART, bahías y aire, riesgos.
- **Nueva carpeta** → permisos, backup offline (¿cabe en el disco de backup?), Nextcloud.
- **Acceso exterior** → puertos, seguridad, ADR.
- **Cambio por actualización** (p. ej. nuevo overlay, cambio de OMV) → arranque, componentes,
  ADR con la fuente.

Pregunta con `AskUserQuestion` (mismo formato que create-hld) lo que no esté claro y confirma
el resumen de cambios antes de editar.

## Paso 4: Versionado y edición

```bash
LATEST_DIR=$(ls -d outputs/hld/v* | sort -V | tail -1)
CURRENT_V=$(basename "$LATEST_DIR")
EXISTING=$(ls -t "$LATEST_DIR"/HLD-*.md | grep -v '\.bak$' | head -1)
TODAY=$(date +%Y-%m-%d)
SHORT=$(basename "$EXISTING" .md | sed -E 's/^HLD-[0-9]{4}-[0-9]{2}-[0-9]{2}-//')
```

- **A — versión nueva** (NRD nuevo, HLD aprobado con cambio de fondo como un disco nuevo, o lo
  pide el usuario): `mkdir outputs/hld/v<N+1>` y copia con la fecha de hoy. El aprobado anterior
  **se conserva**. Versión `<N+1>.0`.
- **B — misma versión, otro día**: copia con la fecha de hoy y renombra la anterior a `.bak`;
  versión menor +1.
- **C — mismo día**: edita en el sitio; versión menor +1.

Reglas de edición:
- Solo Edit, nunca Write; conserva todo lo que no cambia.
- Cada decisión nueva = fila ADR nueva (`ADR-00N`) con alternativas y requisito; una decisión
  que sustituye a otra lo dice ("Sustituye a ADR-003").
- Actualiza `Entregable previo` si cambia el NRD.
- Metadatos: versión, Última modificación = hoy, Estado = `En revisión`.
- Fila en Historial de versiones con el cambio.

## Paso 5: Validar y cerrar

1. `/architect-plugin:validate-hld`; corrige CRITICAL (p. ej. paridad menor tras añadir un disco
   grande: el disco grande debe pasar a paridad).
2. Informa: cambios, ADR nuevos, y qué runbooks (`outputs/rbk/`) hay que actualizar.
3. Nota en `memory/hld/session-AAAA-MM-DD.md`; aprendizajes pendientes →
   `/architect-plugin:apply-learnings`.
4. Siguiente: `/architect-plugin:approve-hld`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "update-hld", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/hld/learnings-queue.jsonl
```

## Prevención de errores
1. **Pisar el HLD aprobado** que citan los runbooks: escenario A lo conserva.
2. **Cambiar sin ADR**: toda decisión nueva deja rastro.
3. **Olvidar el efecto en cadena** de un disco: tabla de almacenamiento, hd-idle, SMART, backup.

## Referencia: cuatro responsabilidades
Integridad de datos · Superficie mínima · Actualizable sin sustos · Trazable.

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
