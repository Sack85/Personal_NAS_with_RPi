# RBK 18 — Ruido de correos

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 18 — Ruido de correos |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-11-04 |
| **Última modificación** | 2026-11-04 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.0, Aprobado) — HLD-2026-10-16-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 30 min + comprobación a la mañana siguiente (tras el sync de las 23:30) |

## Objetivo

Quitar tres correos que no aportan nada y conservar todos los avisos de fallo (HLD v3 §5 «Avisos», §9, §10):

1. Aviso de smartd por cambios del atributo 7 (`Seek_Error_Rate`): se añade `-I 7` a `OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES`.
2. Correo «SnapRAID - Sync/Scrub Job COMPLETED»: solo debe llegar si algo falla.
3. Correo diario «N package update(s) available»: el usuario actualizará una vez al mes con el UPD.

Qué genera cada correo (comprobado en el NAS en solo lectura el 2026-11-04):

| Correo | Lo genera | Cómo se cambia aquí |
|---|---|---|
| Cambios del atributo 7 | `smartd`, con `/etc/smartd.conf` creado por el estado salt `omv/deploy/smartmontools` (plantilla `etc-smartd_conf.j2`, línea `DEFAULT`, que lee `default:OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES`; hoy sin fijar, vale `-a -o on -S on -T permissive -R 5! -R 197! -U 198+`) | `omv-env set OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES …` + `omv-salt deploy run smartmontools`. `-I 7` solo actúa junto a `-p/-u/-t`, que ya trae `-a` (`man smartd.conf`) |
| Sync/Scrub COMPLETED | `/usr/sbin/omv-snapraid-diff` (paquete `openmediavault-snapraid` 8.0.3), función `_send_email` con `mail`; ajuste OMV `conf.service.snapraid.sendmail` = true. El mismo ajuste manda también los avisos de umbral (50 borrados) y de disco ausente, así que apagarlo los perdería | Un `mail` propio (`/usr/local/lib/snapraid-aviso/mail`) delante en el PATH, lanzado por un envoltorio (`/usr/local/sbin/snapraid-diff-solo-fallos`) que pasa a ser el comando de la tarea Cron de OMV. No se toca el script del paquete ni el ajuste `sendmail` |
| Cron - SnapRAID diff+sync diario | Tarea Cron de OMV `1e921904-…` (`sendemail` true, `mail -E`): solo manda si la tarea imprime algo | Se deja como está (es aviso de fallo) |
| N package update(s) available | `apticron` desde `/etc/cron.daily/openmediavault-apticron`; lo crea `omv/deploy/apticron/20cron.sls` solo si la notificación `apt` de OMV está activa (`conf.system.notification.notification`, uuid `5334afb5-…`) | `omv-rpc Notification set` con `enable` false + `omv-salt deploy run apticron apt` |

Consecuencia de la notificación `apt` apagada: desaparece también el listado de cambios de apt-listchanges por correo (`/etc/apt/listchanges.conf.d/98openmediavault-mail.conf`). No afecta a `apt` ni al aviso de `unattended-upgrades`.

**Diferencia con el HLD**: el HLD v3 §5 dice «Informe de cada sync y scrub por correo» y §10 cuenta «correo de SnapRAID» en el calendario semanal. Con este RBK ya no hay informe de éxito. Pide `/architect-plugin:update-hld` (ADR nuevo) antes o justo después de aprobar este RBK.

## Prerrequisitos

- [ ] Fuera de la ventana 22:30-00:30 (backup de AIO, sync de las 23:30): los pasos 4 y 7 reescriben notificaciones y tarea Cron
- [ ] Sin sesión web: todos los pasos los hace el Agente por SSH, una orden por línea; no pegues varias líneas tras `ssh nas`
- [ ] `state/config/usr/local/sbin/snapraid-diff-solo-fallos` y `state/config/usr/local/lib/snapraid-aviso/mail` existen en el repo (PC) y pasan `bash -n`
- [ ] Reinicio no necesario: ningún paso lo pide

## Pasos

### Paso 1: Estado de partida

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5, §9, §10 |

Comando:

```bash
ssh nas 'sudo omv-env get OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES; grep -c -e "-I 7" /etc/smartd.conf; ls /etc/cron.daily/openmediavault-apticron /usr/local/lib/snapraid-aviso 2>&1; sudo omv-rpc Cron get "{\"uuid\":\"1e921904-2c6c-428f-97d5-0079e7387374\"}"'
```

Esperado: (2026-11-04) variable sin valor, `0`, `openmediavault-apticron` existe y `snapraid-aviso` no existe, y el JSON de la tarea con `"command":"\/usr\/sbin\/omv-snapraid-diff"`, `"enable":true`, `"sendemail":true`.

Si falla: si la variable ya tiene valor o el comando de la tarea es otro, para y avisa a la persona usuaria; los pasos 2 y 6 partirían de datos distintos.

### Paso 2: smartd ignora el atributo 7

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comprobación previa: paso 1 (la variable no tiene valor).

Comando (una orden por línea):

```bash
ssh -t nas "sudo omv-env set OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES '-a -o on -S on -T permissive -R 5! -R 197! -U 198+ -I 7'"
```

```bash
ssh -t nas "sudo omv-salt deploy run smartmontools"
```

Esperado: el segundo termina sin `Failed` en el resumen de salt. Reinicia `smartd` pero no despierta discos (`-n standby,q` sigue en la línea `DEFAULT`).

Si falla: `ssh nas 'sudo omv-env unset OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES'` y repite el `omv-salt deploy run smartmontools`; vuelve al valor por defecto de la plantilla.

### Paso 3: Comprobar smartd

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §9 |

Comando:

```bash
ssh nas 'grep -c -e "^DEFAULT .*-R 197! -U 198+ -I 7 -W 0,40,45 -n standby,q" /etc/smartd.conf; grep -c "^DEFAULT" /etc/smartd.conf; systemctl is-active smartmontools; sudo journalctl -u smartmontools -n 5 --no-pager'
```

Esperado: `1`, `1`, `active`; el journal sin `Unable to parse` ni `Directive`. Los avisos de temperatura (`-W 0,40,45`) y de SMART siguen en la misma línea.

Si falla: si el primer número es `0`, mira `grep ^DEFAULT /etc/smartd.conf` y no sigas; si el servicio no está `active`, aplica la vuelta atrás del paso 2.

### Paso 4: Apagar el aviso diario de actualizaciones

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §10 |

Comprobación previa:

```bash
ssh nas 'sudo omv-rpc Notification getList "{\"start\":0,\"limit\":-1}"'
```

Nota de la previa: entrada `"id":"apt"`, uuid `5334afb5-b66d-4719-a3ce-6a6a2d574816`, `"enable":true`.

Comando (una orden por línea; esquema `rpc.notification.json`, método `set` con `uuid`, `id`, `enable`):

```bash
ssh -t nas "sudo omv-rpc Notification set '{\"uuid\":\"5334afb5-b66d-4719-a3ce-6a6a2d574816\",\"id\":\"apt\",\"enable\":false}'"
```

```bash
ssh -t nas "sudo omv-salt deploy run apticron apt"
```

Esperado: sin `Failed`. Comprobación: `ssh nas 'ls /etc/cron.daily/openmediavault-apticron /etc/cron.weekly/openmediavault-apticron /etc/apt/listchanges.conf.d/98openmediavault-mail.conf'` responde `No such file or directory` para los tres, y `ssh nas 'sudo omv-rpc Notification getList "{\"start\":0,\"limit\":-1}" | grep -o "\"id\":\"apt\",\"enable\":[a-z]*"'` da `"id":"apt","enable":false`.

Si falla: pon `"enable":true` en el mismo `omv-rpc Notification set` y repite el `omv-salt deploy run apticron apt`.

### Paso 5: Instalar el `mail` filtrado y el envoltorio de SnapRAID

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | PC y NAS por SSH |
| **HLD** | §5 |

Comprobación previa: `bash -n` de los dos ficheros en el PC y `ssh nas 'ls /usr/local/lib/snapraid-aviso'` → `No such file or directory`.

Comando (una orden por línea; los ficheros se envían desde `state/config/`, sin expansión de la shell):

```bash
ssh nas 'sudo mkdir -p /usr/local/lib/snapraid-aviso'
```

```bash
cat state/config/usr/local/lib/snapraid-aviso/mail | ssh nas "sudo tee /usr/local/lib/snapraid-aviso/mail >/dev/null"
```

```bash
cat state/config/usr/local/sbin/snapraid-diff-solo-fallos | ssh nas "sudo tee /usr/local/sbin/snapraid-diff-solo-fallos >/dev/null"
```

```bash
ssh nas 'sudo chown root:root /usr/local/lib/snapraid-aviso/mail /usr/local/sbin/snapraid-diff-solo-fallos; sudo chmod 755 /usr/local/lib/snapraid-aviso/mail /usr/local/sbin/snapraid-diff-solo-fallos'
```

Esperado: `ssh nas 'ls -l /usr/local/lib/snapraid-aviso/mail /usr/local/sbin/snapraid-diff-solo-fallos; bash -n /usr/local/lib/snapraid-aviso/mail && bash -n /usr/local/sbin/snapraid-diff-solo-fallos && echo sintaxis-ok'` muestra `-rwxr-xr-x root root` en los dos y `sintaxis-ok`. Todavía no los usa nadie.

Si falla: `ssh nas 'sudo rm /usr/local/lib/snapraid-aviso/mail /usr/local/sbin/snapraid-diff-solo-fallos'` (rm de dos ficheros sueltos, no recursivo) y repite.

### Paso 6: Prueba del `mail` filtrado

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comprobación previa: paso 5 correcto. La segunda prueba envía un correo real a `root` (llega a la dirección de OMV) con asunto «PRUEBA RBK18 - Sync/Scrub Job COMPLETED».

Comando (una orden por línea):

```bash
ssh nas "printf 'Everything OK\n' | /usr/local/lib/snapraid-aviso/mail -s 'PRUEBA RBK18 limpia - Sync/Scrub Job COMPLETED' root; echo salida=\$?"
```

```bash
ssh nas "printf 'DANGER! prueba\n' | /usr/local/lib/snapraid-aviso/mail -s 'PRUEBA RBK18 con fallo - Sync/Scrub Job COMPLETED' root; echo salida=\$?"
```

```bash
ssh nas 'sudo journalctl -t snapraid-aviso --since "-5 min" --no-pager'
```

Esperado: ambas con `salida=0`; el journal muestra una sola línea «Informe de exito no enviado: PRUEBA RBK18 limpia …»; en el correo de la persona usuaria llega **solo** «PRUEBA RBK18 con fallo - Sync/Scrub Job COMPLETED» (puede tardar unos minutos).

Si falla: si llegan los dos correos, el filtro no actúa: no pases al paso 7 y revisa con `ssh nas 'cat -A /usr/local/lib/snapraid-aviso/mail | head -20'` que el fichero es el de `state/config/`. Si no llega ninguno, `ssh nas 'sudo tail -20 /var/log/mail.log'` (problema del correo, no del filtro).

### Paso 7: Cambiar la tarea Cron al envoltorio

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §5 |

Comprobación previa: paso 6 correcto y hora fuera de 22:30-00:30. Se cambia solo `command`; el resto es lo leído en el paso 1 (esquema `rpc.cron.json`, método `set`, listas para minuto, hora, mes, día del mes y día de la semana).

Comando (una orden por línea):

```bash
ssh -t nas "sudo omv-rpc Cron set '{\"uuid\":\"1e921904-2c6c-428f-97d5-0079e7387374\",\"enable\":true,\"execution\":\"exactly\",\"sendemail\":true,\"comment\":\"SnapRAID diff+sync diario (HLD 23:30)\",\"type\":\"userdefined\",\"minute\":[\"30\"],\"everynminute\":false,\"hour\":[\"23\"],\"everynhour\":false,\"month\":[\"*\"],\"dayofmonth\":[\"*\"],\"everyndayofmonth\":false,\"dayofweek\":[\"*\"],\"username\":\"root\",\"command\":\"/usr/local/sbin/snapraid-diff-solo-fallos\"}'"
```

```bash
ssh -t nas "sudo omv-salt deploy run cron"
```

Esperado: sin `Failed`; `ssh nas 'sudo cat /var/lib/openmediavault/cron.d/userdefined-1e921904-2c6c-428f-97d5-0079e7387374 | tail -1; grep -c snapraid-diff-solo-fallos /etc/cron.d/openmediavault-userdefined'` da `/usr/local/sbin/snapraid-diff-solo-fallos` y `1`; `grep -c "30 23 \* \* \*" /etc/cron.d/openmediavault-userdefined` da `1` (la otra tarea con el mismo nombre está desactivada y no aparece).

Si falla: repite el `Cron set` con `"command":"/usr/sbin/omv-snapraid-diff"` y el `omv-salt deploy run cron`.

### Paso 8: Comprobar a la mañana siguiente

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH y correo |
| **HLD** | §5, §9, §10 |

Comprobación previa: ha pasado el sync de las 23:30 con la tarea nueva.

Comando:

```bash
ssh nas 'sudo journalctl -t snapraid-aviso --since "-12 hours" --no-pager; sudo tail -15 /var/log/snapraid.log; sudo snapraid status | tail -5'
```

Esperado: una línea «Informe de exito no enviado: SnapRAID - Sync/Scrub Job COMPLETED» (o, si hubo un aviso real, ningún descarte y un correo recibido); `snapraid.log` con `SnapRAID SYNC Job finished`; `snapraid status` sin errores. La persona usuaria comprueba su bandeja: ni «COMPLETED» ni «package update(s) available» ni avisos del atributo 7.

Si falla: si el informe limpio sigue llegando, mira su cuerpo: una línea `WARNING` o un contador de errores distinto de 0 la hace pasar a propósito (el filtro falla hacia el lado del aviso); si es un `WARNING` fijo e inofensivo, anótalo en el OPS y se ajusta el patrón en un `update-rbk`. Si no se registra el sync en `snapraid.log`, aplica la vuelta atrás del paso 7.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| smartd ignora el 7 | `ssh nas 'grep -c "^DEFAULT .*-I 7" /etc/smartd.conf'` | `1` |
| Sin aviso de actualizaciones | `ssh nas 'ls /etc/cron.daily/openmediavault-apticron 2>&1'` | `No such file or directory` |
| Tarea con el envoltorio | `ssh nas 'grep -c snapraid-diff-solo-fallos /etc/cron.d/openmediavault-userdefined'` | `1` |
| Avisos de fallo conservados | `ssh nas 'sudo omv-confdbadm read conf.service.snapraid \| grep -o "\"sendmail\": [a-z]*"'` | `"sendmail": true` |
| Estado SnapRAID | `ssh nas 'sudo snapraid status \| tail -3'` | sin errores |

## Vuelta atrás

- smartd: `ssh nas 'sudo omv-env unset OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES'` y `sudo omv-salt deploy run smartmontools`.
- Actualizaciones: `omv-rpc Notification set` con `"enable":true` y `omv-salt deploy run apticron apt`.
- SnapRAID: `Cron set` con `"command":"/usr/sbin/omv-snapraid-diff"` y `omv-salt deploy run cron`; los dos ficheros de `/usr/local` pueden quedarse sin efecto.
- Sin imagen del SSD: los cambios son de variables de OMV, una notificación, una tarea Cron y dos ficheros nuevos; se deshacen sin reinstalar (regla de aprendizajes: pregunta antes de exigir otra imagen; la verificada del 2026-10-28 sigue siendo la de recuperación).

## Evidencias

- Salida del paso 1 y del paso 3 (línea `DEFAULT` de `/etc/smartd.conf`) en el OPS.
- Salida de la prueba del paso 6 (journal y correo recibido).
- Copias en `state/config/usr/local/lib/snapraid-aviso/mail` y `state/config/usr/local/sbin/snapraid-diff-solo-fallos`; tarea Cron en `state/config/omv/cron-snapraid-setList.json` (guardar el JSON del paso 7) y variable en `state/applied.yaml`.
- Salida del paso 8 de la mañana siguiente.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-11-04 | Runbook Agent | Creación: `-I 7` en smartd, informe de SnapRAID solo ante fallo, fin del aviso diario de actualizaciones |
