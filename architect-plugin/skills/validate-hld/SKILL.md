---
name: validate-hld
description: >
  Valida el HLD del NAS: secciones, metadatos, cita del NRD aprobado y reglas de seguridad del
  diseño (paridad ≥ mayor disco de datos y fuera del pool, content suficientes, paneles no
  expuestos, overlay PCIe del HAT), trazabilidad, ADR, protección con backup real, secretos y
  lenguaje vago. Corrige los CRITICAL antes de presentar.
  También llamado: revisar la arquitectura, auditar el HLD, control de calidad del diseño.
  Entrada: HLD en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar, comprobar, revisar o auditar el HLD
  - Saber si el diseño es seguro o está listo para aprobar
  - Comprobar si un cambio de discos rompe la paridad
  - Revisar el HLD antes de los runbooks
argument-hint: "[ruta-del-hld]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar el Diseño de Alto Nivel (HLD)

Eres el arquitecto del NAS. Compruebas que el diseño es completo y, sobre todo, seguro.

## Paso 1: Ejecutar el validador

```bash
uv run python architect-plugin/skills/validate-hld/scripts/validate_hld.py $ARGUMENTS
# o la última versión:
LATEST=$(ls -d outputs/hld/v* | sort -V | tail -1)
uv run python architect-plugin/skills/validate-hld/scripts/validate_hld.py --all "$LATEST"
```

Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 fichero no encontrado.

## Paso 2: Interpretar

### CRITICAL
- Secciones o metadatos que faltan; no cita `NRD vN (X.Y, Aprobado)`.
- Sin trazabilidad NRD → HLD; sin tabla de puertos; sin tabla de discos.
- Sin paridad o sin discos de datos; tamaños ilegibles.
- **Paridad menor que el mayor disco de datos.**
- **Paridad dentro del pool de MergerFS.**
- **Content files < paridades + 1.**
- **SSH (22), OMV (8000) o AIO (8080) expuestos a Internet.**
- **HAT Penta/JMB585 sin `dtparam=pciex1` o sin `dtoverlay=pcie-32bit-dma-pi5`.**
- Ningún escenario cubierto con un backup (SnapRAID no lo es).
- Sin ADR; datos sensibles en claro.

### WARNING
- Disco de datos fuera del pool o con sistema de ficheros distinto de ext4/xfs.
- SnapRAID sin umbral de borrados; MergerFS sin espacio libre mínimo.
- Requisitos sin `§`; ADR sin requisito o sin alternativas.
- Sin tabla de componentes a comprobar tras actualizar; sin riesgos.
- Lenguaje vago.

### INFO
- Marcadores `[PENDIENTE]` sin responsable ni fecha.

## Paso 3: Corregir los CRITICAL antes de presentar

- Las reglas de seguridad **no se corrigen en silencio**: explica el problema y pregunta con
  `AskUserQuestion` la solución (p. ej. "la paridad de 500 GB es menor que D2 de 1 TB: ¿pasar
  D2 a paridad o sustituir la paridad?"). Registra la decisión como ADR.
- Estructura que falta: añádela con `[PENDIENTE: … — responsable: X, fecha: AAAA-MM-DD]`.
- Secretos: sustitúyelos y avisa de que pueden estar en el historial de git.
- Revalida hasta 0 CRITICAL.

## Paso 4: Informe

Checklist con CRITICAL corregidos, WARNING pendientes e INFO; pregunta qué WARNING arreglar.

## Paso 5: Nota de sesión

`memory/hld/session-AAAA-MM-DD.md`: fichero, recuentos antes/después, arreglos, decisiones.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-hld", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/hld/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes

Si `memory/hld/learnings-queue.jsonl` tiene `pending`, invoca `/architect-plugin:apply-learnings`.

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
