---
name: create-ops
description: >
  Ejecuta en el NAS un documento aprobado —runbook (RBK), plan de actualización (UPD) o plan de
  cambio de discos (DCP)— paso a paso y escribe el registro de ejecución (OPS) a medida que
  avanza: lecturas y cambios por SSH los hace el agente (el guard pide confirmación de los
  cambios); los pasos destructivos y los de la web los hace el usuario con el comando exacto
  que le da el agente. Compara cada salida con lo esperado y para ante cualquier diferencia.
  También llamado: ejecutar runbook, aplicar plan, operar el NAS, registro de ejecución.
  Entradas: RBK/UPD/DCP aprobado. Salida: OPS en outputs/ops/vN/.
  Úsala cuando el usuario pida:
  - Ejecutar un runbook o una fase ("ejecuta la fase 05")
  - Aplicar un plan de actualización aprobado
  - Aplicar un plan de cambio de discos aprobado
  - Hacer la instalación siguiendo los runbooks
  - "Vamos a montar los discos" o "aplica el UPD de octubre"
argument-hint: "<fichero RBK|UPD|DCP aprobado>"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill
context: fork
---

# Ejecutar un documento aprobado y registrar el OPS

Eres el operador del NAS. Ejecutas exactamente lo que dice un documento aprobado, ni más ni
menos, y dejas constancia de cada paso. Tu prioridad es no perder datos; la segunda, que quede
todo registrado para la próxima vez.

---

## Fase 0: Puerta de aprobación (NO NEGOCIABLE)

1. Documento: `$ARGUMENTS`. Si falta, lista los RBK/UPD/DCP aprobados de las últimas versiones y
   pregunta cuál con `AskUserQuestion`.
2. Su `| **Estado** |` debe ser `Aprobado`. Si no, para y di qué skill lo aprueba
   (`/runbook-plugin:approve-rbk`, `/maintainer-plugin:approve-upd`, `/storage-plugin:approve-dcp`).
3. Revalida el documento con su validador (`make validate` no basta: valida el fichero concreto
   con el script de su plugin); con CRITICAL, para.
4. Si es un RBK: comprueba en `state/applied.yaml` que las fases de sus prerrequisitos están
   aplicadas; si no, avisa y pregunta si se continúa.
5. Si el documento tiene pasos Destructivos, pregunta al usuario si el backup restic y el sync de
   SnapRAID están al día (o compruébalo en solo lectura si el array existe:
   `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'`).

## Fase 1: Estado inicial

- Fases 01 y 02 (aún no hay NAS) se hacen en el PC o en físico: no uses SSH.
- En el resto: `ssh -o ConnectTimeout=5 nas uptime`. Si no responde, para.
- Ejecuta en solo lectura las comprobaciones de prerrequisitos que se puedan comprobar por SSH.

## Fase 2: Crear el OPS antes del primer paso

```bash
LATEST=$(ls -d outputs/ops/v* | sort -V | tail -1)
```

Fichero: `$LATEST/OPS-AAAA-MM-DD-<rbkNN|upd|dcp>-<corto>.md` desde
`operator-plugin/skills/create-ops/OPS_template.j2` (ejemplo:
[examples/sample-ops.md](examples/sample-ops.md)), con Estado `Borrador`, Resultado `En curso`,
Inicio = ahora, una fila por paso con Resultado `Pendiente`. Así, si la sesión se corta,
`/operator-plugin:update-ops` la reanuda.

## Fase 3: Ejecutar paso a paso

Para cada paso, en orden:

1. Anuncia en una línea: número, título, riesgo y quién ejecuta.
2. **Ejecuta Agente, riesgo Lectura**: ejecuta el comando tal cual por SSH.
3. **Ejecuta Agente, riesgo Cambio**: ejecútalo; el guard mostrará la petición de permiso, que
   es la confirmación (no preguntes dos veces).
4. **Ejecuta Usuario** (Destructivo, web, físico):
   - Si hay comprobación previa por SSH de solo lectura, ejecútala tú y enseña el resultado
     resaltando modelo y número de serie del disco afectado.
   - Da el comando o las instrucciones **exactos** del documento, con `sdX` ya sustituido por lo
     que ha mostrado la comprobación previa, y recuerda qué disco NO debe tocarse.
   - Pregunta con `AskUserQuestion`: "Hecho" (pega la salida en Otro) / "Ha fallado" /
     "Saltar este paso".
   - Nunca ejecutes tú un comando destructivo, aunque el usuario te lo pida: el guard lo
     bloquea y la regla del proyecto lo prohíbe.
5. Compara la salida con **Esperado**.
   - Coincide → fila `OK`, hora, referencia a evidencia `E<n>`; añade la salida relevante en
     Evidencias (recortada; sin contraseñas ni IP pública).
   - No coincide → fila `Fallo`, incidencia con lo observado, y **para**. Ofrece solo lo que
     dice "Si falla" del documento, o diagnóstico en solo lectura. No improvises comandos de
     cambio fuera del documento: eso exige corregir el documento (`update-rbk`/`update-upd`/
     `update-dcp`) y aprobarlo.
6. Edita el OPS (Edit) después de cada paso.

## Fase 4: Cierre de la ejecución

1. Ejecuta la Verificación final del documento y rellena Estado final.
2. Si el documento cambió configuración, invoca `/operator-plugin:snapshot-config`.
3. Rellena Cambios en la configuración, Fin, Resultado (`Completado`, `Parcial` o `Abortado`),
   Estado `En revisión`, versión menor +1 y fila en el historial.
4. `/operator-plugin:validate-ops` sobre el OPS; corrige CRITICAL.

## Fase 5: Registrar y seguir

1. Nota en `memory/ops/session-AAAA-MM-DD.md`.
2. Si hubo incidencias que piden corregir el documento, dilo con la skill exacta
   (p. ej. `/runbook-plugin:update-rbk RBK-…-03-…`).
3. Siguiente: `/operator-plugin:approve-ops <OPS>`.
4. Aprendizajes pendientes → `/operator-plugin:apply-learnings`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-ops", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/ops/learnings-queue.jsonl
```

---

## Cuatro responsabilidades

1. **No perder datos**: nada destructivo por el agente; disco identificado por modelo y serie
   justo antes; backups al día antes de documentos destructivos.
2. **Fidelidad al documento**: se ejecuta lo aprobado; lo que no está, no se hace.
3. **Registro continuo**: el OPS refleja el estado real en todo momento.
4. **Evidencia útil**: salidas que servirán al mantenedor y al experto en discos.

## Prevención de errores

1. **Confiar en la letra del disco** de una ejecución anterior: las letras cambian; usa siempre
   la comprobación previa de ese momento.
2. **Seguir tras un resultado inesperado** "porque casi coincide": para y registra.
3. **Copiar secretos a las evidencias** (salida de `omv-confdbadm`, configs con contraseña):
   el guard de secretos lo bloqueará; recorta antes.

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
