# UPD — Actualización de enero 2027: kernel y OpenMediaVault 8.1

| Campo | Valor |
|---|---|
| **Documento** | UPD |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2027-01-05 |
| **Última modificación** | 2027-01-05 |
| **Autor** | Maintainer Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-12-20-nas-familiar.md |
| **Inventario** | state/inventory/2027-01-05.yaml |
| **Inventario anterior** | state/inventory/2026-12-01.yaml |
| **Ventana** | Sábado 2027-01-09, 10:00–13:00 |
| **Riesgo máximo** | Cambio |

## Resumen

Hay un kernel nuevo de la Pi y OpenMediaVault 8.1. El kernel es el cambio con más riesgo para
este NAS (el HAT PCIe puede dejar de ver los discos), así que se actualiza en una ventana con
backup reciente y se comprueban los tres discos y el enlace PCIe antes de dar el NAS por bueno.
Nextcloud AIO ya se actualiza solo tras su backup diario y no entra en este plan.

## Cambios disponibles

| Componente | Versión actual | Versión nueva | Tipo | Fuente | Riesgo |
|---|---|---|---|---|---|
| linux-image-rpi-2712 | 6.12.47 | 6.12.55 | Seguridad | Notas de versión de Raspberry Pi OS (enlace en la sesión) | Alto |
| openmediavault | 8.0.12-1 | 8.1.0-1 | Menor | Changelog de openmediavault 8.1 (enlace en la sesión) | Medio |
| nextcloud-aio-mastercontainer | v11.6.1 | v11.6.3 | Menor | Actualización automática de AIO | Bajo |

## Impacto en el diseño

| Cambio | Afecta a (HLD) | Riesgo | Mitigación |
|---|---|---|---|
| Kernel nuevo | §3 Arranque (`pcie-32bit-dma-pi5`), §5 Almacenamiento | Los discos SATA desaparecen si el overlay falla | Comprobar config.txt antes; `lsblk` y `LnkSta` después |
| OMV 8.1 | §6 Servicios, §10 Actualizaciones | Un plugin incompatible deja la web sin cargar | Comprobar plugins tras actualizar; foto de configuración antes |

## Decisión

| Componente | Decisión | Motivo |
|---|---|---|
| Kernel 6.12.55 | Aplicar | Corrección de seguridad; overlay ya presente |
| OMV 8.1.0 | Aplicar | Sin cambios incompatibles en los plugins usados |
| AIO | No aplica | Se actualiza solo tras el backup diario |

## Precondiciones

- [ ] `snapraid status` sin errores y último sync de esta noche correcto
- [ ] Backup diario de AIO de esta noche correcto
- [ ] Backup restic al Hitachi de hace menos de 31 días
- [ ] SAI en `OL` y sin cortes previstos
- [ ] Sin alertas CRITICAL en `tools/inventory_diff.py` del inventario actual

## Pasos

### Paso 1: Comprobar precondiciones

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'sudo snapraid -c /etc/snapraid/omv-snapraid-*.conf status | tail -5; upsc ups@localhost ups.status'
```

Esperado: "No error detected" y `OL`.

Si falla: no se actualiza; se apunta en el OPS y se revisa SnapRAID o el SAI primero.

### Paso 2: Confirmar el overlay PCIe

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas "grep -E '^(dtparam=pciex1|dtoverlay=pcie-32bit-dma-pi5)' /boot/firmware/config.txt"
```

Esperado: las dos líneas presentes.

Si falla: no se actualiza el kernel; se corrige config.txt con el RBK 03 antes.

### Paso 3: Foto de la configuración

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | PC |

Invoca `/operator-plugin:snapshot-config` y haz commit de `state/config/`.

Esperado: `state/config/` al día con la fecha de hoy.

Si falla: sigue solo si el usuario lo acepta; sin foto, la vuelta atrás de OMV es más lenta.

### Paso 4: Aplicar las actualizaciones

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Web de OMV |

En OMV: Sistema → Gestión de actualizaciones → Comprobar → seleccionar `linux-image-rpi-2712` y
`openmediavault*` → Instalar. Esperar a "Done" sin errores.

Esperado: la lista de actualizaciones queda vacía para esos paquetes.

Si falla: copia el error en el OPS y no reinicies; se revisa con `ssh nas 'sudo apt-get -s -f install'`.

### Paso 5: Reiniciar

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas sudo reboot
```

Esperado: `ssh nas uptime` responde en menos de 3 minutos.

Si falla: si no vuelve en 10 minutos, conecta pantalla y teclado o revisa el LED de la Pi;
no desenchufes con los discos girando.

### Paso 6: Comprobar discos y servicios

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |

Comando:

```bash
ssh nas 'uname -r; lsblk -d -o NAME,SIZE,MODEL; sudo lspci -vv -d 197b: | grep LnkSta; systemctl is-active openmediavault-engined; findmnt /srv/mergerfs/pool; docker ps --format "{{.Names}}: {{.Status}}"'
```

Esperado: kernel 6.12.55, cuatro discos, `Speed 8GT/s`, `active`, pool montado y contenedores
de AIO `Up`.

Si falla: ver Vuelta atrás.

## Verificación posterior

| Comprobación | Comando | Esperado |
|---|---|---|
| Kernel nuevo | `ssh nas uname -r` | 6.12.55 |
| Discos visibles | `ssh nas lsblk -d -o NAME,SIZE,MODEL` | XG5 + tres SATA |
| Enlace PCIe | `ssh nas "sudo lspci -vv -d 197b: \| grep LnkSta"` | Speed 8GT/s |
| OMV | `ssh nas systemctl is-active openmediavault-engined` | active |
| Pool | `ssh nas findmnt /srv/mergerfs/pool` | montado |
| Inventario posterior | `/maintainer-plugin:inventory` | sin alertas nuevas en `tools/inventory_diff.py` |

## Vuelta atrás

- **Faltan discos tras el kernel nuevo**: comprueba que config.txt conserva las líneas del
  paso 2. Si están y siguen faltando, el usuario instala el kernel anterior desde la caché de
  apt (`ls /var/cache/apt/archives/linux-image-rpi-2712_6.12.47*`, luego `sudo dpkg -i` de ese
  fichero) y reinicia; se registra en el OPS y se abre una incidencia para el HLD.
- **La web de OMV no carga tras 8.1**: `sudo omv-firstaid` lo ejecuta el usuario y se compara la
  configuración con `state/config/`; si no se resuelve, se pide ayuda en el foro de OMV con el
  error exacto antes de tocar más.
- **AIO no arranca**: restaurar el backup de AIO de esta noche desde su panel.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2027-01-05 | Maintainer Agent | Creación |
