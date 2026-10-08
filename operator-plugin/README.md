# operator-plugin

Operador del NAS. Ejecuta **solo documentos aprobados** —runbooks (RBK), planes de
actualización (UPD) y planes de cambio de discos (DCP)— y deja un registro de ejecución (OPS)
con cada paso, quién lo hizo, el resultado y la evidencia.

- Los pasos de Lectura y Cambio los ejecuta el agente por `ssh nas` (el guard pide confirmación
  para los Cambio).
- Los pasos Destructivos y los de la web de OMV, Nextcloud o el router los hace el usuario: el
  agente le da el comando exacto, espera la salida y la compara con lo esperado.
- El OPS se escribe paso a paso: si la sesión se corta, `update-ops` lo reanuda.
- Al cerrar, `state/applied.yaml` registra qué versión de cada documento está aplicada.

## Skills

| Skill | Comando | Qué hace |
|---|---|---|
| create-ops | `/operator-plugin:create-ops <RBK/UPD/DCP>` | Ejecuta el documento aprobado y escribe el OPS |
| update-ops | `/operator-plugin:update-ops <OPS>` | Reanuda una ejecución o completa evidencias |
| validate-ops | `/operator-plugin:validate-ops` | Comprueba coherencia del registro |
| approve-ops | `/operator-plugin:approve-ops <OPS>` | Cierra la ejecución y actualiza `state/applied.yaml` |
| snapshot-config | `/operator-plugin:snapshot-config` | Copia la configuración del NAS a `state/config/` (solo lectura) |
| apply-learnings | `/operator-plugin:apply-learnings` | Convierte correcciones en reglas |

## Salidas

- `outputs/ops/vN/OPS-AAAA-MM-DD-<doc>-<corto>.md`
- `state/config/` (copia de ficheros de configuración, sin secretos)
- `state/applied.yaml` (qué versión de cada documento está aplicada en el NAS)
