# requirements-plugin

Analista de requisitos del NAS. Convierte la guía de instalación y las respuestas del usuario en
un **NRD** (documento de requisitos del NAS): quién lo usa, qué datos guarda y cuánto ocupan, qué
servicios necesita, qué fallos debe aguantar, en qué entorno vive y qué no se expone nunca.

Es el primer eslabón: el arquitecto no arranca sin un NRD **Aprobado**.

## Skills

| Skill | Comando | Qué hace |
|---|---|---|
| create-nrd | `/requirements-plugin:create-nrd` | Lee `inputs/nrd/vN/`, pregunta lo que falta y escribe el NRD |
| update-nrd | `/requirements-plugin:update-nrd` | Aplica cambios con versionado A/B/C y solo con Edit |
| validate-nrd | `/requirements-plugin:validate-nrd` | Ejecuta el validador y corrige los CRITICAL |
| approve-nrd | `/requirements-plugin:approve-nrd` | Pasa el NRD a Aprobado |
| apply-learnings | `/requirements-plugin:apply-learnings` | Convierte correcciones en reglas de las skills |

## Entradas y salidas

- Entradas: `inputs/nrd/vN/` (guía v2 en markdown y PDF).
- Salida: `outputs/nrd/vN/NRD-AAAA-MM-DD-<corto>.md`.
- Memoria: `memory/nrd/` (notas de sesión y `learnings-queue.jsonl`).

## Validación

```bash
uv run python requirements-plugin/skills/validate-nrd/scripts/validate_nrd.py <fichero>
make validate D=nrd
```
