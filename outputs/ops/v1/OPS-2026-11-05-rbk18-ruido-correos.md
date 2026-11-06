# OPS — RBK 18 Ruido de correos (pasos 1 a 7)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-11-05 |
| **Última modificación** | 2026-11-05 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v3 (1.2, Aprobado) — RBK-2026-11-05-18-ruido-correos.md |
| **Resultado** | En curso |
| **Inicio** | 2026-11-05 09:42 |
| **Fin** | 2026-11-05 09:45 |

## Alcance

Pasos 1 a 7 del RBK 18. El paso 8 (comprobación tras el sync de las 23:30) queda para mañana. Ejecución a las 09:42, fuera de la ventana 22:30-00:30.

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK validado (validate_rbk.py) | 0 CRITICAL, 0 WARNING |
| NAS responde (uptime) | up 1 day, 1:40 |
| Ficheros del repo pasan bash -n | OK |
| Paso 1 (partida) | Variable sin valor, 0 coincidencias de -I 7, apticron existe, snapraid-aviso no existe, tarea Cron con /usr/sbin/omv-snapraid-diff (E1) |
| state/applied.yaml | No lista las fases 08 a 17 aunque hay OPS de 16 y 17; se continúa, sin dependencia con el RBK 18 |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1 | Lectura | Agente | 09:42 | OK | E1 |
| 2 | Cambio | Agente | 09:44 | Fallo | E2 |
| 2 (reanudado, RBK 1.1) | Cambio | Agente | 15:58 | Fallo | E3 |
| 3 | Lectura | Agente | 15:59 | Fallo | E3 |
| 2 (reanudado, RBK 1.2) | Cambio | Agente | 16:22 | OK | E4 |
| 3 (reanudado) | Lectura | Agente | 16:22 | OK | E4 |
| 4 | Cambio | Agente | 16:30 | OK | E5 |
| 5 | Cambio | Agente | 20:50 | OK | E6 |
| 6 | Cambio | Agente | 20:56 | OK | E7 |
| 7 | Cambio | Agente | 21:06 | OK | E8 |
| 8 | Lectura | Agente | 2026-11-06 07:30 | OK | E9 |

## Evidencias

### E1 Paso 1

```
(variable vacía)
0
ls: cannot access '/usr/local/lib/snapraid-aviso': No such file or directory
/etc/cron.daily/openmediavault-apticron
{"uuid":"1e921904-...","enable":true,"sendemail":true,"command":"\/usr\/sbin\/omv-snapraid-diff", ...}
```

### E2 Paso 2

```
Pseudo-terminal will not be allocated because stdin is not a terminal.
Usage: omv-env set [OPTIONS] KEY VALUE
Error: No such option: -a
```

### E3 Pasos 2 (reanudado) y 3

```
omv-env get --value-only -> -a -o on -S on -T permissive -R 5! -R 197! -U 198+ -I 7
omv-salt deploy run smartmontools -> Succeeded: 10 (changed=2), Failed: 0
grep -c "^DEFAULT .*-I 7 ..." /etc/smartd.conf -> 0
grep -c ^DEFAULT -> 1 ; smartmontools active
DEFAULT -a -o on -S on -T permissive -R 5! -R 197! -U 198+ -W 0,40,45 -n standby,q
systemctl status: Active since Wed 2026-11-04 08:01:32 (no reiniciado)
```

### E4 Pasos 2 y 3 (RBK 1.2)

```
omv-env get -> ... -U 198+ -I 7 ; grep -c pillar antes: 0
omv-salt stage run prepare -> Failed: 0 ; grep -c pillar: 1
omv-salt deploy run smartmontools -> Succeeded: 10 (changed=4), Failed: 0
grep -c "^DEFAULT .*-I 7 -W 0,40,45 -n standby,q" -> 1 ; grep -c ^DEFAULT -> 1 ; smartmontools active, sin errores en el journal
```

### E5 Paso 4

```
Notification set apt enable=false -> {"uuid":"5334afb5-...","id":"apt","enable":false}
omv-salt deploy run apticron apt -> Failed: 0
ls cron.daily/cron.weekly apticron y 98openmediavault-mail.conf -> No such file or directory (3)
getList -> "id":"apt","enable":false
```

### E6 Paso 5

```
-rwxr-xr-x root root 808 /usr/local/lib/snapraid-aviso/mail
-rwxr-xr-x root root 264 /usr/local/sbin/snapraid-diff-solo-fallos
sintaxis-ok
```

### E7 Paso 6

```
salida=0 (limpia) ; salida=0 (con fallo)
journal: Informe de exito no enviado: PRUEBA RBK18 limpia - Sync/Scrub Job COMPLETED   (una sola linea)
```

### E8 Paso 7

```
hora del NAS: 21:06 (fuera de 22:30-00:30); antes: command=/usr/sbin/omv-snapraid-diff
Cron set -> command=/usr/local/sbin/snapraid-diff-solo-fallos (resto igual)
omv-salt deploy run cron -> Succeeded: 7 (changed=3), Failed: 0
tail -1 cron.d/userdefined-1e921904-... -> /usr/local/sbin/snapraid-diff-solo-fallos
grep -c snapraid-diff-solo-fallos /etc/cron.d/openmediavault-userdefined -> 0 (esperado 1)
grep -c "30 23 \* \* \*" /etc/cron.d/openmediavault-userdefined -> 1
```

### E9 Paso 8 (2026-11-06 07:30)

```
journal: 23:30:57 Informe de exito no enviado: SnapRAID - Sync/Scrub Job COMPLETED (una sola linea)
snapraid.log: SYNC Job finished 23:30:57; Added 1166, Updated 2; scrub no ejecutado (ciclo 2 de 7)
snapraid status: No error detected
verificacion final: -I 7 =1; apticron cron.daily No such file; "sendmail": true; ultima linea script cron = snapraid-diff-solo-fallos
grep -c snapraid-diff-solo-fallos /etc/cron.d/openmediavault-userdefined -> 0 (misma incidencia del paso 7)
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 2 | `omv-env set` (click) interpreta el valor que empieza por `-a` como opción: `Error: No such option: -a`. No se cambió nada (la variable sigue sin valor) | Parada de la ejecución; sin vuelta atrás necesaria | Corregir el RBK: pasar el valor tras `--` (`omv-env set -- KEY VALUE`) o empezarlo de otro modo, verificado antes en solo lectura; `/runbook-plugin:update-rbk RBK-2026-11-04-18-ruido-correos` |
| 2/3 | Con RBK 1.1 la variable se guarda con `--`, pero el deploy de smartmontools no la lleva a `/etc/smartd.conf` (la línea DEFAULT sigue sin `-I 7` y smartd no se reinició). Estado: variable fijada, fichero sin cambiar | Parada; pasos 4 a 7 sin ejecutar. Vuelta atrás opcional: `omv-env unset OMV_SMARTMONTOOLS_DEFAULTDIRECTIVES` | Investigar en solo lectura cómo lee la plantilla `etc-smartd_conf.j2` la variable (posible caché de pillar o clave distinta); `/runbook-plugin:update-rbk` |
| 7 | El recuento `grep -c snapraid-diff-solo-fallos /etc/cron.d/openmediavault-userdefined` dio 0 y el RBK esperaba 1. Causa: la línea de cron llama al script generado `/var/lib/openmediavault/cron.d/userdefined-1e921904-...`, que sí contiene el comando nuevo (comprobado). El cambio es correcto; el esperado del RBK es erróneo | Ninguna sobre el NAS; paso 8 pendiente tras el sync de las 23:30 | Corregir ese esperado en el RBK 18 con `/runbook-plugin:update-rbk` |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| smartd ignora el 7 | grep -c = 1 | Si |
| Sin aviso de actualizaciones | cron.daily/openmediavault-apticron no existe | Si |
| Tarea con el envoltorio | Script generado la llama; grep -c en /etc/cron.d da 0 (esperado del RBK erroneo, incidencia 7) | Si, con incidencia |
| Avisos de fallo conservados | sendmail true | Si |
| Estado SnapRAID | No error detected | Si |
| Bandeja de la persona 1 sin COMPLETED limpio | Pendiente de confirmar | Pendiente |

## Cambios en la configuración

- Pendiente

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-11-05 | Operator Agent | Inicio de la ejecución |
| 1.1 | 2026-11-05 | Operator Agent | Reanudada en el paso 2 con RBK 1.1; parada en el paso 3 |
| 1.2 | 2026-11-05 | Operator Agent | Reanudada en el paso 2 con RBK 1.2; pasos 2 a 6 OK; pausa antes del paso 7 a la espera de confirmar el correo de prueba |
| 1.3 | 2026-11-05 | Operator Agent | Reanudada en el paso 7: confirmado el correo del paso 6; paso 7 OK (tarea Cron al envoltorio); pausa hasta el sync de las 23:30 para el paso 8 |
| 1.4 | 2026-11-06 | Operator Agent | Reanudada en el paso 8: sync de las 23:30 filtrado en el journal, snapraid sin errores; pendiente confirmar la bandeja y corregir el esperado del paso 7 en el RBK |
