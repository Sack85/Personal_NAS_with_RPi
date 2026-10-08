# maintainer-plugin

Mantenedor del NAS. Su trabajo es que actualizar no dé miedo y que los problemas se vean antes
de que pierdan datos.

## Ciclo de actualización

```
/maintainer-plugin:inventory          lee versiones y salud por SSH → state/inventory/AAAA-MM-DD.yaml
/maintainer-plugin:create-upd         compara con el inventario anterior, lee notas de versión,
                                      evalúa el impacto contra el HLD → UPD en Borrador
/maintainer-plugin:approve-upd        revisión y aprobación
/operator-plugin:create-ops <UPD>     ejecución con precondiciones, pasos y verificación
/operator-plugin:approve-ops          cierre; queda en state/applied.yaml
/maintainer-plugin:inventory          inventario posterior para comprobar el resultado
```

## Mantenimiento periódico

`/maintainer-plugin:create-mnt semanal|mensual|semestral` hace el informe de la lista de la
sección 13.3 de la guía con evidencias del inventario: SnapRAID, backups, SMART con tendencia,
temperaturas, espacio. Si un disco se degrada, la acción apunta a `/storage-plugin:diagnose-disk`.

Para que no se olvide, puedes programarlo (opcional): `/schedule` con una tarea mensual que
ejecute `/maintainer-plugin:inventory` y `/maintainer-plugin:create-mnt mensual`.

## Skills

| Skill | Qué hace |
|---|---|
| inventory | Inventario de versiones y salud en solo lectura |
| create-upd / update-upd / validate-upd / approve-upd | Plan de actualización |
| create-mnt / update-mnt / validate-mnt / approve-mnt | Informe de mantenimiento |
| apply-learnings | Convierte correcciones en reglas |

`scripts/inventory_diff.py` compara dos inventarios (versiones que cambian, atributos SMART que
crecen, temperaturas y espacio) y lo usan create-upd y create-mnt.

## Reglas que el validador del UPD bloquea

- Sin inventario de referencia ni HLD aprobado.
- Sin precondiciones de SnapRAID y backup, o sin vuelta atrás.
- Cambio de kernel o firmware sin comprobar después `lsblk` y el enlace PCIe (`LnkSta` 8GT/s).
- Mismas reglas por paso que los runbooks (destructivo = usuario, comprobación previa…).
