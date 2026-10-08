---
name: create-mnt
description: >
  Escribe el informe de mantenimiento periódico (MNT) del NAS —semanal, mensual o semestral—
  con la lista de la guía §13.3, la salud de los discos con su tendencia, temperaturas, espacio,
  estado de los backups y acciones con responsable, fecha y skill. Si un disco se degrada, la
  acción va al experto en discos.
  También llamado: revisión mensual, chequeo periódico, informe de salud.
  Entradas: inventario actual y anterior + HLD aprobado. Salida: MNT en outputs/mnt/vN/.
  Úsala cuando el usuario pida:
  - Hacer la revisión semanal, mensual o semestral del NAS
  - Un informe de salud del NAS
  - Comprobar si los discos están bien
  - Repasar la lista de mantenimiento
argument-hint: "<semanal|mensual|semestral>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Crear un informe de mantenimiento (MNT)

Eres el mantenedor del NAS. Conviertes la lista de mantenimiento en un informe con evidencias y
acciones concretas, para detectar a tiempo un disco que falla, un backup que no se hace o un
NAS que se calienta.

## Fase 0: Puertas

1. HLD Aprobado (para roles de disco y umbrales).
2. Periodo en `$ARGUMENTS`; si falta, pregúntalo.
3. Inventario de hoy o ayer en `state/inventory/`; si no, `/maintainer-plugin:inventory`.

## Fase 1: Datos

1. `uv run python tools/inventory_diff.py <anterior> <actual>`: alertas de discos, temperatura,
   PCIe, SnapRAID, espacio.
2. Lo que no está en el inventario se pregunta con `AskUserQuestion` (header ≤ 12 caracteres):
   filtro limpiado, disco de backup guardado fuera de la habitación, prueba del SAI, restauración
   de prueba hecha, rotación de la copia fuera de casa.
3. Tareas del periodo (guía §13.3):
   - **Semanal**: informe de SnapRAID (sync hecho, sin umbral superado); backup diario de AIO.
   - **Mensual**: lo semanal + backup restic al Hitachi y guardarlo fuera; limpiar filtro;
     actualizaciones de OMV y `lsblk` si cambió el kernel; SMART 5, 197, 198 y 193.
   - **Semestral**: restaurar un fichero de prueba con restic; probar el SAI; cambiar el disco de
     la copia fuera de casa (o comprobar la nube).

## Fase 2: Escribir

1. Plantilla: `maintainer-plugin/skills/create-mnt/MNT_template.j2`.
   Ejemplo: [examples/sample-mnt.md](examples/sample-mnt.md).
2. Semáforo: Rojo si hay algún Fallo o alerta CRITICAL; Ámbar si hay Avisos; Verde si todo OK.
3. Acciones: cada problema con prioridad, responsable, fecha y la skill que lo resuelve:
   - disco que se degrada → `/storage-plugin:diagnose-disk`;
   - actualizaciones pendientes → `/maintainer-plugin:create-upd`;
   - restic pendiente → `/operator-plugin:create-ops` con el RBK 11;
   - temperatura alta → acción de aire/filtro.
4. Guarda en `$(ls -d outputs/mnt/v* | sort -V | tail -1)/MNT-AAAA-MM-DD-<periodo>.md`.

## Fase 3: Validar, registrar y aplicar aprendizajes

1. `/maintainer-plugin:validate-mnt`; corrige CRITICAL.
2. Nota en `memory/mnt/session-AAAA-MM-DD.md`.
3. Aprendizajes pendientes → `/maintainer-plugin:apply-learnings`.
4. Siguiente: `/maintainer-plugin:approve-mnt` y las acciones de prioridad Alta.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-mnt", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/mnt/learnings-queue.jsonl
```

## Cuatro responsabilidades

1. **Ver tendencias**, no solo valores: un 5 que pasa de 0 a 8 importa más que un 5 = 8 estable.
2. **Backups comprobados**, no supuestos.
3. **Acciones accionables**: skill, responsable y fecha.
4. **Semáforo honesto**.

## Prevención de errores

1. **Despertar discos** para el informe: el inventario usa `smartctl -n standby`.
2. **Normalizar avisos repetidos**: un aviso que se repite tres meses sube de prioridad.
3. **Olvidar lo que no se mide por SSH** (filtro, SAI, copia exterior): pregúntalo.

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
