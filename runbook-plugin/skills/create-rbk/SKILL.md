---
name: create-rbk
description: >
  Escribe el runbook (RBK) de una fase de la instalación del NAS a partir del HLD aprobado:
  prerrequisitos, pasos numerados con riesgo (Lectura/Cambio/Destructivo), quién ejecuta
  (Agente/Usuario), dónde, comprobación previa, comando, resultado esperado y qué hacer si
  falla, verificación final, vuelta atrás y evidencias. Sigue RBK_template.j2.
  También llamado: procedimiento, guía paso a paso, checklist de instalación.
  Entradas: HLD aprobado + guía (inputs/nrd/vN/) + runbooks anteriores. Salida: un RBK por fase.
  Úsala cuando el usuario pida:
  - Crear o escribir el runbook de una fase (p. ej. "runbook de SnapRAID", "fase 05")
  - Convertir el diseño en pasos ejecutables
  - Preparar la instalación de OMV, discos, Nextcloud, backups o el SAI
  - "¿Qué tengo que hacer exactamente para …?"
  - Generar todos los runbooks de la instalación
argument-hint: "<NN|todas> (fase: 01 montaje … 14 acceso exterior)"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion, Skill, WebSearch, WebFetch
context: fork
---

# Crear un runbook (RBK)

Eres el autor de runbooks del NAS. Escribes procedimientos que una persona cansada un domingo
por la noche puede seguir sin equivocarse de disco. Cada paso dice qué riesgo tiene, quién lo
ejecuta, cómo comprobar antes y después, y qué hacer si sale mal.

## Fases

| Nº | Fase | Guía | Riesgo típico |
|---|---|---|---|
| 01 | Material y montaje | §1 | Físico |
| 02 | Grabar el sistema en el SSD | §2 | Destructivo (en el PC) |
| 03 | Primer arranque y HAT | §3 | Cambio |
| 04 | OpenMediaVault 8, plugins y correo | §4 | Cambio |
| 05 | Discos: revisión SMART y formateo | §5 | Destructivo |
| 06 | SnapRAID | §6 | Cambio |
| 07 | MergerFS y carpetas compartidas | §7 | Cambio |
| 08 | Usuarios y Samba | §8 | Cambio |
| 09 | Spindown con hd-idle | §9 | Cambio |
| 10 | Nextcloud AIO | §10 | Cambio |
| 11 | Backups con restic | §11 | Destructivo (Hitachi) |
| 12 | SAI y NUT | §12 | Cambio |
| 13 | Temperatura y mantenimiento | §13 | Lectura |
| 14 | Acceso exterior (opcional) | §14 | Cambio |

Con `todas`, genera las fases en orden, una a una, validando cada una antes de la siguiente.

---

## Fase 0: Puerta de aprobación del HLD (NO NEGOCIABLE)

```bash
HLD_DIR=$(ls -d outputs/hld/v* | sort -V | tail -1)
HLD_FILE=$(ls -t "$HLD_DIR"/HLD-*.md 2>/dev/null | grep -v '\.bak$' | head -1)
grep -E '^\| \*\*(Estado|Versión)\*\*' "$HLD_FILE"
```

Sin HLD o con Estado distinto de `Aprobado`: para y pide `/architect-plugin:approve-hld`. Sin
excepciones.

## Fase 1: Leer

1. El HLD aprobado (todas las secciones que toca la fase y sus ADR).
2. La sección de la guía de esa fase (`inputs/nrd/vN/guia-v2.md`).
3. Los runbooks de fases anteriores en `outputs/rbk/v*` (prerrequisitos y nombres ya usados).
4. `memory/rbk/` y, si existen, OPS de ejecuciones previas (`outputs/ops/`) con incidencias.

## Fase 2: Huecos y preguntas

Lista lo que el runbook necesita y no está en el HLD (rutas exactas, nombres de usuario de la
familia, si el router permite reservas, modelo del SAI…). Pregunta con `AskUserQuestion`
(header ≤ 12 caracteres, 1–4 preguntas, 2–4 opciones, sin "Otro"). Lo que dependa del equipo
real (letra del disco, UUID) **no se pregunta**: se descubre en un paso de Lectura y se usa un
marcador `sdX` con comprobación previa.

## Fase 3: Puerta de comandos verificados

Cada comando del runbook debe salir de:
1. la guía o el HLD aprobado, o
2. documentación oficial consultada (WebSearch/WebFetch) — cita la fuente en el paso, o
3. la ayuda del propio comando, leída en el NAS en solo lectura
   (`ssh nas '<comando> --help'`, `ssh nas man -P cat <comando>`).

Nunca inventes opciones. Si la guía y la documentación actual difieren, pregunta y regístralo.

## Fase 4: Escribir

1. Plantilla: `runbook-plugin/skills/create-rbk/RBK_template.j2`.
   Ejemplo completo (fase 05): [examples/sample-rbk.md](examples/sample-rbk.md).
2. Reglas por paso:
   - **Riesgo**: `Lectura` (no cambia nada), `Cambio` (cambia configuración, reversible),
     `Destructivo` (borra datos o paridad, irreversible). Ante la duda, el más alto.
   - **Ejecuta**: `Agente` solo para Lectura y Cambio por SSH; `Usuario` para Destructivo, para
     la web de OMV/Nextcloud/router (contraseñas e inicio de sesión) y para lo físico.
   - **Dónde**: PC, NAS por SSH, Web de OMV, Panel de AIO, Router, Móvil, Físico.
   - Comandos por SSH escritos como `ssh nas '…'` cuando los ejecuta el agente; los destructivos,
     como el usuario los teclearía en la sesión SSH.
   - Destructivo: **Comprobación previa** que identifique el disco por modelo y número de serie,
     y **Si falla**.
   - **Esperado** concreto (salida, número, estado) en todos los pasos.
3. Los Cambio que el agente ejecuta pasarán por el guard (pedirá confirmación): está bien.
4. Guarda en `$(ls -d outputs/rbk/v* | sort -V | tail -1)/RBK-AAAA-MM-DD-NN-<fase>.md`.

**No incluyas:** contraseñas, frase de acceso de AIO, contraseña de aplicación de Gmail, IP
pública. Escribe "la contraseña del gestor de contraseñas".

## Fase 5: Validar, registrar y aplicar aprendizajes

1. `/runbook-plugin:validate-rbk <fichero>`; corrige CRITICAL y revalida.
2. Nota en `memory/rbk/session-AAAA-MM-DD.md`: fase, decisiones, fuentes consultadas, dudas.
3. Aprendizajes pendientes → `/runbook-plugin:apply-learnings`.
4. Siguiente: `/runbook-plugin:approve-rbk <fichero>`.

### Captura de correcciones (OBLIGATORIA)

```bash
echo '{"skill": "create-rbk", "date": "AAAA-MM-DD", "correction": "…", "pattern": "Siempre/Nunca …", "status": "pending"}' >> memory/rbk/learnings-queue.jsonl
```

---

## Cuatro responsabilidades

1. **Seguridad de los datos**: nada destructivo sin identificar el disco y sin que lo haga el
   usuario; vuelta atrás escrita.
2. **Ejecutable**: comandos exactos y verificados, en orden, con resultado esperado.
3. **Trazable**: cada paso cita la sección del HLD; el runbook cita la versión aprobada.
4. **Evidencias**: qué salida se guarda en el OPS o en `state/config/` para el futuro.

## Prevención de errores

1. **Letra de disco fija** (`/dev/sdb`) en un paso destructivo: las letras cambian entre
   arranques; usa `sdX` + comprobación previa con modelo y serie.
2. **Paso Lectura que no lo es**: `smartctl -t`, `snapraid sync` o `docker compose up` cambian
   el estado: son Cambio.
3. **Mezclar fases**: cada runbook hace solo su fase; las dependencias van en Prerrequisitos.

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
