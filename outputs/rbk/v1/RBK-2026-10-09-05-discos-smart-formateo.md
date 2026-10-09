# RBK 05 — Discos: revisión SMART y formateo

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 05 — Discos: revisión SMART y formateo |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 5 h (incluye los tests SMART largos) |

## Objetivo

Comprobar la salud de los tres discos SATA, confirmar con `lsblk -b` que el WD Blue tiene al
menos tantos bytes como el Toshiba MK1059 (D1) y el Samsung QVO (D2) para ser la paridad,
activar la vigilancia SMART en modo Standby y dejar cada disco en ext4 con 0 % de bloques
reservados, montado por separado (HLD §5, ADR-001, ADR-003).

## Prerrequisitos

- [ ] RBK 04 completado: OMV en `http://nas.local:8000` y correo probado
- [ ] Datos de los discos viejos copiados fuera (RBK 01): los pasos 9 y 10 los borran
- [ ] Tabla Rol → modelo → serie del RBK 01 a mano
- [ ] Sesión iniciada por el usuario en la web de OMV

## Pasos

### Paso 1: Identificar los discos y sus bytes

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

Esperado: XG5 (`usb`) y tres `sata`: WD Blue, Toshiba MK1059 y Samsung QVO, con los números de serie del RBK 01. Anota en el OPS NAME, SIZE en bytes y SERIAL de cada uno.

Si falla: si falta un disco SATA, apaga, revisa bahía y FFC y repite; si sigue faltando, para.

### Paso 2: Comparar tamaños: la paridad debe ser la mayor o igual

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, ADR-003, §12 |

Comparación aritmética de los bytes del paso 1; no hay comando nuevo.

Esperado: SIZE(WD Blue) ≥ SIZE(Toshiba MK1059) y SIZE(WD Blue) ≥ SIZE(Samsung QVO), en bytes, con los valores del paso 1. Anota la comparación en el OPS.

Si falla: si el WD Blue tiene menos bytes que cualquiera de los otros dos, **para el runbook**: no se formatea nada y se vuelve al arquitecto (`/architect-plugin:update-hld`, riesgo «Tamaños sin verificar» del HLD §12).

### Paso 3: Leer SMART de cada disco SATA

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, ADR-003 |

Comando:

```bash
ssh nas 'sudo smartctl -a /dev/sdX'
```

Repite con la letra de cada disco SATA del paso 1.

Esperado: `PASSED` en los tres; atributos 197 y 198 a 0 en el WD Blue. Anota 5, 9, 193, 197, 198, 199 de cada disco y 177/241 del QVO en el OPS.

Si falla: si el WD Blue tiene 197 o 198 distintos de 0, para: la paridad debe cambiar de disco (`/architect-plugin:update-hld`). Si un disco de datos no da `PASSED`, para y llama a `/storage-plugin:diagnose-disk`.

### Paso 4: Lanzar el test SMART largo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'sudo smartctl -t long /dev/sdX'
```

Repite con cada disco SATA. Los tres pueden ir en paralelo.

Esperado: «Testing has begun» en cada disco; 2-3 h en los mecánicos de 1 TB, menos en el QVO.

Si falla: si un disco rechaza el test, anótalo y sigue con los demás; se decide en el paso 5.

### Paso 5: Leer el resultado del test largo

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'sudo smartctl -l selftest /dev/sdX'
```

Esperado: `Completed without error` en la primera línea del registro de cada disco.

Si falla: un `read failure` descarta el disco: para y llama a `/storage-plugin:diagnose-disk`.

### Paso 6: Activar la vigilancia SMART en OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §9 (temperatura), ADR-014 |

Esperado: Almacenamiento → S.M.A.R.T. → Configuración: activado, intervalo 1800 s, modo de energía **En espera** (Standby), temperatura informativa 40 °C y crítica 45 °C. En Dispositivos, vigilancia activada en los tres discos SATA. Aplicado.

Si falla: si la barra amarilla no aplica, revisa el registro en Diagnósticos → Registros del sistema.

### Paso 7: Programar los tests SMART

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §9, §10 |

Esperado: Pruebas programadas por disco SATA: corta cada sábado a las 10:00 y larga el día 15 de cada mes a las 10:00 (en horario de uso, fuera de 23:00-01:00).

Si falla: si OMV no acepta la programación, deja solo la corta semanal y anótalo como pregunta abierta.

### Paso 8: Comprobar smartd

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas "grep -v '^#' /etc/smartd.conf | grep -v '^$'"
```

Esperado: una línea por disco SATA con `-n standby` y los umbrales de temperatura 40 y 45 (`-W`).

Si falla: si falta `-n standby`, vuelve al paso 6: smartd despertaría los discos.

### Paso 9: Borrar los tres discos SATA

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 |

Comprobación previa:

```bash
ssh nas 'lsblk -b -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

Compara modelo y número de serie con los del paso 1. El disco `usb` (XG5) no se toca.

En OMV: Almacenamiento → Discos → cada disco SATA → Borrar → Rápido. Uno cada vez, leyendo el número de serie en la ventana antes de confirmar.

Esperado: los tres discos SATA sin particiones (`lsblk` no muestra `sdX1` bajo ellos). El XG5 intacto.

Si falla: si se borró el disco equivocado, para y no formatees nada; los datos se pueden recuperar con herramientas de recuperación mientras no se escriba en él.

### Paso 10: Crear y montar ext4 en cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 |

Comprobación previa:

```bash
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL,TRAN'
```

Compara serie y modelo con el paso 1 antes de cada creación.

En OMV: Almacenamiento → Sistemas de archivos → Crear y montar → EXT4, un disco cada vez, eligiéndolo por número de serie.

Esperado: tres sistemas de archivos ext4 montados en `/srv/dev-disk-by-uuid-…`.

Si falla: si OMV no monta uno, revisa `ssh nas 'sudo dmesg | tail -n 30'` y repite la creación solo en ese disco.

### Paso 11: Anotar qué montaje es cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'findmnt -rn -o SOURCE,TARGET | grep /srv/dev-disk-by-uuid; lsblk -o NAME,SERIAL,UUID,MOUNTPOINT'
```

Esperado: tres líneas `/dev/sdX1 /srv/dev-disk-by-uuid-…`. Tabla Rol (parity, d1, d2) → serie → UUID → montaje en el OPS y en `state/config/montajes.md`.

Si falla: si falta un montaje, vuelve al paso 10 para ese disco.

### Paso 12: Bloques reservados a 0 en paridad, D1 y D2

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §5 (ext4 con 0 % reservado) |

Comprobación previa:

```bash
ssh nas "sudo tune2fs -l /dev/disk/by-uuid/UUID | grep 'Reserved block count'"
```

Sustituye `UUID` por el de cada disco según el paso 11 (paridad, d1 y d2). Si ya es 0, salta ese disco.

Comando:

```bash
sudo tune2fs -m 0 /dev/disk/by-uuid/UUID
```

Esperado: `Setting reserved blocks percentage to 0%` en cada uno; la comprobación previa repetida da `Reserved block count: 0`.

Si falla: si se aplicó a una partición que no es de los tres discos SATA (por ejemplo la raíz del XG5), vuelve a dejarla en 5 % con `sudo tune2fs -m 5` sobre esa partición.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Tres discos montados | `ssh nas 'findmnt -rn -o TARGET \| grep -c dev-disk-by-uuid'` | 3 |
| Reserva a 0 | `ssh nas "sudo tune2fs -l /dev/disk/by-uuid/UUID \| grep 'Reserved block count'"` | 0 en los tres |
| Tests largos | `ssh nas 'sudo smartctl -l selftest /dev/sdX'` | Completed without error |
| Paridad ≥ datos | `tabla del paso 2` | WD Blue ≥ Toshiba y ≥ QVO en bytes |

## Vuelta atrás

Hasta el paso 8 no se ha borrado nada. Desde el paso 9 los discos están borrados: la vuelta
atrás es restaurar los datos copiados en los prerrequisitos. El paso 12 se revierte con
`sudo tune2fs -m 5` sobre el disco afectado.

## Evidencias

- `lsblk -b` y la comparación de bytes (pasos 1 y 2) en el OPS
- Atributos SMART 5, 9, 193, 197, 198, 199 (y 177/241 del QVO) por disco en el OPS
- Tabla Rol → serie → UUID → montaje en `state/config/montajes.md`
- Copia de `/etc/smartd.conf` en `state/config/`

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| Horario de los tests SMART programados (sábado 10:00 corta, día 15 10:00 larga): propuesta del runbook, no fijada en el HLD. ¿Se acepta? | Persona 1 | Antes de aprobar este RBK |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
