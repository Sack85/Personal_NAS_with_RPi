# Foto de la configuración del NAS

| Campo | Valor |
|---|---|
| Fecha | 2026-10-13 |
| Sistema | Debian 13 (trixie), kernel 6.18.50+rpt-rpi-2712 |
| OMV | 8.5.11-1 (web en :8000; plugins snapraid, mergerfs, sharerootfs, compose) |
| EEPROM | bootloader 2025-05-08, BOOT_ORDER=0xf41 (leído con `rpi-eeprom-config`) |

Ficheros copiados:
- `boot/firmware/config.txt`
- `etc/fstab`
- `etc/ssh/sshd_config.d/10-sin-contrasena.conf`

hd-idle, SnapRAID, NUT y compose de AIO aún no existen.
- `etc/netplan/10-openmediavault-default.yaml`, `etc/netplan/20-openmediavault-eth0.yaml` (red de OMV; interfaz `end0` casada por MAC)
- `etc/systemd/system/systemd-networkd-wait-online.service.d/any.conf`
- `etc/ssh/sshd_config` (generado por OMV desde Servicios → SSH; no editar a mano)
