# DCP — D2 (Samsung QVO) ha muerto: reconstrucción con SnapRAID

| Campo | Valor |
|---|---|
| **Documento** | DCP |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2027-03-02 |
| **Última modificación** | 2027-03-02 |
| **Autor** | Storage Agent |
| **Entregable previo** | HLD v1 (1.0, Aprobado) — HLD-2026-10-10-nas-familiar.md |
| **Escenario** | Fallo de disco de datos |
| **Disco afectado** | D2 — Samsung 870 QVO 1 TB, serie S5XXXXXXXXXX |
| **Disco nuevo** | Samsung 870 EVO 1 TB (≥ disco muerto y ≤ paridad de 1 TB) |
| **Inventario** | state/inventory/2027-03-02.yaml |
| **Riesgo máximo** | Destructivo |

## Resumen

D2 ha desaparecido del sistema. Sus datos se reconstruyen desde la paridad del WD y D1 sobre un
disco nuevo de 1 TB, con el mismo nombre `d2` en SnapRAID. Lo más importante: **no puede
ejecutarse ningún sync** hasta terminar la reconstrucción, porque un sync con D2 vacío
sobrescribiría la paridad con la ausencia de sus datos.

## Diagnóstico

- `lsblk` ya no muestra el QVO; `dmesg` registra `ata3: link is slow to respond` y
  `I/O error` antes de desaparecer.
- `snapraid status` del último sync (04:15 de hoy) sin errores: la paridad es válida y contiene
  D2 tal como estaba a esa hora.
- Lo escrito en D2 después de las 04:15 no se puede reconstruir (RPO 24 h del NRD §5).
- Backup restic del 2027-02-05 contiene Documentos y Fotos como segunda vía.

## Situación de partida

| Rol | Disco | Tamaño | Estado |
|---|---|---|---|
| Paridad | WD Blue | 1 TB | Bien |
| D1 | Toshiba MK1059 | 1 TB | Bien |
| D2 | Samsung 870 QVO | 1 TB | Muerto (no detectado) |

## Situación final

| Rol | Disco | Tamaño | Sistema de ficheros | En pool | Content |
|---|---|---|---|---|---|
| Sistema | Toshiba XG5 | 512 GB | ext4 | No | Sí |
| Paridad | WD Blue | 1 TB | ext4 (0 % reservado) | No | No |
| D1 | Toshiba MK1059 | 1 TB | ext4 | Sí | Sí |
| D2 | Samsung 870 EVO | 1 TB | ext4 | Sí | Sí |

## Precondiciones

- [ ] Sync programado de SnapRAID desactivado antes de cualquier otro paso (paso 1)
- [ ] Nadie escribe en el pool durante la reconstrucción: avisar a la familia y pausar la subida automática de Nextcloud en los móviles
- [ ] Fecha del último backup restic anotada (2027-02-05) por si la reconstrucción falla
- [ ] Disco nuevo de 1 TB disponible y probado con SMART en otro equipo o tras instalarlo

## Pasos

### Paso 1: Desactivar el sync programado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Servicios → SnapRAID → Programación (diff/sync) → desactivar → Guardar y aplicar.

Esperado: la tarea de las 04:00 aparece desactivada.

Si falla: si no se puede desactivar, apaga el NAS hasta tener el disco nuevo; un sync con D2
ausente destruiría la posibilidad de reconstruirlo.

### Paso 2: Confirmar el estado sin tocar nada

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status | tail -8'
```

Esperado: tres discos (XG5, WD, Toshiba) y SnapRAID avisando de que falta d2.

Si falla: si D2 vuelve a aparecer, para: puede ser el cable o la bahía (atributo 199); se revisa
con `/storage-plugin:diagnose-disk` antes de cambiar nada.

### Paso 3: Cambiar el disco físicamente

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |

Apaga el NAS desde la web de OMV (o `sudo poweroff` en la sesión SSH), desenchufa los 12 V,
saca el QVO de la bahía 4 y pon el 870 EVO en la misma bahía. Arranca.

Esperado: el NAS arranca y responde a `ssh nas uptime`.

Si falla: si no arranca, quita el disco nuevo y arranca sin él para descartar el disco.

### Paso 4: Identificar el disco nuevo

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'lsblk -d -o NAME,SIZE,MODEL,SERIAL; sudo smartctl -i -H /dev/disk/by-id/ata-Samsung_SSD_870_EVO*'
```

Esperado: aparece el 870 EVO de 1 TB con su número de serie y SMART `PASSED`. Anota la letra.

Si falla: si SMART no es PASSED, no se usa: se devuelve el disco.

### Paso 5: Formatear el disco nuevo en ext4

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

Comprobación previa:

```bash
ssh nas lsblk -d -o NAME,SIZE,MODEL,SERIAL
```

Confirma que el disco a formatear es el 870 EVO con el número de serie del paso 4.

En OMV: Almacenamiento → Sistemas de archivos → Crear y montar → EXT4 → el 870 EVO.

Esperado: nuevo sistema de archivos montado en `/srv/dev-disk-by-uuid-…`.

Si falla: repite solo sobre ese disco tras revisar `dmesg`.

### Paso 6: Asignar el disco nuevo como d2 en SnapRAID y en MergerFS

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Servicios → SnapRAID → Discos → editar `d2` → nuevo sistema de archivos (mismo nombre
`d2`, datos y content activados) → Guardar y aplicar. Almacenamiento → mergerfs → `pool` →
sustituir la rama del QVO por la del 870 EVO → Guardar y aplicar.

Esperado: `grep '^data d2' /etc/snapraid/omv-snapraid-*.conf` apunta al montaje nuevo.

Si falla: no sigas al paso 7 hasta que d2 apunte al disco nuevo; un `fix` sobre otro disco
escribiría donde no debe.

### Paso 7: Reconstruir d2 desde la paridad

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | NAS por SSH |

Comprobación previa:

```bash
ssh nas "grep -E '^(data|parity|content)' /etc/snapraid/omv-snapraid-*.conf"
```

Confirma que `data d2` apunta al montaje del 870 EVO y que la paridad sigue en el WD.

Comando:

```bash
sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf -d d2 -l fix.log fix
```

Esperado: termina con "Everything OK" o con la lista de ficheros no recuperables en
`fix.log` (escritos después del último sync).

Si falla: si se interrumpe, se puede relanzar el mismo comando; no ejecutes `sync`.

### Paso 8: Verificar lo reconstruido

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf -d d2 -a check'
```

Esperado: sin errores; los ficheros de `fix.log` marcados como no recuperables se restauran
desde restic si son de Documentos o Fotos.

Si falla: relanza el paso 7 para los ficheros con error y vuelve a comprobar.

### Paso 9: Sincronizar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf sync'
```

Esperado: sync completo sin errores.

Si falla: revisa `snapraid status` y la salida del error antes de repetir.

### Paso 10: Reactivar el sync programado y la vigilancia SMART

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: reactivar la programación de SnapRAID; Almacenamiento → S.M.A.R.T. → Dispositivos →
activar la vigilancia del 870 EVO. Reanudar la subida automática en los móviles.

Esperado: tarea de las 04:00 activa y el disco nuevo vigilado.

Si falla: anótalo en el OPS; el NAS queda sin sync automático hasta corregirlo.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| SnapRAID sano | `ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status'` | No error detected |
| Pool montado con dos ramas | `ssh nas findmnt /srv/mergerfs/pool` | montado |
| Disco nuevo vigilado | `ssh nas sudo smartctl -H /dev/sdX` | PASSED |

## Vuelta atrás

Hasta el paso 7 no se ha escrito nada en la paridad ni en D1: si algo falla, se para con el
sync desactivado y el estado sigue siendo reconstruible. Si el `fix` no recupera ficheros
importantes, se restauran desde restic (Documentos y Fotos) a una carpeta nueva; Videos es
reemplazable (NRD §3).

## Cambios en el diseño

- HLD §5: D2 pasa a Samsung 870 EVO 1 TB → `/architect-plugin:update-hld`.
- SnapRAID: mismo nombre `d2`, nuevo montaje; content en el disco nuevo.
- MergerFS: rama del QVO sustituida por la del 870 EVO.
- hd-idle: sin cambios (los SSD no se paran).
- SMART: vigilancia activada para el disco nuevo.
- `state/config/` con `/operator-plugin:snapshot-config` al terminar.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2027-03-02 | Storage Agent | Creación |
