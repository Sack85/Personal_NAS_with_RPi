# storage-plugin

Experto en discos del NAS. Se usa cuando un disco muere, cuando empieza a fallar, cuando hay que
cambiarlo o cuando se quiere añadir uno más grande. Diagnostica en solo lectura y escribe un
**plan de cambio de discos (DCP)** con el procedimiento exacto para SnapRAID + MergerFS; lo
ejecuta el operador y los pasos destructivos los hace siempre el usuario.

## Escenarios

| Escenario | Claves |
|---|---|
| Fallo de disco de datos | No sincronizar (sync programado desactivado); disco nuevo ≥ al muerto y ≤ paridad, mismo nombre (dN) en SnapRAID; `snapraid -d dN -l fix.log fix`, luego `-d dN -a check`, luego sync |
| Fallo de paridad | Los datos están intactos; disco nuevo ≥ mayor disco de datos; ext4 con 0 % reservado; sync completo |
| Sustitución preventiva | SMART 5/197/198 crecen: backup y sync al día, copia del disco viejo al nuevo, cambio de rutas en SnapRAID y MergerFS, sync |
| Ampliación | Disco mayor que la paridad → pasa a ser la paridad y la antigua se convierte en dato; si no, nuevo dN en SnapRAID y MergerFS |
| Retirada | Vaciar con rsync al resto del pool, quitar del array y del pool, sync |

En todos: actualizar content files, MergerFS, hd-idle (`/dev/disk/by-id`), vigilancia SMART en
OMV, HLD (`/architect-plugin:update-hld`) y `state/config/`.

## Skills

| Skill | Comando | Qué hace |
|---|---|---|
| diagnose-disk | `/storage-plugin:diagnose-disk <disco>` | Diagnóstico en solo lectura y escenario recomendado |
| create-dcp | `/storage-plugin:create-dcp` | Escribe el plan del escenario |
| update-dcp | `/storage-plugin:update-dcp` | Ajusta el plan (otro disco, incidencia) |
| validate-dcp | `/storage-plugin:validate-dcp` | Reglas de seguridad por escenario |
| approve-dcp | `/storage-plugin:approve-dcp` | Aprueba el plan para ejecutarlo |
| apply-learnings | `/storage-plugin:apply-learnings` | Convierte correcciones en reglas |

## Reglas que el validador bloquea

- La disposición final de discos incumple SnapRAID (paridad < mayor dato, paridad en el pool,
  content insuficientes): por ejemplo, un disco mayor que la paridad asignado como dato.
- Precondiciones sin backup o sin desactivar el sync programado.
- Fallo de disco de datos: sin `fix -d`, o con un `sync` antes del `fix`.
- Fallo de paridad: sin sync completo.
- Las reglas por paso de los runbooks (destructivo = usuario con comprobación previa).
