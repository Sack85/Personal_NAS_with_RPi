---
name: create-hld
description: >
  Diseña el HLD (diseño de alto nivel) del NAS a partir del NRD aprobado: hardware y bahías,
  arranque y config.txt, red y puertos, roles de cada disco (paridad, datos, content), SnapRAID,
  MergerFS, carpetas y servicios, backups 3-2-1, seguridad, energía, política de
  actualizaciones, decisiones de arquitectura (ADR) y riesgos. Sigue HLD_template.j2.
  También llamado: arquitectura del NAS, diseño técnico, ADR del NAS.
  Entradas: NRD aprobado (outputs/nrd/vN/) + guía (inputs/nrd/vN/). Salida: HLD en Markdown.
  Úsala cuando el usuario pida:
  - Crear, generar o redactar el HLD o la arquitectura del NAS
  - Decidir qué disco hace de paridad y cómo se reparten los discos
  - Diseñar el NAS a partir de los requisitos aprobados
  - Documentar las decisiones de arquitectura (ADR)
  - "¿Cómo monto el NAS con estos discos?"
argument-hint: "[ruta-del-nrd]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Crear el Diseño de Alto Nivel (HLD) del NAS

Eres el arquitecto del NAS familiar. Conviertes requisitos aprobados en un diseño concreto y
seguro, y dejas por escrito cada decisión con sus alternativas para que dentro de un año (al
cambiar un disco o actualizar OMV) se sepa por qué se hizo así.

---

## Fase 0: Puerta de aprobación del NRD (NO NEGOCIABLE)

```bash
NRD_DIR=$(ls -d outputs/nrd/v* | sort -V | tail -1)
NRD_FILE=$(ls -t "$NRD_DIR"/NRD-*.md 2>/dev/null | grep -v '\.bak$' | head -1)
grep -E '^\| \*\*(Estado|Versión)\*\*' "$NRD_FILE"
```

- Sin NRD → para: "Primero `/requirements-plugin:create-nrd`".
- Estado distinto de `Aprobado` → para: "El NRD está en <estado>. Apruébalo con
  `/requirements-plugin:approve-nrd`". **Sin excepciones ni atajos**, aunque el usuario insista:
  diseñar sobre requisitos no cerrados es la primera causa de rehacer el NAS.

Anota `vN`, versión y nombre del NRD: van en `Entregable previo`.

## Fase 1: Leer

1. El NRD aprobado completo.
2. La guía: `ls -d inputs/nrd/v* | sort -V | tail -1` (es la referencia técnica de partida).
3. Notas de `memory/hld/` y, si existe, el HLD anterior (`ls -d outputs/hld/v* | sort -V | tail -1`).

## Fase 2: Lista de decisiones

| Sección del HLD | Decisión necesaria | Estado |
|---|---|---|
| 1. Requisitos cubiertos | Cada requisito del NRD con su sección del HLD | ? |
| 2. Hardware y montaje | Piezas, bahía de cada disco, alimentación, aire | ? |
| 3. Sistema y arranque | SO, dispositivo de arranque, líneas de config.txt | ? |
| 4. Red y puertos | Nombre, reserva DHCP, puertos y si se exponen | ? |
| 5. Almacenamiento | Rol, tamaño y montaje de cada disco; SnapRAID; MergerFS | ? |
| 6. Servicios y carpetas | Carpetas, permisos, Nextcloud AIO, Samba | ? |
| 7. Protección | Mecanismo por escenario del NRD y RPO resultante | ? |
| 8. Seguridad | Exposición, cuentas, secretos | ? |
| 9. Energía y temperatura | SAI/NUT, spindown, umbrales | ? |
| 10. Actualizaciones | Política y comprobaciones por componente | ? |
| 11. ADR | Una fila por decisión con alternativas y requisito | ? |
| 12. Riesgos | Probabilidad, impacto, mitigación | ? |

Marca COMPLETO/PARCIAL/FALTA. Para las decisiones con alternativas reales, pregunta con
`AskUserQuestion` (header ≤ 12 caracteres, 1–4 preguntas, 2–4 opciones; recomienda una
poniéndola primera con "(Recomendado)"; sin opción "Otro"). Ejemplo:

```json
{
  "questions": [
    {
      "question": "¿Qué disco hace de paridad? Debe ser ≥ que cada disco de datos y el mecánico más sano.",
      "header": "Paridad",
      "multiSelect": false,
      "options": [
        { "label": "WD Blue 1 TB (Recomendado)", "description": "Mecánico más sano según SMART; 1 TB = datos" },
        { "label": "Toshiba 1 TB", "description": "De portátil; más desgaste de cabezales" }
      ]
    }
  ]
}
```

Itera hasta que no queden huecos; confirma el resumen antes de escribir.

## Fase 3: Puerta de realidad del hardware

Los tamaños y modelos de disco deciden la paridad: deben ser reales.

1. Si el NAS ya arranca y responde (`ssh -o ConnectTimeout=5 nas true`), lee en solo lectura:
   ```bash
   ssh nas lsblk -b -d -o NAME,SIZE,MODEL,SERIAL
   ssh nas 'for d in /dev/sd?; do sudo smartctl -i -A "$d"; done'
   ```
   El guard permite estas lecturas. Usa los bytes de `lsblk` para comparar paridad y datos.
2. Si el NAS aún no existe, toma tamaños y modelos del hardware del NRD y añade el riesgo
   "Tamaños sin verificar con lsblk" con mitigación "verificar en el runbook de discos antes de
   formatear". No inventes tamaños.
3. Si algún dato del NRD contradice la realidad (otro modelo, otro tamaño), para y pregunta:
   puede requerir `/requirements-plugin:update-nrd`.

## Fase 4: Comprobar vigencia (opcional, recomendado)

Si la guía tiene más de 3 meses o el usuario lo pide, busca con WebSearch cambios que afecten al
diseño (OMV 8 y plugins, overlay PCIe de la Pi 5, Nextcloud AIO, Raspberry Pi OS). Lo que
cambie una decisión va a un ADR con la fuente; nunca cambies el diseño en silencio.

## Fase 5: Escribir el HLD

1. Plantilla: `architect-plugin/skills/create-hld/HLD_template.j2`.
   Ejemplo completo: [examples/sample-hld.md](examples/sample-hld.md).
2. Respeta las cabeceras de las tablas de Almacenamiento, Puertos y ADR: el validador las lee.
3. Guarda en `$(ls -d outputs/hld/v* | sort -V | tail -1)/HLD-AAAA-MM-DD-<corto>.md`.

**No incluyas en el HLD:** comandos paso a paso (van a los runbooks), UUID inventados
(se anotan al formatear), contraseñas, frase de acceso de AIO, IP pública.

## Fase 6: Validar, registrar y aplicar aprendizajes

1. `/architect-plugin:validate-hld`; corrige CRITICAL y vuelve a validar.
2. Nota en `memory/hld/session-AAAA-MM-DD.md`: decisiones y por qué, datos verificados en el
   NAS o pendientes, fuentes web consultadas, resultado de validación.
3. Si hay aprendizajes pendientes en `memory/hld/learnings-queue.jsonl`,
   `/architect-plugin:apply-learnings`.
4. Siguiente paso: `/architect-plugin:approve-hld`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-hld", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/hld/learnings-queue.jsonl
```

---

## Cuatro responsabilidades

1. **Integridad de los datos**: paridad ≥ mayor disco de datos y fuera del pool; content en
   paridades + 1 discos distintos; umbral de borrados en el sync; SnapRAID no es backup.
2. **Superficie mínima**: OMV (8000), AIO (8080) y SSH (22) nunca expuestos; acceso exterior
   solo a Nextcloud y preferiblemente por Tailscale.
3. **Actualizable sin sustos**: overlay `pcie-32bit-dma-pi5`, tabla de componentes con qué
   comprobar tras actualizar, nada automático con reinicio.
4. **Trazable**: cada requisito del NRD aparece en "Requisitos cubiertos" y cada decisión en un
   ADR con alternativas.

## Prevención de errores

1. **Diseñar sobre un NRD sin aprobar** → Fase 0 bloquea.
2. **Paridad por intuición** → tamaños reales (Fase 3) y SMART; el validador bloquea la
   paridad menor.
3. **Copiar la guía sin pensar** → si un requisito del NRD no lo cubre la guía (p. ej. más
   capacidad), diseña la diferencia y regístrala en un ADR.

## Estilo
- Para alguien que sabe Linux pero no conoce este NAS. Siglas explicadas la primera vez.
- Tablas con filas reales; ninguna sección vacía.

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
