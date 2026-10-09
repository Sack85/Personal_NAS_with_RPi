# Foto de la configuración del NAS

| Campo | Valor |
|---|---|
| Fecha | 2026-10-09 |
| Sistema | Debian 13 (trixie), kernel 6.18.50+rpt-rpi-2712 |
| OMV | sin instalar (fase 04 pendiente) |
| EEPROM | bootloader 2025-05-08, BOOT_ORDER=0xf41 (leído con `rpi-eeprom-config`) |

Ficheros copiados:
- `boot/firmware/config.txt`
- `etc/fstab`
- `etc/ssh/sshd_config.d/10-sin-contrasena.conf`

hd-idle, SnapRAID, NUT y compose de AIO aún no existen.
