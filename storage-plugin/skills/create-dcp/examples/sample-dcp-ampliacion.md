# DCP — Sustituir D1 (Toshiba, degradándose) por un disco de 2 TB

| Campo | Valor |
|---|---|
| **Documento** | DCP |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-12-04 |
| **Última modificación** | 2026-12-04 |
| **Autor** | Storage Agent |
| **Entregable previo** | HLD v1 (1.0, Aprobado) — HLD-2026-10-10-nas-familiar.md |
| **Escenario** | Sustitución preventiva |
| **Disco afectado** | D1 — Toshiba MK1059 1 TB, serie Z0XXXXXXX |
| **Disco nuevo** | WD Red Plus 2 TB (mayor que la paridad de 1 TB: pasa a ser la paridad) |
| **Inventario** | state/inventory/2026-12-01.yaml |
| **Riesgo máximo** | Destructivo |

## Resumen

D1 reasigna sectores (atributo 5 de 0 a 8 y 197 de 0 a 2 en un mes). Se sustituye antes de que
falle. Como el disco nuevo (2 TB) es mayor que la paridad actual (1 TB), **el nuevo pasa a ser la
paridad** y el WD Blue de 1 TB que era paridad pasa a ser D1; así la paridad sigue siendo ≥ que
cualquier disco de datos y el pool podrá crecer en el futuro con discos de hasta 2 TB.

## Diagnóstico

- `tools/inventory_diff.py` (2026-11-01 → 2026-12-01): D1 atributo 5 crece 0 → 8, 197 crece
  0 → 2; 193 sube 222/día; temperatura 41 °C.
- `snapraid smart` estima para D1 una probabilidad de fallo anual alta.
- D1 contiene unos 520 GB; el WD Blue tiene 1 TB: cabe con margen.
- Último backup restic: 2026-12-03 (hecho como acción del MNT de diciembre).

## Situación de partida

| Rol | Disco | Tamaño | Estado |
|---|---|---|---|
| Paridad | WD Blue | 1 TB | Bien |
| D1 | Toshiba MK1059 | 1 TB | Degradándose |
| D2 | Samsung 870 QVO | 1 TB | Bien |

## Situación final

| Rol | Disco | Tamaño | Sistema de ficheros | En pool | Content |
|---|---|---|---|---|---|
| Sistema | Toshiba XG5 | 512 GB | ext4 | No | Sí |
| Paridad | WD Red Plus | 2 TB | ext4 (0 % reservado) | No | No |
| D1 | WD Blue | 1 TB | ext4 | Sí | Sí |
| D2 | Samsung 870 QVO | 1 TB | ext4 | Sí | Sí |

## Precondiciones

- [ ] Backup restic de Documentos, Fotos y nextcloud-aio-backup de menos de 7 días (2026-12-03)
- [ ] `snapraid status` sin errores y sync de esta noche correcto
- [ ] Sync programado de SnapRAID desactivado durante todo el cambio (paso 1)
- [ ] Disco nuevo instalado en la bahía libre (2) con SMART largo sin errores

## Pasos

### Paso 1: Desactivar el sync programado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Servicios → SnapRAID → Programación → desactivar → Guardar y aplicar.

Esperado: la tarea de las 04:00 desactivada.

Si falla: no sigas; un sync a mitad del cambio deja la paridad incoherente.

### Paso 2: Instalar e identificar el disco nuevo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |

Apaga el NAS desde OMV, desenchufa los 12 V, instala el WD Red Plus en la bahía 2 y arranca.
Después el agente comprueba:

```bash
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; sudo smartctl -i -H /dev/disk/by-id/ata-WDC_WD20EFPX*'
```

Esperado: cinco dispositivos; el WD Red Plus de 2 TB con SMART `PASSED`. Anota su serie.

Si falla: si no aparece, revisa la bahía y el FFC; si SMART no pasa, se devuelve.

### Paso 3: Test SMART largo del disco nuevo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo smartctl -t long /dev/disk/by-id/ata-WDC_WD20EFPX*'
```

Esperado: tras unas 4 h, `smartctl -l selftest` muestra `Completed without error`.

Si falla: con errores no se usa el disco.

### Paso 4: Formatear el disco nuevo y quitar la reserva

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV y NAS por SSH |

Comprobación previa:

```bash
ssh nas lsblk -d -o NAME,SIZE,MODEL,SERIAL
```

Confirma modelo WD Red Plus, 2 TB y la serie del paso 2.

En OMV: Sistemas de archivos → Crear y montar → EXT4 → el WD Red Plus. Después, en la sesión
SSH, con la partición confirmada:

Comando:

```bash
sudo tune2fs -m 0 /dev/sdX1
```

Esperado: montado en `/srv/dev-disk-by-uuid-…` y `Reserved block count: 0`.

Si falla: si se aplicó `-m 0` a otro disco, devuélvelo a 5 % con `sudo tune2fs -m 5`.

### Paso 5: Mover la paridad al disco nuevo

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Servicios → SnapRAID → Discos → editar `parity` → sistema de archivos del WD Red Plus
→ Guardar y aplicar.

Esperado: `grep '^parity' /etc/snapraid/omv-snapraid-*.conf` apunta al montaje del WD Red Plus.

Si falla: vuelve a poner `parity` en el WD Blue; su paridad sigue siendo válida.

### Paso 6: Crear la paridad nueva

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync'
```

Esperado: sync completo sin errores (varias horas: calcula la paridad entera).

Si falla: la paridad antigua del WD Blue sigue intacta; vuelve al paso 5 y repite.

### Paso 7: Liberar el WD Blue (antigua paridad)

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

Comprobación previa:

```bash
ssh nas "lsblk -d -o NAME,SIZE,MODEL,SERIAL; grep '^parity' /etc/snapraid/omv-snapraid-*.conf"
```

Confirma que la paridad ya está en el WD Red Plus y que el disco a borrar es el WD Blue (serie
WD-WCC6Y0XXXXXX).

En OMV: desmontar el sistema de archivos del WD Blue → Discos → Borrar → Rápido → Sistemas de
archivos → Crear y montar → EXT4.

Esperado: el WD Blue vacío, montado en un `/srv/dev-disk-by-uuid-…` nuevo.

Si falla: si se borró otro disco, para y no escribas nada; avisa al experto en discos.

### Paso 8: Copiar los datos de D1 al WD Blue

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo rsync -aHAX --info=progress2 /srv/dev-disk-by-uuid-TOSHIBA/ /srv/dev-disk-by-uuid-WDBLUE/'
```

Sustituye las dos rutas por los montajes reales (Toshiba origen, WD Blue destino).

Esperado: rsync termina con código 0; `du -s` igual en ambos.

Si falla: el Toshiba no se ha modificado; repite rsync (es incremental).

### Paso 9: Cambiar d1 en SnapRAID y en MergerFS

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: SnapRAID → Discos → editar `d1` → sistema de archivos del WD Blue (mismo nombre `d1`,
datos y content) → aplicar. mergerfs → `pool` → sustituir la rama del Toshiba por la del WD Blue
→ aplicar.

Esperado: `grep '^data d1'` apunta al WD Blue y `findmnt /srv/mergerfs/pool` sigue montado.

Si falla: vuelve a poner el Toshiba como d1; sus datos siguen intactos.

### Paso 10: Comprobar y sincronizar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf diff; sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync'
```

Esperado: `diff` sin borrados masivos (los ficheros aparecen como movidos o iguales) y sync sin
errores.

Si falla: si `diff` muestra borrados, no sincronices: d1 no apunta al disco correcto.

### Paso 11: hd-idle, SMART y programación

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH y Web de OMV |

Edita `/etc/default/hd-idle` (`sudo nano /etc/default/hd-idle`): quita el Toshiba y añade el WD
Red Plus por su `/dev/disk/by-id/ata-WDC_WD20EFPX…` con `-i 2700`; mantén el WD Blue.
`sudo systemctl restart hd-idle`. En OMV: vigilancia SMART del WD Red Plus activada y la del
Toshiba quitada; reactivar la programación de SnapRAID.

Esperado: `systemctl status hd-idle` activo; tarea de las 04:00 activa.

Si falla: hd-idle mal configurado solo impide el spindown; corrige el fichero y reinicia el servicio.

### Paso 12: Retirar el Toshiba

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |

Apaga desde OMV, saca el Toshiba de la bahía 3, coloca el WD Red Plus (el que más calienta) en la
bahía con más aire si hace falta, y arranca. Guarda el Toshiba sin borrar 30 días como copia
extra.

Esperado: cuatro dispositivos y pool montado.

Si falla: vuelve a colocar los discos como estaban y revisa `lsblk`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| SnapRAID sano | `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'` | No error detected |
| Paridad en el disco de 2 TB | `ssh nas "grep '^parity' /etc/snapraid/omv-snapraid-*.conf"` | montaje del WD Red Plus |
| Pool con D1 y D2 | `ssh nas findmnt /srv/mergerfs/pool` | montado |
| Inventario posterior | `/maintainer-plugin:inventory` | sin alertas de discos |

## Vuelta atrás

Hasta el paso 7 la paridad del WD Blue sigue siendo válida y el Toshiba no se ha tocado: basta
con volver a poner `parity` en el WD Blue. Después del paso 7, el Toshiba conserva los datos de
D1 hasta el paso 12 y se guarda 30 días; si algo falla, se vuelve a poner como `d1` y se
recalcula la paridad.

## Cambios en el diseño

- HLD §5: paridad WD Red Plus 2 TB, D1 WD Blue 1 TB, Toshiba retirado; ADR nuevo
  ("paridad de 2 TB para poder crecer") → `/architect-plugin:update-hld`.
- SnapRAID: `parity` y `d1` con montajes nuevos; content en D1, D2 y SSD.
- MergerFS: rama del Toshiba sustituida por la del WD Blue.
- hd-idle: Toshiba fuera, WD Red Plus dentro.
- SMART: vigilancia del WD Red Plus activada.
- `state/config/` con `/operator-plugin:snapshot-config`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-12-04 | Storage Agent | Creación |
