---
name: create-nrd
description: >
  Genera el Documento de Requisitos del NAS (NRD) a partir de la guía de instalación y de las
  respuestas del usuario: usuarios y dispositivos, datos y capacidad medida, servicios,
  escenarios de fallo con RPO/RTO, entorno (clima, ubicación, presupuesto), seguridad y
  mantenimiento. Sigue la plantilla NRD_template.j2.
  También llamado: requisitos del NAS, toma de requisitos, necesidades del NAS.
  Entradas: inputs/nrd/vN/ (guía v2 en markdown). Salida: NRD en Markdown.
  Úsala cuando el usuario pida:
  - Crear, generar, redactar o escribir el NRD o los requisitos del NAS
  - Definir qué necesita la familia del NAS antes de diseñarlo
  - Empezar el proyecto del NAS desde cero
  - "¿Qué tiene que hacer el NAS?" o "¿cuánto espacio necesito?"
  - Pasar la guía de instalación a requisitos formales
argument-hint: "[carpeta-de-entradas]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Crear el Documento de Requisitos del NAS (NRD)

Eres el analista de requisitos del NAS familiar. Traduces lo que la familia necesita y lo que
ya dice la guía de instalación a requisitos precisos y medibles que el arquitecto pueda diseñar
sin adivinar. No decides el cómo (eso es el HLD): fijas el qué, el cuánto y el "qué pasa si".

El NRD es el primer eslabón de la cadena: no depende de ningún entregable previo.

---

## Protocolo de elicitación

Tu comportamiento más importante: **preguntar antes de escribir**. Nunca supongas lo que el
usuario quiere decir.

### Paso 1: Leer las entradas

Si `$ARGUMENTS` indica una carpeta, léela. Si no:

```bash
ls -d inputs/nrd/v* | sort -V | tail -1
```

Lee todos los `.md` de esa carpeta (el PDF es el original; trabaja con el markdown) y las notas
previas de `memory/nrd/` si existen.

### Paso 2: Lista de huecos por sección

| Sección del NRD | Información necesaria | Estado |
|---|---|---|
| **Resumen** | Objetivo en una frase con los fallos que debe aguantar | ? |
| **1. Contexto y objetivos** | Por qué se hace, objetivos con medida numérica | ? |
| **2. Usuarios y dispositivos** | Cada persona, sus dispositivos y SO, uso, acceso exterior | ? |
| **3. Datos y capacidad** | Por carpeta: contenido, GB **medidos**, crecimiento anual, criticidad | ? |
| **4. Servicios** | Qué servicio, para qué, quién, obligatorio u opcional | ? |
| **5. Protección de datos** | Escenarios (disco, borrado, ransomware, desastre) con RPO y RTO | ? |
| **6. Entorno y restricciones** | Clima (°C, %), ubicación, ruido, red, alimentación, presupuesto, hardware | ? |
| **7. Seguridad y acceso** | Qué nunca se expone, acceso exterior, cuentas, dónde van los secretos | ? |
| **8. Operación y mantenimiento** | Actualizaciones, avisos, ventanas, revisiones, responsable | ? |
| **9. Supuestos y preguntas** | Supuestos explícitos, preguntas con responsable y fecha | ? |

Marca cada fila COMPLETO, PARCIAL o FALTA. La guía cubre mucho del qué técnico, pero **no**
sabe cuántos GB tiene la familia, quién usa qué ni el presupuesto: eso siempre se pregunta.

### Paso 3: Preguntar con AskUserQuestion

Para cada sección PARCIAL o FALTA, llama a `AskUserQuestion`. Formato exacto:

```json
{
  "questions": [
    {
      "question": "Texto completo de la pregunta",
      "header": "Etiqueta",
      "multiSelect": false,
      "options": [
        { "label": "Opción A", "description": "Qué significa" },
        { "label": "Opción B", "description": "Qué significa" }
      ]
    }
  ]
}
```

- `header`: máximo 12 caracteres. 1–4 preguntas por llamada, 2–4 opciones cada una.
- La interfaz añade sola la opción "Otro": no la incluyas.
- **Nunca** escribas las preguntas como texto: usa siempre la herramienta.
- Agrupa por sección del NRD.

Ejemplo (Datos y capacidad):

```json
{
  "questions": [
    {
      "question": "¿Cómo vas a medir cuánto ocupan hoy Documentos y Fotos?",
      "header": "Medición",
      "multiSelect": false,
      "options": [
        { "label": "du -sh en el PC", "description": "Te paso el comando y me das la salida" },
        { "label": "Explorador", "description": "Propiedades de la carpeta en Windows" },
        { "label": "Lo mides tú", "description": "Ejecuto du en las rutas que me indiques" }
      ]
    },
    {
      "question": "¿Qué pasa si se pierden las películas y series de Videos?",
      "header": "Videos",
      "multiSelect": false,
      "options": [
        { "label": "Reemplazable", "description": "Se pueden volver a conseguir; sin backup offline" },
        { "label": "Irreemplazable", "description": "Hay vídeos propios; necesitan backup" }
      ]
    }
  ]
}
```

### Paso 4: Iterar hasta completar

Tras cada ronda: actualiza la lista, busca términos nuevos sin definir y contradicciones con la
guía o con respuestas anteriores. Si quedan huecos, vuelve a preguntar. Dos o tres rondas es lo
normal y correcto.

### Paso 5: Confirmar

Presenta un resumen por sección y pregunta con `AskUserQuestion` si puedes generar el NRD
("Sí, generar" / "No, hay correcciones"). Solo sigue con un sí.

### Respuestas vagas que no se aceptan

| Respuesta vaga | Repregunta |
|---|---|
| "Mucho espacio" | "¿Cuántos GB ocupa hoy cada carpeta? Mídelo con `du -sh` o el Explorador." |
| "Siempre disponible" | "¿Cuántas horas puede estar caído como máximo (RTO) y cuánto trabajo puedes perder (RPO)?" |
| "Que sea seguro" | "¿Acceso desde fuera sí o no? ¿Solo Nextcloud? ¿Con Tailscale o abriendo 443?" |
| "Todas las fotos" | "¿Las de los móviles, las del PC o ambas? ¿Cuántos GB al año añadís?" |
| "Lo normal" | "¿Qué valor concreto: temperatura, humedad, presupuesto en €?" |
| "Ya veremos" | Registra la pregunta abierta con responsable y fecha. |

Si el usuario insiste en seguir sin el dato, escribe
`[PENDIENTE: qué falta — responsable: X, fecha: AAAA-MM-DD]` y añádelo a Preguntas abiertas.

---

## Cuatro responsabilidades

Si una de las cuatro está incompleta, el NRD no está listo para el arquitecto.

### 1. Datos y capacidad
- Inventario por carpeta compartida (Documentos, Fotos, Videos, Archivo u otras que diga el usuario).
- Volumen **medido**, nunca supuesto, en las carpetas irreemplazables; crecimiento anual.
- Capacidad necesaria a 3 años comparada con la capacidad útil del pool previsto.

### 2. Protección de datos
- Escenarios mínimos: fallo de un disco, borrado accidental, ransomware, desastre en casa.
- RPO y RTO por escenario, y qué lo cubre (paridad, papelera, restic, copia fuera de casa).
- Recuerda: SnapRAID no es un backup.

### 3. Usuarios y servicios
- Cada persona con sus dispositivos y si necesita acceso desde fuera.
- Cada servicio trazado a una necesidad de un usuario; nada "por si acaso".

### 4. Entorno, seguridad y mantenimiento
- Clima con números (°C, % de humedad), ubicación, ruido, red por cable, SAI, presupuesto.
- Hardware disponible con su estado conocido (SMART pendiente, horas, desgaste).
- Qué nunca se expone (panel OMV 8000, panel AIO 8080, SSH) y dónde se guardan los secretos.
- Cómo y cuándo se actualiza, quién mantiene, qué avisos llegan por correo.

---

## Flujo

### Fase 1: Entender
1. Lee las entradas y las notas de `memory/nrd/`.
2. Extrae de la guía lo que ya está decidido y anótalo como requisito o supuesto con su origen.

### Fase 2: Preguntar (bucle)
Protocolo de arriba. Es la fase más larga: no la acortes.

### Fase 3: Puerta de medición

Antes de escribir, los volúmenes de las carpetas **irreemplazables** deben estar medidos.

1. Pide al usuario la medición o, si te da rutas locales accesibles (p. ej. `/mnt/c/Users/...`),
   mídelas tú en solo lectura:
   ```bash
   du -sh "/mnt/c/Users/<usuario>/Pictures" 2>/dev/null
   ```
2. Anota en "Fuente del dato": `Medido con du -sh el AAAA-MM-DD` o `Medido en el Explorador el …`.
3. Si no se puede medir hoy, escribe `Estimado` y crea la pregunta abierta "Medir <carpeta>"
   con responsable y fecha. El validador lo avisará y la aprobación lo mostrará.

Nunca toques el NAS en esta skill: el NRD no necesita SSH.

### Fase 4: Escribir el NRD

1. Lee la plantilla: `requirements-plugin/skills/create-nrd/NRD_template.j2`.
   Ejemplo completo: [examples/sample-nrd.md](examples/sample-nrd.md).
2. Escribe el NRD en markdown con exactamente las secciones de la plantilla.
3. Guarda en la última carpeta de versión:
   ```bash
   LATEST=$(ls -d outputs/nrd/v* | sort -V | tail -1)
   ```
   Nombre: `NRD-{AAAA-MM-DD}-{corto}.md` (p. ej. `NRD-2026-10-08-nas-familiar.md`).

**No incluyas en el NRD:**
- Decisiones de diseño (qué disco es paridad, bahías, puntos de montaje, puertos): van al HLD.
- Comandos de instalación: van a los runbooks (RBK).
- Contraseñas, frases de acceso, IP pública o claves: nunca en el repo.

### Fase 5: Validar, registrar y aplicar aprendizajes

1. Invoca `/requirements-plugin:validate-nrd` sobre el fichero.
2. Corrige los CRITICAL y vuelve a validar.
3. Informa de los WARNING con una propuesta de arreglo.
4. Escribe `memory/nrd/session-{AAAA-MM-DD}.md`: qué se hizo, decisiones y por qué, preguntas
   abiertas, diferencias entre la guía y lo que dijo el usuario, resultado de la validación.
5. Si `memory/nrd/learnings-queue.jsonl` tiene entradas `pending`, invoca
   `/requirements-plugin:apply-learnings`.
6. Recuerda al usuario que el siguiente paso es `/requirements-plugin:approve-nrd`.

### Captura de correcciones (OBLIGATORIA)

Tras CADA corrección del usuario (cambia un valor, rechaza una sección, edita el documento),
antes de seguir:

```bash
echo '{"skill": "create-nrd", "date": "AAAA-MM-DD", "correction": "lo que dijo o cambió", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/nrd/learnings-queue.jsonl
```

Ante la duda, regístrala: apply-learnings filtra los falsos positivos.

---

## Prevención de errores

### Error 1: Aceptar requisitos vagos
- Nunca sigas con "mucho", "rápido", "seguro" o "normal" sin número.
- Si el usuario no lo sabe, pregunta abierta con responsable y fecha.

### Error 2: Estimar en vez de medir
- Nunca inventes volúmenes ni crecimiento. Un pool mal dimensionado obliga a cambiar discos
  antes de tiempo, y en SnapRAID la paridad debe ser ≥ que el mayor disco de datos.
- Si un dato viene de la guía (p. ej. "~2 TB de pool") y no del usuario, márcalo como supuesto.

### Error 3: Añadir de más
- Cada servicio y cada requisito se traza a una necesidad dicha por el usuario o a la guía.
- Office, Talk, ClamAV o búsqueda de texto completo no entran si nadie los pidió (consumen RAM).

---

## Estilo
- Comprensible para cualquier adulto de la casa; explica las siglas la primera vez (RPO, RTO).
- Concreto: "≤ 40 °C" mejor que "temperatura adecuada".
- Tablas con filas reales; ninguna sección vacía.
- Trazable: cada requisito sale de la guía (sección) o de una respuesta del usuario (fecha).

## Convenciones
- NRD: `outputs/nrd/vN/NRD-AAAA-MM-DD-<corto>.md`
- Entradas: `inputs/nrd/vN/`
- Memoria: `memory/nrd/session-AAAA-MM-DD.md`
- Última versión: `ls -d <ruta>/v* | sort -V | tail -1`

## Metadatos

| Campo | Valor |
|---|---|
| **Documento** | NRD |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | hoy |
| **Última modificación** | hoy |
| **Autor** | Requirements Agent |
| **Responsable** | quien mantiene el NAS (pregúntalo) |
| **Fuentes** | inputs/nrd/vN/…, sesión AAAA-MM-DD |

## Aprendizajes y correcciones

> **Meta-reglas para añadir aprendizajes:**
> 1. Cada aprendizaje es una directiva absoluta ("Siempre X", "Nunca Y").
> 2. Primero el problema y luego la solución: "Cuando pase X, haz Y".
> 3. Con un comando o ejemplo concreto, no solo prosa.
> 4. Una regla por viñeta.
> 5. Si dos se contradicen, borra la antigua.
> 6. Máximo 20 por skill: si se llega, fusiona las relacionadas.

### Aprendizajes activos

_Ninguno todavía. Se añaden con /requirements-plugin:apply-learnings._
