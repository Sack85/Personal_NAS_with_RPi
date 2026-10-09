# OPS — Ejecución de los RBK 01, 02 y 03 (montaje, grabación del sistema y primer arranque con el HAT)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v1 (1.0, Aprobado) — RBK-2026-10-09-01-material-montaje.md, RBK-2026-10-09-02-grabar-sistema.md, RBK-2026-10-09-03-primer-arranque-hat.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-09 |
| **Fin** | 2026-10-09 17:35 |

> Resultado: **Completado con incidencias** (3 incidencias corregidas durante la ejecución, los pasos 3 (reserva DHCP, aplazada) y 9 (EEPROM) del RBK 03 se omitieron por decisión del usuario y quedan 3 pendientes del usuario; ver Incidencias).
> Registro hecho a posteriori: la ejecución la hizo el usuario hoy y el agente solo repitió lecturas de verificación por `ssh nas` a las 17:34.

## Alcance

Un único OPS para las tres primeras fases (01 material y montaje, 02 grabar el sistema en el XG5,
03 primer arranque, HAT a PCIe Gen 3, EEPROM y discos). Las fases 01 y 02 se hicieron en físico y
en el PC; la 03, en el PC y por SSH. Ningún paso destructivo sobre los discos de datos.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 01, 02 y 03 aprobados y revalidados | Sí, 0 CRITICAL en `validate_rbk.py` |
| Prerrequisitos en `state/applied.yaml` | Vacío (son las primeras fases; no hay prerrequisitos aplicados) |
| Material | Pi 5, Radxa Penta SATA HAT, XG5 512 GB, 3 discos de 1 TB; disco USB de 4 TB **aún no comprado** |
| Pasos destructivos | Ninguno sobre datos (el XG5 se graba con Imager, vacío) |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| RBK01 1. Comprobar el material contra el HLD | Lectura | Usuario | — | OK | E1 |
| RBK01 2. Anotar modelo y serie de cada disco | Lectura | Usuario | — | OK | E10 |
| RBK01 3. Montar la Pi, el Active Cooler y el HAT | Cambio | Usuario | — | OK | E1 |
| RBK01 4. Colocar los discos en sus bahías | Cambio | Usuario | — | OK | E1 |
| RBK01 5. Montar el ventilador y el filtro | Cambio | Usuario | — | OK | E1 |
| RBK01 6. Ubicar el NAS | Cambio | Usuario | — | OK | E1 |
| RBK02 1. Instalar Raspberry Pi Imager 2.x | Cambio | Usuario | — | OK | E2 |
| RBK02 2. Identificar el XG5 en el PC | Lectura | Usuario | — | OK | E2 |
| RBK02 3. Grabar Raspberry Pi OS Lite (64-bit) en el XG5 | Cambio | Usuario | — | OK | E2 |
| RBK03 1. Añadir las líneas del HAT a config.txt | Cambio | Usuario | — | OK | E3 |
| RBK03 2. Arrancar sin discos y alimentado por el HAT | Cambio | Usuario | — | OK | E4 |
| RBK03 3. Reserva DHCP para nas en el router | Cambio | Usuario | — | Omitido | E4 |
| RBK03 4. Primera conexión SSH y alias nas en el PC | Cambio | Usuario | — | OK | E4 |
| RBK03 5. Comprobar sistema, zona horaria y config.txt | Lectura | Agente | — | OK | E5 |
| RBK03 6. Actualizar el sistema y reiniciar | Cambio | Agente | — | OK | E6 |
| RBK03 7. Comprobar el JMB585 a PCIe Gen 3 | Lectura | Agente | 17:34 | OK | E7 |
| RBK03 8. Leer la configuración de la EEPROM | Lectura | Agente | — | OK | E8 |
| RBK03 9. Orden de arranque con USB primero y PSU_MAX_CURRENT | Cambio | Usuario | — | Omitido | E9 |
| RBK03 10. Conectar los tres discos | Cambio | Usuario | — | OK | E1 |
| RBK03 11. Comprobar los cuatro dispositivos | Lectura | Agente | 17:34 | OK | E10 |
| RBK03 v2 6. SSH solo con clave (paso adicional) | Cambio | Agente | — | OK | E11 |

## Evidencias

### E1 — Montaje físico (RBK 01 y RBK 03 paso 10)

```
Montado por el usuario en estructura de latón con metacrilato; ventilador arriba.
Discos conectados al HAT ya en el montaje (se adelantó el paso 10 del RBK 03; sin impacto).
Bahías: NO verificadas por el usuario contra la tabla del HLD.
Disco USB de 4 TB (backup): aún no comprado; necesario antes del RBK 11.
```

### E2 — Grabación (RBK 02)

```
Raspberry Pi Imager → Raspberry Pi OS Lite (64-bit) en el XG5
Personalización: hostname nas, usuario nas, SSH con contraseña (contraseña en el gestor de contraseñas)
Serie del XG5 leída después con lsblk (78EB616DKAWP), no en el PC
```

### E3 — config.txt (verificado por SSH a las 17:34)

```
[all]
dtparam=pciex1
dtparam=pciex1_gen=3
dtoverlay=pcie-32bit-dma-pi5
usb_max_current_enable=1
```

### E4 — Arranque, red y SSH

```
IP recibida: 192.168.1.11 (no la .200 del HLD); MAC d8:3a:dd:a4:c5:c3
~/.ssh/config: Host nas → HostName 192.168.1.11, User nas
Reserva DHCP en la box: pendiente (usuario)
```

### E5 — Sistema

```
Debian GNU/Linux 13 (trixie), aarch64, kernel 6.18.50+rpt-rpi-2712
Time zone: Indian/Reunion, System clock synchronized: yes
sudo sin contraseña para nas: /etc/sudoers.d/010-nas-nopasswd (presente, verificado 17:34)
```

### E6 — Actualización

```
apt update && apt full-upgrade (incluye xz-utils, entre otros) → OK; reboot → OK
```

### E7 — PCIe y temperatura (verificado 17:34)

```
JMB58x en 0001:01:00.0
LnkSta: Speed 8GT/s, Width x1 (downgraded)   ← x1 es lo esperado en la Pi 5
throttled=0x0
temp=43.9'C
```

### E8 — EEPROM

```
BOOTLOADER: 2025/05/08
BOOT_ORDER=0xf41
PSU_MAX_CURRENT: no definido
```

### E9 — Paso 9 omitido

```
nano no guardó los cambios.
rpi-eeprom-config --apply dejó pieeprom.upd (2026-09-25) en /boot/firmware,
pero no se aplicó al reiniciar:
  - /dev/spidev10.0 no existe (dtoverlay=nospi10)
  - recovery.bin no se aplicó arrancando desde USB (causa no confirmada)
Decisión del usuario: se deja BOOT_ORDER=0xf41 (ya arranca por USB sin SD)
y usb_max_current_enable=1 en config.txt cubre la corriente USB.
Alternativa futura: SD con Imager → Bootloader → USB Boot.
```

### E10 — Dispositivos (lsblk tras la ejecución y de nuevo a las 17:34)

```
Durante la ejecución:
sda  476.9G KXG50ZNV512G (XG5)       78EB616DKAWP     usb
sdb  931.5G TOSHIBA MK1059GSM        Y1NDFAQES        sata
sdc  931.5G WDC WD10JPVX-60JC3T1     WD-WXU1EB6APMW5  sata
sdd  931.5G Samsung SSD 870 QVO 1TB  S5SVNG0N868475F  sata

Verificación 17:34 (tras otro arranque; las letras cambiaron):
sda  TOSHIBA Y1NDFAQES · sdb WDC WD-WXU1EB6APMW5 · sdc XG5 78EB616DKAWP (usb) · sdd QVO S5SVNG0N868475F
blockdev --getsize64: Toshiba 1000204886016, WD 1000204886016, QVO 1000204886016
→ los tres discos tienen el mismo tamaño en bytes: la paridad en el WD es válida.
```

### E11 — SSH solo con clave (RBK 03 v2, paso 6; paso adicional)

```
/etc/ssh/sshd_config.d/10-sin-contrasena.conf:
  PasswordAuthentication no
  KbdInteractiveAuthentication no
sshd -t → OK; systemctl reload ssh → OK
ssh nas hostname → nas (con clave)
Login por contraseña → "Permission denied (publickey)"
Comprobado: /boot/firmware/pieeprom.upd y recovery.bin ya no existen.
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| RBK03 2 | SSD conectado al USB-C de la Pi (solo alimentación): no arrancaba | Movido al USB-A azul (USB 3); arranca | `/runbook-plugin:update-rbk` RBK 03: advertir que el USB-C no sirve para datos |
| RBK03 3/4 | La Pi recibió 192.168.1.11, no la .200 del HLD | Alias `ssh nas` apuntado a .11 | Usuario: reserva DHCP en la box (MAC d8:3a:dd:a4:c5:c3); decidir .11 o .200 y alinear HLD/alias |
| RBK03 4 | `~/.ssh/config` con bloque duplicado y `<IP>` literal por pegar mal | Corregido a un único bloque `Host nas` | RBK 03: dar el bloque ya con un solo valor a sustituir |
| RBK03 5 | Decisión del usuario: sudo sin contraseña para `nas` | `/etc/sudoers.d/010-nas-nopasswd`; el guard sigue pidiendo confirmación | Reflejar en HLD (seguridad) con `/architect-plugin:update-hld` |
| RBK03 9 | EEPROM no actualizada (nano no guardó; `pieeprom.upd` no aplicado; spidev10.0 ausente por nospi10) | Omitido por decisión del usuario; queda 0xf41 + `usb_max_current_enable=1` | RBK 03: alternativa con SD y Imager → Bootloader USB Boot; borrar `pieeprom.upd` pendiente si no se usa |
| RBK01 4 | Bahías no verificadas contra el HLD | — | Usuario: comprobar antes del RBK 05 |
| RBK01 1 | Disco USB de 4 TB no comprado | — | Usuario: comprarlo antes del RBK 11 |
| RBK03 10 | Discos conectados en el montaje (paso adelantado) | Sin impacto | — |

> Seguimiento aplicado: las incidencias de los RBK se corrigieron en `outputs/rbk/v2/` y las del diseño (sudo sin contraseña, IP, EEPROM) en `outputs/hld/v2/`. El paso 6 del RBK 03 v2 (SSH solo con clave) se ejecutó como paso adicional (E11).

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| JMB585 a Gen 3 | Speed 8GT/s, Width x1 | Sí |
| Sin throttling | throttled=0x0 | Sí |
| Discos SATA | 3 (Toshiba, WD, QVO) | Sí |
| Alias SSH | `ssh nas hostname` → nas | Sí |
| SSH solo con clave | contraseña → Permission denied (publickey) | Sí |

## Cambios en la configuración

- `/boot/firmware/config.txt`: 4 líneas tras `[all]` (pciex1, pciex1_gen=3, pcie-32bit-dma-pi5, usb_max_current_enable=1).
- `/etc/sudoers.d/010-nas-nopasswd`: sudo sin contraseña para `nas`.
- Sistema actualizado con `apt full-upgrade`.
- `/boot/firmware/pieeprom.upd` presente sin aplicar; EEPROM sin cambios (BOOT_ORDER=0xf41). Actualización 1.1: `pieeprom.upd` y `recovery.bin` ya no existen (comprobado).
- `/etc/ssh/sshd_config.d/10-sin-contrasena.conf`: SSH solo con clave (RBK 03 v2 paso 6).
- PC: `~/.ssh/config` con `Host nas` → 192.168.1.11.
- Pendiente: `/operator-plugin:snapshot-config` para copiar config.txt a `state/config/`.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Operator Agent | Registro a posteriori de la ejecución de los RBK 01, 02 y 03 |
| 1.1 | 2026-10-09 | Operator Agent | Añadida evidencia E11 (RBK 03 v2 paso 6, SSH solo con clave), comprobación de pieeprom.upd/recovery.bin y referencia a RBK v2 y HLD v2; pasa a En revisión |
| 1.2 | 2026-10-09 | Operator Agent | Ejecución cerrada y aprobada (Completado con incidencias aceptadas por el usuario) |
