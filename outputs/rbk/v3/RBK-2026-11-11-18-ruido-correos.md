# RBK 18 — Ruido de correos

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 18 — Ruido de correos |
| **Versión** | 1.5 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-11-04 |
| **Última modificación** | 2026-11-11 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v3 (3.1, Aprobado) — HLD-2026-11-06-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 40 min + comprobación a la mañana siguiente (tras el sync de las 23:30) |

## Objetivo

Quitar tres correos que no aportan nada y conservar todos los avisos de fallo (HLD v3 §5 «Avisos», §9, §10):

1. Aviso de smartd por cambios del atributo 7 (`Seek_Error_Rate`): se añade `-I 7` a `OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES`.
2. Correo «SnapRAID - Sync/Scrub Job COMPLETED»: solo debe llegar si algo falla.
3. Correo diario «N package update(s) available»: el usuario actualizará una vez al mes con el UPD.

Qué genera cada correo (comprobado en el NAS en solo lectura el 2026-11-04):

| Correo | Lo genera | Cómo se cambia aquí |
|---|---|---|
| Cambios del atributo 7 | `smartd`, con `/etc/smartd.conf` creado por el estado salt `omv/deploy/smartmontools` (plantilla `etc-smartd_conf.j2`, línea `DEFAULT`, que lee `default:OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES`; hoy sin fijar, vale `-a -o on -S on -T permissive -R 5! -R 197! -U 198+`) | `omv-env set OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES …` + `omv-salt stage run prepare` + `omv-salt deploy run smartmontools`. `-I 7` solo actúa junto a `-p/-u/-t`, que ya trae `-a` (`man smartd.conf`) |
| Sync/Scrub COMPLETED | `/usr/sbin/omv-snapraid-diff` (paquete `openmediavault-snapraid` 8.0.3), función `_send_email` con `mail`; ajuste OMV `conf.service.snapraid.sendmail` = true. El mismo ajuste manda también los avisos de umbral (50 borrados) y de disco ausente, así que apagarlo los perdería | Un `mail` propio (`/usr/local/lib/snapraid-aviso/mail`) delante en el PATH, lanzado por un envoltorio (`/usr/local/sbin/snapraid-diff-solo-fallos`) que pasa a ser el comando de la tarea Cron de OMV. No se toca el script del paquete ni el ajuste `sendmail` |
| Cron - SnapRAID diff+sync diario | Tarea Cron de OMV `1e921904-…` (`sendemail` true, `mail -E`): solo manda si la tarea imprime algo | Se deja como está (es aviso de fallo) |
| N package update(s) available | `apticron` desde `/etc/cron.daily/openmediavault-apticron`; lo crea `omv/deploy/apticron/20cron.sls` solo si la notificación `apt` de OMV está activa (`conf.system.notification.notification`, uuid `5334afb5-…`) | `omv-rpc Notification set` con `enable` false + `omv-salt deploy run apticron apt` |

Efecto colateral (hallazgo del 2026-11-11 al revisar los correos desde el 5 de noviembre; correo diario «Pending configuration changes» de las ~07:35, 6 desde el 06-11): los `omv-rpc ... set` de los pasos 4 y 7 marcan módulos como pendientes en `/var/lib/openmediavault/dirtymodules.json` y el `omv-salt deploy run` a mano no limpia ese marcador. El paso 9 los aplica con la forma oficial de OMV (`omv-rpc Config applyChanges`, esquema `rpc.config.json`: `modules` y `force`, ambos obligatorios; método en `/usr/share/openmediavault/engined/rpc/config.inc`, comprobado en solo lectura el 2026-11-11).

Consecuencia de la notificación `apt` apagada: desaparece también el listado de cambios de apt-listchanges por correo (`/etc/apt/listchanges.conf.d/98openmediavault-mail.conf`). No afecta a `apt` ni al aviso de `unattended-upgrades`.

**Diferencia con el HLD**: el HLD v3 §5 dice «Informe de cada sync y scrub por correo» y §10 cuenta «correo de SnapRAID» en el calendario semanal. Con este RBK ya no hay informe de éxito. Pide `/architect-plugin:update-hld` (ADR nuevo) antes o justo después de aprobar este RBK.

## Prerrequisitos

- [ ] Fuera de la ventana 22:30-00:30 (backup de AIO, sync de las 23:30): los pasos 4 y 7 reescriben notificaciones y tarea Cron
- [ ] Sin sesión web: todos los pasos los hace el Agente por SSH, una orden por línea; no pegues varias líneas tras `ssh nas`
- [ ] `state/config/usr/local/sbin/snapraid-diff-solo-fallos` y `state/config/usr/local/lib/snapraid-aviso/mail` existen en el repo (PC) y pasan `bash -n`
- [ ] Reinicio no necesario: ningún paso lo pide
- [ ] El paso 9 reinicia `monit`, `rsyslog`, `smartd` y regenera cron: también fuera de la ventana 22:30-00:30

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

Comprobación previa: paso 1 (la variable no tiene valor, o ya tiene el valor de este paso si se reanuda tras la incidencia del OPS; el `set` es idempotente).

Comando (una orden por línea):

```bash
ssh -t nas "sudo omv-env set -- OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES '-a -o on -S on -T permissive -R 5! -R 197! -U 198+ -I 7'"
```

```bash
ssh nas 'sudo omv-env get --value-only OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES'
```

```bash
ssh -t nas "sudo omv-salt stage run prepare"
```

```bash
ssh nas 'grep -c OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES /srv/pillar/omv/default.sls'
```

```bash
ssh -t nas "sudo omv-salt deploy run smartmontools"
```

Nota: el pillar de OMV (`/srv/pillar/omv/default.sls`) se genera con `stage run prepare`; sin él el deploy no ve la variable nueva (OPS 2026-11-05 pasos 2/3; mismo caso que la incidencia 1 de OPS-2026-10-29-rbk16-resiliencia). El `grep -c` debe dar `1` antes del deploy; si da `0`, repite el `prepare` y no sigas. `omv-env set` usa click y trata un valor que empieza por `-` como opción (`No such option: -a`, OPS 2026-11-05 paso 2); el `--` antes de la clave termina las opciones. Probado en solo lectura en el NAS con el mismo click 8.1.8 y los mismos argumentos (`['--','K','-a -o on -I 7']` da `('K','-a -o on -I 7')`). Esperado: el `get` devuelve `-a -o on -S on -T permissive -R 5! -R 197! -U 198+ -I 7`; el `prepare` y el `omv-salt` terminan sin `Failed` en el resumen de salt. Reinicia `smartd` pero no despierta discos (`-n standby,q` sigue en la línea `DEFAULT`).

Si falla: `ssh nas 'sudo omv-env unset OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES'` y repite `omv-salt stage run prepare` y `omv-salt deploy run smartmontools`; vuelve al valor por defecto de la plantilla.

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

Esperado: sin `Failed`; `ssh nas 'sudo cat /var/lib/openmediavault/cron.d/userdefined-1e921904-2c6c-428f-97d5-0079e7387374 | tail -1; grep -c snapraid-diff-solo-fallos /var/lib/openmediavault/cron.d/userdefined-1e921904-2c6c-428f-97d5-0079e7387374'` da `/usr/local/sbin/snapraid-diff-solo-fallos` y `1` (el comando está en el script generado por OMV; `/etc/cron.d/openmediavault-userdefined` solo llama a ese script y da 0); `grep -c "30 23 \* \* \*" /etc/cron.d/openmediavault-userdefined` da `1` (la otra tarea con el mismo nombre está desactivada y no aparece).

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

### Paso 9: Aplicar los cambios pendientes de OMV

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Agente |
| **Dónde** | NAS por SSH |
| **HLD** | §10 |

Comprobación previa (Lectura): pasos 2 a 7 hechos y hora fuera de 22:30-00:30. Lista los módulos pendientes y su origen:

```bash
ssh nas 'cat /var/lib/openmediavault/dirtymodules.json'
```

Esperado (2026-11-11): `["apt","apticron","monit","rsyslog","smartmontools","cron"]`. Origen comprobado en solo lectura: `apt` y `apticron` (paso 4: notificación `apt`); `monit` y `rsyslog` también los marca la notificación (los módulos `monit.inc` y `syslog.inc` escuchan `conf.system.notification.notification`, así que son del paso 4 y no de los RBK 16 y 17, cuyos OPS no los tocan); `smartmontools` (paso 2) y `cron` (paso 7). Si aparece un módulo que no es de esta lista, para y avisa a la persona usuaria: es de otro cambio y no se aplica sin saber cuál.

Comando (una orden por línea; usa exactamente los módulos que devolvió la previa; `force` false para tocar solo lo pendiente):

```bash
ssh -t nas "sudo omv-rpc Config applyChanges '{\"modules\":[\"apt\",\"apticron\",\"monit\",\"rsyslog\",\"smartmontools\",\"cron\"],\"force\":false}'"
```

```bash
ssh nas 'cat /var/lib/openmediavault/dirtymodules.json; systemctl is-active monit rsyslog smartmontools cron'
```

```bash
ssh nas 'grep -c snapraid-diff-solo-fallos /var/lib/openmediavault/cron.d/userdefined-1e921904-2c6c-428f-97d5-0079e7387374; grep -c "30 23 \* \* \*" /etc/cron.d/openmediavault-userdefined; grep -c -e "-I 7" /etc/smartd.conf; ls /etc/cron.daily/openmediavault-apticron 2>&1'
```

Esperado: el `applyChanges` devuelve la lista de módulos procesados y sin error; `dirtymodules.json` queda `[]`; `active` cuatro veces; luego `1`, `1`, `1` y `No such file or directory` (el cron de SnapRAID sigue llamando al envoltorio, smartd conserva `-I 7` y no vuelve el aviso de apt). Aplicar no cambia valores: despliega lo que los pasos 2, 4 y 7 ya fijaron en la base de datos y en el pillar.

Si falla: si `applyChanges` da error, no edites `dirtymodules.json` a mano; copia el mensaje al OPS y repite con un solo módulo (`"modules":["monit"]`) para localizar el que falla. Si un servicio no está `active`, `ssh nas 'sudo journalctl -u <servicio> -n 20 --no-pager'` y para. Si el cron o `smartd.conf` no cuadran, aplica la vuelta atrás del paso 7 o del 2. Mañana a las 07:35 el correo seguirá llegando si el fichero no quedó en `[]`.

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| smartd ignora el 7 | `ssh nas 'grep -c "^DEFAULT .*-I 7" /etc/smartd.conf'` | `1` |
| Sin aviso de actualizaciones | `ssh nas 'ls /etc/cron.daily/openmediavault-apticron 2>&1'` | `No such file or directory` |
| Tarea con el envoltorio | `ssh nas 'grep -c snapraid-diff-solo-fallos /var/lib/openmediavault/cron.d/userdefined-1e921904-2c6c-428f-97d5-0079e7387374; grep -c "30 23 \* \* \*" /etc/cron.d/openmediavault-userdefined'` | `1` y `1` (script generado y línea de cron de las 23:30) |
| Avisos de fallo conservados | `ssh nas 'sudo omv-confdbadm read conf.service.snapraid \| grep -o "\"sendmail\": [a-z]*"'` | `"sendmail": true` |
| Estado SnapRAID | `ssh nas 'sudo snapraid status \| tail -3'` | sin errores |
| Sin cambios pendientes en OMV | `ssh nas 'cat /var/lib/openmediavault/dirtymodules.json'` | `[]` |
| Servicios activos | `ssh nas 'systemctl is-active monit rsyslog smartmontools cron'` | `active` cuatro veces |
| Sin correo «Pending configuration changes» | La persona usuaria comprueba su bandeja mañana a las 07:35 (más el `dirtymodules.json` a esa hora) | No llega el correo y el fichero sigue en `[]` |

## Vuelta atrás

- smartd: `ssh nas 'sudo omv-env unset OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES'`, `sudo omv-salt stage run prepare` y `sudo omv-salt deploy run smartmontools`.
- Actualizaciones: `omv-rpc Notification set` con `"enable":true` y `omv-salt deploy run apticron apt`.
- SnapRAID: `Cron set` con `"command":"/usr/sbin/omv-snapraid-diff"` y `omv-salt deploy run cron`; los dos ficheros de `/usr/local` pueden quedarse sin efecto.
- Paso 9: no tiene vuelta atrás propia (solo despliega lo ya fijado); si un servicio falla, se deshace el paso que lo cambió (2, 4 o 7).
- Sin imagen del SSD: los cambios son de variables de OMV, una notificación, una tarea Cron y dos ficheros nuevos; se deshacen sin reinstalar (regla de aprendizajes: pregunta antes de exigir otra imagen; la verificada del 2026-10-28 sigue siendo la de recuperación).

## Evidencias

- Salida del paso 1 y del paso 3 (línea `DEFAULT` de `/etc/smartd.conf`) en el OPS.
- Salida de la prueba del paso 6 (journal y correo recibido).
- Copias en `state/config/usr/local/lib/snapraid-aviso/mail` y `state/config/usr/local/sbin/snapraid-diff-solo-fallos`; tarea Cron en `state/config/omv/cron-snapraid-setList.json` (guardar el JSON del paso 7) y variable en `state/applied.yaml`.
- Salida del paso 8 de la mañana siguiente.
- Salida del paso 9: `dirtymodules.json` antes y después, módulos procesados y servicios activos; y la bandeja de la mañana siguiente a las 07:35.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-11-04 | Runbook Agent | Creación: `-I 7` en smartd, informe de SnapRAID solo ante fallo, fin del aviso diario de actualizaciones |
| 1.0 | 2026-11-04 | Runbook Agent | Estado cambiado a Aprobado |
| 1.1 | 2026-11-05 | Runbook Agent | Paso 2: `omv-env set -- CLAVE VALOR` (el valor empieza por `-`) y `get` de comprobación; incidencia del OPS-2026-11-05-rbk18-ruido-correos paso 2. Estado En revisión |
| 1.1 | 2026-11-05 | Runbook Agent | Estado cambiado a Aprobado |
| 1.2 | 2026-11-05 | Runbook Agent | Paso 2: `omv-salt stage run prepare` y `grep -c` del pillar (=1) antes del deploy de smartmontools; paso idempotente si la variable ya está fijada. Pasos 4 y 7 no lo necesitan (leen la base de datos de OMV, no `/etc/default/openmediavault`). Incidencia del OPS-2026-11-05-rbk18-ruido-correos pasos 2/3. Estado En revisión |
| 1.2 | 2026-11-05 | Runbook Agent | Estado cambiado a Aprobado |
| 1.3 | 2026-11-06 | Runbook Agent | Paso 7 y Verificación final: el esperado `grep -c` se hace sobre el script generado `/var/lib/openmediavault/cron.d/userdefined-1e92...` (el cron.d solo lo llama y da 0) y la línea `30 23 * * *` aparece una vez. Incidencia del OPS-2026-11-05-rbk18-ruido-correos paso 7. Estado En revisión |
| 1.3 | 2026-11-06 | Runbook Agent | Estado cambiado a Aprobado |
| 1.4 | 2026-11-08 | Runbook Agent | Solo la cita del HLD: de HLD 3.0 a HLD 3.1 (Aprobado, 2026-11-06), sin cambiar pasos ni comandos. Anotado sin cambiar: la «Diferencia con el HLD» de la introducción ya no aplica, porque el HLD 3.1 recoge este RBK en ADR-028 a 031; ningún paso los contradice. Estado En revisión |
| 1.4 | 2026-11-08 | Runbook Agent | Estado cambiado a Aprobado (cambio solo de cita; persona 1: «sigue») |
| 1.5 | 2026-11-11 | Runbook Agent | Paso 9 nuevo: `omv-rpc Config applyChanges` con los módulos de `dirtymodules.json` (apt, apticron, monit, rsyslog, smartmontools, cron) para parar el correo diario «Pending configuration changes» (6 desde el 06-11); origen de cada módulo comprobado en solo lectura (todos de los pasos 2, 4 y 7); verificación final ampliada. Estado En revisión |
| 1.5 | 2026-11-11 | Runbook Agent | Estado cambiado a Aprobado (persona 1: «GO a todo») |
