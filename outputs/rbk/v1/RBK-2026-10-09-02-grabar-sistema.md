# RBK 02 — Grabar el sistema en el SSD

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 02 — Grabar el sistema en el SSD |
| **Versión** | 1.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v1 (1.1, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Destructivo |
| **Duración estimada** | 45 min |

## Objetivo

Grabar Raspberry Pi OS Lite 64-bit (Trixie) en el SSD Toshiba XG5 desde el PC con Raspberry Pi
Imager 2.x, con equipo `nas`, usuario propio, SSH con contraseña, sin WiFi y sin Raspberry Pi
Connect (HLD §3, ADR-002).

## Prerrequisitos

- [ ] RBK 01 completado
- [ ] PC con Windows o Linux y conexión a Internet
- [ ] Usuario y contraseña de la Pi creados en el gestor de contraseñas (el nombre de usuario no es `pi`)

## Pasos

### Paso 1: Instalar Raspberry Pi Imager 2.x

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3 (guía §2.1) |

Descarga desde https://www.raspberrypi.com/software/ (fuente oficial).

Esperado: Imager con versión 2.x o superior (Ayuda → Acerca de). Las 1.x no ofrecen Trixie.

Si falla: en Linux, si la AppImage no abre, instala `libfuse2t64`; si la personalización falla con una 2.0.x, instala la última versión.

### Paso 2: Identificar el XG5 en el PC

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §2, §3 |

Comando:

```bash
# Linux
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN
# Windows (PowerShell)
Get-Disk | Format-Table Number,FriendlyName,SerialNumber,Size,BusType
```

Ejecuta el comando antes y después de conectar el XG5 por su caja USB.

Esperado: un disco de ~512 GB por USB (TRAN `usb` o BusType `USB`) que no estaba antes de conectar el XG5. Anota su modelo y serie en el OPS.

Si falla: si aparecen dos discos de tamaño parecido, desconecta todo lo USB salvo el XG5 y repite.

### Paso 3: Grabar Raspberry Pi OS Lite (64-bit) en el XG5

| Campo | Valor |
|---|---|
| **Riesgo** | Destructivo |
| **Ejecuta** | Usuario |
| **Dónde** | PC |
| **HLD** | §3 |

Comprobación previa:

```bash
lsblk -o NAME,SIZE,MODEL,SERIAL,TRAN     # Linux
Get-Disk | Format-Table Number,FriendlyName,SerialNumber,Size,BusType   # Windows
```

El almacenamiento que elijas en Imager debe tener el tamaño (~512 GB) y modelo del paso 2.

En Imager: Dispositivo → **Raspberry Pi 5**; Sistema → **Raspberry Pi OS (other) →
Raspberry Pi OS Lite (64-bit)**; Almacenamiento → el XG5. Personalización: equipo `nas`; zona
horaria y teclado los de casa; usuario propio (no `pi`) con la contraseña del gestor de
contraseñas; WiFi vacío; SSH activado con contraseña; Raspberry Pi Connect desactivado.
Pulsa Escribir.

Esperado: Imager termina con «Escritura correcta» tras la verificación. El XG5 queda con las particiones `bootfs` y `rootfs`.

Si falla: si se eligió otro disco, para: no escribas nada más en él y restaura desde tu backup del PC. Si la verificación falla, cambia de cable o de puerto USB y repite.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Particiones | `lsblk -o NAME,SIZE,LABEL (en el PC)` | `bootfs` y `rootfs` en el XG5 |

## Vuelta atrás

El XG5 se puede volver a grabar desde el paso 3. Si se borró otro disco del PC por error, restaurar desde la copia del PC.

## Evidencias

- Modelo, serie y tamaño del XG5 en el OPS
- Capturas 2.1 y 2.2 (sin contraseñas) en el OPS

## Preguntas abiertas

Ninguna.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 1.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
