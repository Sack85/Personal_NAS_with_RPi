# RBK 05 — Discos: revisión SMART y formateo

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 05 — Discos: revisión SMART y formateo |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-12 |
| **Última modificación** | 2026-10-12 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.0, Aprobado) — HLD-2026-10-10-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 4 h (incluye 3 tests SMART largos en paralelo) |

## Objetivo

Comprobar la salud de los tres discos SATA, confirmar que el WD Blue puede ser la paridad y
dejar cada disco formateado en ext4 y montado por separado, con 0 % de bloques reservados en la
paridad (HLD §5).

## Prerrequisitos

- [ ] RBK 04 completado: OMV 8 accesible en `http://nas.local:8000` y avisos por correo probados
- [ ] Los datos que quieras conservar de los discos viejos están copiados fuera de ellos
- [ ] Sesión iniciada por el usuario en la web de OMV

## Pasos

### Paso 1: Identificar los discos

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 Almacenamiento |

Comando:

```bash
ssh nas lsblk -b -d -o NAME,SIZE,MODEL,SERIAL
```

Esperado: cuatro dispositivos: el XG5 (~512 GB, USB) y tres SATA de ~1 000 204 886 016 bytes
(WD, Toshiba MK1059 y Samsung QVO). Anota en el OPS la letra y el número de serie de cada uno.

Si falla: si falta un disco SATA, apaga (`sudo poweroff`), revisa el FFC y la bahía y vuelve a
arrancar; si sigue faltando, revisa `dmesg | grep -i ata` y para el runbook.

### Paso 2: Leer SMART de cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, ADR-003 |

Comando:

```bash
ssh nas 'for d in /dev/sda /dev/sdb /dev/sdc; do sudo smartctl -a "$d"; done'
```

Esperado: `SMART overall-health self-assessment test result: PASSED` en los tres; atributos 197
y 198 a 0 en el WD (paridad). Anota 5, 9, 193, 197, 198 y 199 de cada disco en el OPS.

Si falla: si el WD tiene 197 o 198 distintos de 0, para: la paridad debe cambiar de disco
(`/architect-plugin:update-hld`).

### Paso 3: Lanzar el test SMART largo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'for d in /dev/sda /dev/sdb /dev/sdc; do sudo smartctl -t long "$d"; done'
```

Esperado: "Testing has begun" en cada disco; tarda 2–3 h. Después,
`sudo smartctl -l selftest /dev/sdX` muestra `Completed without error`.

Si falla: un test con `read failure` descarta ese disco; registra el resultado en el OPS y para.

### Paso 4: Borrar los tres discos SATA

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 |

Comprobación previa:

```bash
ssh nas lsblk -d -o NAME,SIZE,MODEL,SERIAL
```

Compara modelo y número de serie con los anotados en el paso 1. El XG5 del sistema no se toca.

En OMV: Almacenamiento → Discos → seleccionar cada disco SATA → Borrar → Rápido. Uno cada vez,
comprobando el número de serie en la ventana antes de confirmar.

Esperado: los tres discos sin particiones (`lsblk` no muestra `sdX1`).

Si falla: si se borró el disco equivocado, para y no formatees nada; los datos pueden
recuperarse con herramientas de recuperación mientras no se escriba en él.

### Paso 5: Crear y montar ext4 en cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |
| **HLD** | §5 |

Comprobación previa:

```bash
ssh nas lsblk -d -o NAME,SIZE,MODEL,SERIAL
```

En OMV: Almacenamiento → Sistemas de archivos → Crear y montar → EXT4, un disco cada vez.

Esperado: tres sistemas de archivos montados en `/srv/dev-disk-by-uuid-…`.

Si falla: si OMV no monta, revisa `dmesg` y repite la creación solo en ese disco.

### Paso 6: Anotar qué montaje es cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comando:

```bash
ssh nas 'findmnt -rn -o SOURCE,TARGET | grep /srv/dev-disk-by-uuid; ls -l /dev/disk/by-uuid/'
```

Esperado: un montaje por disco; anota en el OPS la tabla Rol → disco → UUID → montaje y guarda
la salida en `state/config/`.

Si falla: si falta un montaje, vuelve al paso 5 para ese disco.

### Paso 7: Bloques reservados a 0 en la paridad

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |
| **HLD** | §5 (ext4 con 0 % reservado) |

Comprobación previa:

```bash
ssh nas "sudo tune2fs -l /dev/sdX1 | grep 'Reserved block count'"
```

Sustituye `sdX1` por la partición del WD según el paso 6. Si ya es 0, salta este paso.

Comando:

```bash
sudo tune2fs -m 0 /dev/sdX1
```

Esperado: `Setting reserved blocks percentage to 0%`; la comprobación previa repetida da 0.

Si falla: si se aplicó a un disco de datos, vuelve a dejarlo en 5 % con `sudo tune2fs -m 5`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Tres discos montados | `ssh nas findmnt -rn -o TARGET \| grep -c dev-disk-by-uuid` | 3 |
| Paridad sin reserva | `ssh nas "sudo tune2fs -l /dev/sdX1 \| grep 'Reserved block count'"` | 0 |
| Tests largos sin error | `ssh nas sudo smartctl -l selftest /dev/sdX` | Completed without error |

## Vuelta atrás

Hasta el paso 3 no se ha cambiado nada. A partir del paso 4 los discos están borrados: la
vuelta atrás es restaurar desde la copia hecha en los prerrequisitos.

## Evidencias

- Salida de `lsblk -b -d -o NAME,SIZE,MODEL,SERIAL` (paso 1) en el OPS
- Atributos SMART 5, 9, 193, 197, 198 y 199 por disco (paso 2) en el OPS
- Tabla Rol → disco → UUID → montaje en `state/config/montajes.md` (paso 6)

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-12 | Runbook Agent | Creación |
