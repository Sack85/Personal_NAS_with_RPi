---
name: diagnose-disk
description: >
  Diagnostica en solo lectura un disco del NAS que falla, desaparece, da errores o se quiere
  cambiar: SMART con tendencia, mensajes del kernel, estado de SnapRAID, qué datos y carpetas
  tiene, cuánto ocupa y si está el backup al día. Termina con el escenario recomendado
  (fallo de datos, fallo de paridad, sustitución preventiva, ampliación, retirada) y el disco
  nuevo que encaja.
  También llamado: revisar un disco, disco roto, disco que hace ruido, errores SMART.
  Entrada: rol, letra o serie del disco. Salida: diagnóstico en memory/dcp/ y recomendación.
  Úsala cuando el usuario diga o pida:
  - "Se ha muerto un disco" o "ha desaparecido un disco"
  - Revisar un disco con errores SMART o que hace ruido
  - "Quiero cambiar un disco" o "quiero añadir un disco más grande"
  - Saber si un disco aguanta o hay que cambiarlo
  - Después de un aviso de SMART o de un MNT en rojo
argument-hint: "<d1|d2|paridad|serie|nuevo>"
allowed-tools: Read, Write, Grep, Glob, Bash, AskUserQuestion, WebSearch
---

# Diagnosticar un disco

Eres el experto en discos del NAS (SnapRAID con 1 paridad + MergerFS, ext4 por disco). En un
diagnóstico **no cambias nada**: lees, comparas y recomiendas. El primer reflejo ante un disco
muerto es proteger la paridad.

## Paso 0: Si un disco de datos ha muerto, lo primero

Si el usuario dice que un disco ha muerto o desaparecido, antes de nada dile:

> No hagas ningún `sync` y desactiva ahora la programación de SnapRAID (Servicios → SnapRAID →
> Programación). Si el sync de las 04:00 se ejecuta sin el disco, la paridad dejará de poder
> reconstruirlo.

Y confirma con `AskUserQuestion` que lo ha hecho antes de seguir.

## Paso 1: Contexto

1. HLD aprobado: tabla de almacenamiento (rol, modelo, tamaño, montaje) y bahías.
2. Últimos dos inventarios (`state/inventory/`) y
   `uv run python tools/inventory_diff.py <anterior> <actual>`.
3. Último MNT y OPS relacionados con discos (`grep -l "disco\|SMART" outputs/mnt/v*/*.md`).
4. Último backup restic (OPS del RBK 11 o pregunta).

## Paso 2: Lecturas en el NAS (solo lectura)

```bash
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; lsblk -b -d -o NAME,SIZE'
ssh nas 'sudo dmesg | grep -iE "ata[0-9]|I/O error|reset|link" | tail -40'
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status | tail -12'
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf smart'
ssh nas 'sudo smartctl -x /dev/sdX'          # solo el disco afectado; lo despierta
ssh nas 'df -h /srv/dev-disk-by-uuid-*; du -sh /srv/dev-disk-by-uuid-XXXX/* 2>/dev/null'
```

`snapraid smart` da una probabilidad de fallo por disco: úsala como dato, no como sentencia.

## Paso 3: Interpretar

| Señal | Significado | Escenario |
|---|---|---|
| Disco no aparece en `lsblk`, `dmesg` con I/O error o link down | Muerto o conexión | Revisar FFC/bahía (199) primero; si sigue: fallo |
| 5 / 197 / 198 crecen entre inventarios | Superficie degradándose | Sustitución preventiva, pronto |
| 199 crece | Cable, FFC o bahía | No cambiar el disco: revisar conexión |
| 193 sube cientos al día | Aparcado agresivo de cabezales | APM 254; vigilar |
| Temperatura > 45 °C | Aire, filtro, posición | Aire antes que disco |
| `snapraid status` con errores en un disco | Bitrot o sectores | `scrub -p bad` y vigilar |
| Pool > 85 % | Falta espacio | Ampliación |

**Dos discos a la vez** (dos de datos, o uno de datos y la paridad): con una sola paridad
SnapRAID no puede reconstruir ambos. Lo de los discos sanos sigue intacto (cada uno es ext4
legible); lo perdido se restaura desde restic (Documentos, Fotos) y lo reemplazable se da por
perdido. Dilo claramente y no prometas recuperación.

## Paso 4: Disco nuevo que encaja

- **Fallo de datos**: tamaño ≥ datos que tenía y ≤ paridad (si es mayor que la paridad, el
  escenario pasa a ser Ampliación: el nuevo será la paridad).
- **Fallo de paridad**: ≥ el mayor disco de datos, en bytes (`lsblk -b`), no en la etiqueta.
- **Ampliación**: si el nuevo es mayor que la paridad, pasa a paridad y la antigua a datos.
- Evita discos **SMR** como paridad (los sync largos se vuelven muy lentos): comprueba el modelo
  con WebSearch y cita la fuente.
- Mecánico vs SSD: hd-idle solo para mecánicos; un QLC como dato vale, como paridad no.

## Paso 5: Resultado

1. Escribe `memory/dcp/diagnostico-AAAA-MM-DD-<rol>.md` con lecturas (recortadas), señales,
   escenario recomendado, disco nuevo recomendado y urgencia (hoy / esta semana / vigilar).
2. Presenta el resumen y pregunta con `AskUserQuestion` el siguiente paso:
   - "Crear el plan (DCP)" → `/storage-plugin:create-dcp`
   - "Solo vigilar" → acción en el próximo MNT
   - "Revisar conexión primero" → cuando 199 crece o el disco va y viene

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "diagnose-disk", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/dcp/learnings-queue.jsonl
```

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
