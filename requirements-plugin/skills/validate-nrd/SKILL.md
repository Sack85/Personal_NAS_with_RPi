---
name: validate-nrd
description: >
  Valida un Documento de Requisitos del NAS (NRD): secciones obligatorias, metadatos,
  inventario de datos con criticidad y volúmenes medidos, escenarios de fallo con RPO/RTO,
  clima, reglas de exposición, secretos en claro y lenguaje vago. Informa por gravedad
  (CRITICAL, WARNING, INFO) y corrige los CRITICAL antes de presentar.
  También llamado: revisar el NRD, auditar requisitos, control de calidad del NRD.
  Entrada: NRD en Markdown. Salida: informe de validación.
  Úsala cuando el usuario pida:
  - Validar, comprobar, revisar o auditar el NRD
  - Saber si el NRD está listo para aprobar
  - Buscar huecos o errores en los requisitos
  - Pasar el control de calidad antes del HLD
argument-hint: "[ruta-del-nrd]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
---

# Validar el Documento de Requisitos del NAS (NRD)

Eres el analista de requisitos del NAS familiar. Compruebas que el NRD está completo y es
preciso antes de que el arquitecto diseñe sobre él.

## Paso 1: Ejecutar el validador

```bash
# Un fichero
uv run python requirements-plugin/skills/validate-nrd/scripts/validate_nrd.py $ARGUMENTS

# La última versión
LATEST=$(ls -d outputs/nrd/v* | sort -V | tail -1)
uv run python requirements-plugin/skills/validate-nrd/scripts/validate_nrd.py --all "$LATEST"
```

Salida: 0 ok, 1 CRITICAL, 2 solo WARNING, 3 fichero no encontrado.

## Paso 2: Interpretar

### CRITICAL (bloquea la aprobación y el HLD)
- Falta alguna sección obligatoria o el historial de versiones está vacío.
- Metadatos incompletos o estado/versión no válidos.
- Sin usuarios, sin servicios, sin inventario de datos, criticidad no válida.
- Sin tabla de escenarios con RPO y RTO.
- Datos sensibles en claro: contraseña, frase de acceso, token, clave privada, IP pública.

### WARNING
- Objetivos sin medida numérica.
- Carpetas irreemplazables con volumen no medido; volúmenes no numéricos; sin cálculo de
  capacidad a N años.
- Escenarios no cubiertos (disco, borrado, ransomware, desastre).
- Clima sin °C y %; sin hardware disponible.
- Sin regla de lo que nunca se expone; sin indicar dónde van los secretos.
- Sin política de actualizaciones; preguntas abiertas sin responsable o fecha.
- Lenguaje vago ("etc.", "si es necesario", "adecuado", "suficiente"…); sin fuentes.

### INFO
- Marcadores `[PENDIENTE]`/`[TBD]` sin responsable ni fecha.

## Secciones del NRD (referencia)

Resumen · 1. Contexto y objetivos · 2. Usuarios y dispositivos · 3. Datos y capacidad ·
4. Servicios · 5. Protección de datos · 6. Entorno y restricciones · 7. Seguridad y acceso ·
8. Operación y mantenimiento · 9. Supuestos y preguntas abiertas · 10. Historial de versiones.

## Paso 3: Corregir los CRITICAL antes de presentar

- Estructura (sección o metadato que falta): añádela con Edit y
  `[PENDIENTE: … — responsable: X, fecha: AAAA-MM-DD]`.
- Contenido que requiere decisión (criticidad, RPO): pregunta con `AskUserQuestion`.
- Secretos: sustitúyelos por "en el gestor de contraseñas" o una IP privada/ejemplo; avisa al
  usuario de que ese secreto pudo quedar en el historial local si ya se hizo commit.
- Vuelve a validar hasta 0 CRITICAL.

## Paso 4: Informe

Checklist accionable:

```
Validación de NRD-2026-10-08-nas-familiar.md

CRITICAL: 0 (2 corregidos)
WARNING:
- [ ] Datos y capacidad: 'Fotos' es irreemplazable y su volumen no está medido
INFO:
- [ ] línea 88: marcador pendiente sin responsable ni fecha

Resumen: 0 critical, 1 warning, 1 info
```

Pregunta con `AskUserQuestion` qué WARNING arreglar (todos, solo los importantes, dejarlos).

## Paso 5: Nota de sesión

Siempre, pase o no: `memory/nrd/session-AAAA-MM-DD.md` con fichero validado, recuentos antes y
después, arreglos aplicados, decisiones y avisos que el usuario decidió dejar (con responsable y
fecha).

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "validate-nrd", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/nrd/learnings-queue.jsonl
```

## Paso final: aplicar aprendizajes

Si `memory/nrd/learnings-queue.jsonl` tiene entradas `pending`, invoca
`/requirements-plugin:apply-learnings`.

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
