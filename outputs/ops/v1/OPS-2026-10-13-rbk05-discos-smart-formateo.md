# OPS — Ejecución del RBK 05 (discos: SMART, limpieza y formateo)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-13 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v2 (2.1, Aprobado) — RBK-2026-10-09-05-discos-smart-formateo.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-13 14:00 |
| **Fin** | 2026-10-13 21:00 |

> Registro a posteriori: la ejecución se hizo el 2026-10-13 y se registra sin re-ejecutar nada,
> a partir de `memory/ops/session-2026-10-13.md` (sección RBK 05) y `state/config/montajes.md`.
> Las horas de inicio y fin son aproximadas.

## Alcance

Fase 05 completa: identificación y tamaño de los tres discos SATA, SMART corto y largo,
vigilancia y tests programados en OMV, limpieza de firmas ZFS antiguas, ext4 en paridad, D1 y
D2, etiquetas, montajes y tabla de montajes. Pasos destructivos (8b, 10) hechos por el usuario.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 05 v2.1 aprobado | Sí |
| RBK 01-04 aplicados | Sí (OPS rbk01-03 Aprobado; OPS rbk04 cerrado el 2026-10-13) |
| `ssh nas` con clave | Sí |
| Pasos destructivos | Sí (8b, 9, 10, 12). Sin array SnapRAID ni datos que conservar: los discos solo tenían un pool ZFS antiguo "Photos" y el usuario confirmó por escrito "puedes borrar todo" |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Identificar los discos y sus bytes | Lectura | Agente | ~14:00 | OK | E1 |
| 2. Comparar tamaños: la paridad debe ser la mayor o igual | Lectura | Agente | ~14:00 | OK | E1 |
| 3. Leer SMART de cada disco SATA | Lectura | Agente | ~14:10 | OK | E2 |
| 4. Lanzar el test SMART largo | Cambio | Agente | ~14:20 | OK | E3 |
| 5. Leer el resultado del test largo | Lectura | Agente | 20:06 | OK | E3 |
| 6. Activar la vigilancia SMART en OMV | Cambio | Agente | ~20:10 | OK | E4 |
| 7. Programar los tests SMART | Cambio | Agente | ~20:10 | OK | E4 |
| 8. Comprobar smartd | Lectura | Agente | ~20:15 | OK | E5 |
| 8b. Limpiar las firmas ZFS antiguas de los tres discos SATA | Destructivo | Usuario | ~20:20 | OK | E6 |
| 9. Borrar los tres discos SATA | Destructivo | Usuario | — | Omitido | — |
| 10. Crear y montar ext4 en cada disco | Destructivo | Usuario | ~20:30 | OK | E7 |
| 11. Anotar qué montaje es cada disco | Lectura | Agente | ~21:00 | OK | E8 |
| 12. Bloques reservados a 0 en paridad, D1 y D2 | Destructivo | Usuario | — | Omitido | E7 |

## Evidencias

### E1 — Pasos 1-2: discos y tamaños

```
ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5   1000204886016 bytes  (paridad)
ata-TOSHIBA_MK1059GSM_Y1NDFAQES            1000204886016 bytes  (D1)
ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F 1000204886016 bytes (D2)
Paridad (WD) >= cada disco de datos: Sí (iguales)
Hallazgo: los 3 discos con pool ZFS antiguo "Photos" (part1 zfs_member + part9 8M)
```

### E2 — Paso 3: SMART (todos PASSED; atributos 5/197/198/199 = 0)

```
Toshiba Y1NDFAQES   6433 h, 3027 ciclos, Load_Cycle_Count 95042, 30 °C (máx. histórico 70 °C)
WD WD-WXU1EB6APMW5  7807 h, Load_Cycle_Count 81085, 188 Command_Timeout=1, 28 °C
QVO S5SVNG0N868475F 7727 h, Wear_Leveling_Count 24 (97 %), 187 = 0
```

### E3 — Pasos 4-5: test largo

```
Lanzado ~14:20; fin previsto: QVO ~15:47, WD ~17:36, Toshiba ~19:27
20:06 smartctl -l selftest:
  Toshiba  Extended offline  Completed without error  6437 h
  WD       Extended offline  Completed without error  7810 h
  QVO      Extended offline  Completed without error  7728 h
```

### E4 — Pasos 6-7: vigilancia y tests (agente, omv-rpc)

```
Smart setSettings: enable, interval 1800, powermode standby, tempmax 40
  (tempmax 45 generaba -W 0,45,50; corregido a 40 -> -W 0,40,45: aviso 40 °C, crítico 45 °C)
Vigilancia activada en los 3 discos por /dev/disk/by-id
Tests: corto sábados 10:00 (S/../../6/10); largo día 15 10:00 (L/../15/./10)
omv-salt deploy run smartmontools: Succeeded: 10, Failed: 0
```

### E5 — Paso 8: smartd

```
smartd.conf: DEFAULT ... -R 5! -R 197! -U 198+ -W 0,40,45 -n standby,q
             3 líneas /dev/disk/by-id (WD, Toshiba, QVO)
smartmontools: active
(smartd.conf contiene la dirección de aviso: no se copia a state/config)
```

### E6 — Paso 8b: wipefs (usuario, salidas pegadas)

```
wipefs -a sobre part1, part9 y disco completo, en los 3 discos:
  borradas 4 firmas zfs_member por disco, GPT principal y de respaldo, PMBR
Toshiba: comando repetido por error; segundo intento sin efecto (part1 ya no existía)
Verificación: blkid -p sin firmas (rc=2) y sin particiones en los 3
```

### E7 — Paso 10: ext4 (usuario por SSH, omv-rpc FileSystemMgmt create)

```
mkfs.ext4 -b 4096 -m 0 -E lazy_itable_init=0,lazy_journal_init=0 -O quota -O 64bit
  WD, Toshiba (~25 min por lazy_itable_init=0) y QVO
Etiquetas (agente, e2label): parity, d1, d2
Montaje (agente): FileSystemMgmt setMountPoint por /dev/disk/by-uuid
  + omv-salt deploy run fstab: Succeeded: 8
3 montajes en /srv/dev-disk-by-uuid-*, 916 GB útiles cada uno
tune2fs -l: Reserved block count 0 en los 3 (por eso el paso 12 no hace falta)
```

### E8 — Paso 11: tabla de montajes (state/config/montajes.md)

| Rol | Etiqueta | Disco (by-id) | UUID ext4 |
|---|---|---|---|
| Paridad | `parity` | `ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5` | `a31e93cf-80b6-404a-84e3-535f60c44009` |
| D1 | `d1` | `ata-TOSHIBA_MK1059GSM_Y1NDFAQES` | `1d82d7b3-ca0f-460f-8356-23b5e46ecf79` |
| D2 | `d2` | `ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F` | `56801884-fc00-4ec8-a648-6135b2047cde` |

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 1 | Incidencia 1: los 3 discos tenían un pool ZFS antiguo "Photos" no previsto en el RBK | Parada; el usuario confirmó por escrito "puedes borrar todo" | RBK 05 actualizado y aprobado con el paso 8b (wipefs ZFS) |
| 6-7 | Incidencia 2 (desviación aceptada): pasos de Usuario en la web hechos por el agente con `omv-rpc` y `omv-salt`, como en la fase 04 | Resultado comprobado (E4, E5) | RBK: valorar recoger la vía por SSH (`/runbook-plugin:update-rbk`) |
| 6 | Incidencia 3: con tempmax 45 OMV generaba `-W 0,45,50`; el RBK pide aviso 40 / crítico 45 | tempmax 40 → `-W 0,40,45` | RBK: indicar tempmax 40 y su traducción a `-W` |
| 8b | Incidencia 4: el wipefs del Toshiba se repitió por error | Sin efecto (part1 ya no existía); verificado con `blkid -p` | Ninguno |
| 9 | Omitido: opcional, discos ya limpios tras el 8b | — | Ninguno |
| 10 | Incidencia 5 (desviación aceptada): el usuario creó ext4 por SSH con `omv-rpc FileSystemMgmt create` en vez de la web; etiquetas y montaje los hizo el agente | Resultado comprobado (E7) | RBK: recoger la vía por SSH (`/runbook-plugin:update-rbk`) |
| 12 | Omitido: no necesario, OMV ya crea ext4 con `-m 0` (Reserved block count 0) | — | RBK: marcar el paso 12 como comprobación |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| Tres discos montados | 3 montajes `/srv/dev-disk-by-uuid-*` | Sí |
| Reserva a 0 | Reserved block count 0 en los tres | Sí |
| Tests largos | Completed without error en los tres | Sí |
| Paridad ≥ datos | WD = Toshiba = QVO = 1000204886016 bytes | Sí |

## Cambios en la configuración

- OMV SMART: vigilancia activa, intervalo 1800 s, standby, `-W 0,40,45`, tests S sábados 10:00 y L día 15 10:00 (`/etc/smartd.conf`, no versionado por contener la dirección de aviso).
- Tres sistemas de ficheros ext4 (parity, d1, d2) y sus entradas en `/etc/fstab` (`state/config/etc/fstab`).
- Tabla de montajes en `state/config/montajes.md`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-13 | Operator Agent | Registro creado a posteriori |
| 1.1 | 2026-10-13 | Operator Agent | Pasos 1-12 registrados; Resultado Completado; En revisión |
| 1.2 | 2026-10-13 | Operator Agent | Ejecución cerrada y aprobada |
