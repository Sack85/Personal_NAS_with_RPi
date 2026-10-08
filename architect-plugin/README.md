# architect-plugin

Arquitecto del NAS. A partir del NRD **Aprobado** decide el cómo: hardware y bahías, arranque,
red y puertos, roles de cada disco (paridad, datos, content), pool, carpetas, servicios,
backups, seguridad, energía y política de actualizaciones. Cada decisión queda como ADR con sus
alternativas y el requisito que la justifica.

El HLD es la referencia que usan los runbooks, el operador, el mantenedor y el experto en discos.

## Skills

| Skill | Comando | Qué hace |
|---|---|---|
| create-hld | `/architect-plugin:create-hld` | Diseña el HLD desde el NRD aprobado |
| update-hld | `/architect-plugin:update-hld` | Aplica cambios (p. ej. un disco nuevo) con versionado A/B/C |
| validate-hld | `/architect-plugin:validate-hld` | Reglas de seguridad del diseño y completitud |
| approve-hld | `/architect-plugin:approve-hld` | Pasa el HLD a Aprobado |
| apply-learnings | `/architect-plugin:apply-learnings` | Convierte correcciones en reglas |

## Entradas y salidas

- Entrada: NRD aprobado en `outputs/nrd/vN/` y la guía en `inputs/nrd/vN/`.
- Salida: `outputs/hld/vN/HLD-AAAA-MM-DD-<corto>.md`.
- Memoria: `memory/hld/`.

## Reglas que el validador bloquea

- Paridad más pequeña que el mayor disco de datos, o paridad dentro del pool.
- Menos ficheros content que paridades + 1.
- Panel de OMV (8000), panel de AIO (8080) o SSH (22) expuestos a Internet.
- HAT Penta SATA sin `dtoverlay=pcie-32bit-dma-pi5` en `config.txt`.
- No citar la versión aprobada del NRD.
