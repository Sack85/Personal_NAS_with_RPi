---
name: create-upd
description: >
  Prepara un plan de actualización (UPD) del NAS: parte del inventario actual, compara con el
  anterior, busca las notas de versión de cada componente que cambia, evalúa el impacto contra
  el HLD aprobado (sobre todo kernel y firmware frente al HAT PCIe), decide qué se aplica y qué
  se pospone, y escribe precondiciones, pasos, verificación posterior y vuelta atrás.
  También llamado: plan de actualización, actualizar OMV, actualizar el kernel, parches.
  Entradas: state/inventory/ + HLD aprobado. Salida: UPD en outputs/upd/vN/.
  Úsala cuando el usuario pida:
  - Actualizar el NAS, OMV, el kernel, Docker o Nextcloud
  - Preparar la actualización del mes
  - Saber si una actualización es segura
  - "¿Puedo actualizar ya?" o "hay actualizaciones pendientes"
  - Revisar qué rompe una versión nueva
argument-hint: "[inventario]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Crear un plan de actualización (UPD)

Eres el mantenedor del NAS. Las actualizaciones son la causa más probable de que este NAS deje
de ver sus discos (kernel + HAT PCIe) o de que la web de OMV no arranque (plugins). Tu trabajo
es que cada actualización se haga sabiendo qué cambia, con backups al día y con una vuelta
atrás escrita.

---

## Fase 0: Puertas

1. **HLD aprobado** (como en los runbooks): sin HLD Aprobado, para.
2. **Inventario de hoy**: el más reciente de `state/inventory/` debe ser de hoy o de ayer. Si
   no, invoca `/maintainer-plugin:inventory`.
3. **Salud**: ejecuta `tools/inventory_diff.py` (anterior → actual). Si hay alertas CRITICAL de
   discos, PCIe o SnapRAID, **no se planifica la actualización** salvo que el usuario la
   justifique por seguridad; primero `/storage-plugin:diagnose-disk` o la revisión indicada.

## Fase 1: Qué cambia

- `pendientes` del inventario + diferencias de versión con el anterior.
- Por cada componente: versión actual → nueva, tipo (seguridad, mayor, menor).
- Nextcloud AIO se actualiza solo tras su backup diario: aparece como "No aplica" salvo que el
  usuario quiera forzar algo.

## Fase 2: Notas de versión (obligatorio para kernel, firmware, OMV y plugins)

Con WebSearch/WebFetch busca las notas de versión y problemas conocidos de cada componente
relevante: Raspberry Pi OS / kernel `rpi-2712`, firmware/EEPROM de la Pi 5, OpenMediaVault 8 y
los plugins usados (snapraid, mergerfs, compose, nut, sharerootfs), Docker. Busca en concreto:
- cambios en PCIe/DMA de la Pi 5 o en el overlay `pcie-32bit-dma-pi5`;
- incompatibilidades de plugins de OMV con la versión nueva;
- cambios que exijan migración manual.

Cita la fuente en la columna Fuente. Si no encuentras nada fiable, dilo ("sin notas
encontradas") y sube el riesgo.

## Fase 3: Impacto y decisión

1. Para cada cambio, qué sección del HLD toca (tabla de componentes del HLD §10) y su mitigación.
2. Propón la decisión por componente (Aplicar / Posponer / Descartar / No aplica) y confírmala
   con `AskUserQuestion` (header ≤ 12 caracteres; la recomendada primera con "(Recomendado)").
3. Si un cambio obliga a cambiar el diseño (p. ej. un overlay distinto), el UPD **no** lo
   resuelve: propone `/architect-plugin:update-hld` primero.

## Fase 4: Escribir el UPD

1. Plantilla: `maintainer-plugin/skills/create-upd/UPD_template.j2`.
   Ejemplo completo: [examples/sample-upd.md](examples/sample-upd.md).
2. Precondiciones: siempre SnapRAID sin errores y sync reciente, backup de AIO correcto, restic
   de menos de 31 días, SAI en `OL`, sin alertas CRITICAL.
3. Pasos con las mismas reglas que los runbooks (Riesgo, Ejecuta, Dónde, Esperado, Si falla;
   destructivo = usuario con comprobación previa). Las actualizaciones desde la web de OMV las
   hace el usuario; el reinicio y las comprobaciones, el agente.
4. Si cambia kernel o firmware: comprobar config.txt antes; después `uname -r`, `lsblk` (tres
   SATA) y `LnkSta` 8GT/s. El validador lo exige.
5. Vuelta atrás concreta por componente.
6. Guarda en `$(ls -d outputs/upd/v* | sort -V | tail -1)/UPD-AAAA-MM-DD-<corto>.md`.

## Fase 5: Validar, registrar y aplicar aprendizajes

1. `/maintainer-plugin:validate-upd`; corrige CRITICAL.
2. Nota en `memory/upd/session-AAAA-MM-DD.md` con fuentes consultadas y decisiones.
3. Aprendizajes pendientes → `/maintainer-plugin:apply-learnings`.
4. Siguiente: `/maintainer-plugin:approve-upd` y luego `/operator-plugin:create-ops <UPD>`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-upd", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/upd/learnings-queue.jsonl
```

---

## Cuatro responsabilidades

1. **Saber qué cambia** (inventario + notas de versión con fuente).
2. **Proteger antes** (precondiciones de backup y SnapRAID).
3. **Comprobar después** (discos, PCIe, servicios, inventario posterior).
4. **Poder volver** (vuelta atrás por componente).

## Prevención de errores

1. **Actualizar con un disco degradándose**: un reinicio puede ser lo que lo rompa; primero el DCP.
2. **"Es solo un parche"**: un kernel menor también puede cambiar el PCIe de la Pi 5.
3. **Actualizar todo a la vez sin poder aislar fallos**: si hay kernel y cambio mayor de OMV,
   considera dos ventanas (pregúntalo).

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
