# OPS — Ejecución del UPD-2026-10-28 (apt completo e Immich 3.3.5)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-29 |
| **Última modificación** | 2026-10-29 |
| **Autor** | Operator Agent |
| **Entregable previo** | UPD v1 (1.0, Aprobado) — UPD-2026-10-28-apt-immich.md |
| **Resultado** | En curso |
| **Inicio** | 2026-10-28 23:45 |
| **Fin** | — |

## Alcance

Plan de actualización aprobado el 2026-10-28. Persona 1 aceptó expresamente que no hay backup
restic, ni SAI, y que el backup de AIO sigue desactivado (ADR-027). La vuelta atrás es la imagen
del SSD `D:\_nas_imagenes\nas-ssd-2026-10-28.img.gz`.

Persona 1 delegó en el agente el paso 5, que el UPD asignaba al usuario en la web de OMV («te dejo
hacer la actualización, yo me voy»). El agente lo ejecutó por SSH con `omv-upgrade`, que es la
orden de OMV equivalente.

El reinicio (paso 9) se aplaza hasta que persona 1 esté en casa: sin pantalla, nadie podría
recuperar la Pi si no arrancara. Además, el kernel no cambia.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| UPD aprobado | Sí |
| Imagen del SSD verificada | Sí: se descomprime a 512 110 190 592 bytes, el tamaño exacto del SSD |
| `snapraid status` | No error detected |
| Inventario | `state/inventory/2026-10-28.yaml` |
| Pasos destructivos | No |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Precondiciones y estado de partida | Lectura | Agente | 2026-10-28 23:40 | OK | E1 |
| 2. Sync de SnapRAID antes de actualizar | Cambio | Agente | 2026-10-28 23:50 | OK | E2 |
| 3. Foto de la configuración | Lectura | Agente | — | Pendiente | — |
| 4. Simular la actualización | Lectura | Agente | 2026-10-28 23:55 | OK | E3 |
| 5. Aplicar las actualizaciones de apt | Cambio | Agente | 2026-10-29 06:30 | OK | E4 |
| 6. sshd, Tailscale y EEPROM antes del reinicio | Lectura | Agente | 2026-10-29 06:45 | OK | E5 |
| 7. Subir Immich a v3.3.5 | Cambio | Agente | 2026-10-29 06:50 | OK | E6 |
| 8. Nextcloud AIO (panel) | Cambio | Usuario | — | Pendiente | — |
| 9. Reinicio | Cambio | Agente | — | Pendiente | — |
| 10. Discos, PCIe y servicios tras el reinicio | Lectura | Agente | — | Pendiente | — |
| 11. Inventario posterior y RBK 16 | Lectura | Agente | — | Pendiente | — |

## Evidencias

### E1 — Paso 1

```
snapraid status: No error detected; último sync 2026-10-20 23:37 (cuelgue del 21 al 28)
PCIe 8GT/s x1, throttled=0x0, 34 °C, pool 36 %
```

### E2 — Paso 2

```
snapraid diff: 226266 equal, 705 added, 0 removed, 2 updated
systemd-run --unit=snapraid-sync-upd ... sync → 100% completed, Everything OK
```

### E3 — Paso 4

```
apt-get -s full-upgrade: 36 Inst, 0 Remv, ningún linux-image
```

### E4 — Paso 5

```
systemd-run --unit=upd-omv-upgrade /usr/sbin/omv-upgrade → Result=success, ExecMainStatus=0
Setting up openmediavault (8.6.0-1); Setting up docker-ce (5:29.9.2-1~debian.13~trixie)
apt list --upgradable: 0
```

### E5 — Paso 6

```
sshd -T: passwordauthentication no
tailscale 1.104.4, HostName "nas"
ssh, nginx, caddy, docker, tailscaled, smbd, monit: active
rpi-eeprom-update: "update available" sin actualización programada (no se aplica, ADR-021)
OMV web: http://192.168.1.11:8000 → 200 (el puerto 80 está libre por Caddy, RBK 10)
Nextcloud status.php → 200; 11 contenedores healthy
```

### E6 — Paso 7

```
IMMICH_VERSION v3.3.3 → v3.3.5 con sed (repo env.sin-secretos y /srv/immich/compose/.env)
grep -c IMMICH_VERSION=v3.3.5 → 1; grep -c DB_PASSWORD= → 1
docker compose pull && up -d → /api/server/version {"major":3,"minor":3,"patch":5}
docker image prune -f
```

## Incidencias

| # | Paso | Descripción | Acción |
|---|---|---|---|
| 1 | 5 | El UPD asigna el paso al usuario por la web de OMV; persona 1 lo delegó en el agente | `omv-upgrade` por SSH dentro de `systemd-run`, para que siguiera aunque se cortara la conexión |
| 2 | 6 | Una comprobación usó el puerto 80 para la web de OMV, pero OMV escucha en el 8000 | No es un fallo: el puerto 80 está libre por Caddy. Corregir la comprobación en el UPD siguiente |
| 3 | 9 | Reinicio aplazado | Se hará con persona 1 en casa, junto con el reinicio del RBK 16 |

## Estado final

Pendiente: AIO (paso 8), reinicio y comprobaciones (pasos 9 y 10) e inventario posterior (paso 11).

## Cambios en la configuración

- `state/config/srv/immich/compose/env.sin-secretos`: `IMMICH_VERSION=v3.3.5`.

## Historial de versiones

| Versión | Fecha | Autor | Cambios |
|---|---|---|---|
| 1.0 | 2026-10-29 | Operator Agent | Registro de los pasos 1, 2 y 4 a 7; pasos 3 y 8 a 11 pendientes |
