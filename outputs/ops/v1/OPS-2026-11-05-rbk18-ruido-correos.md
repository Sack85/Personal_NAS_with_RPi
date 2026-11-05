# OPS — RBK 18 Ruido de correos (pasos 1 a 7)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-11-05 |
| **Última modificación** | 2026-11-05 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v3 (1.0, Aprobado) — RBK-2026-11-04-18-ruido-correos.md |
| **Resultado** | Parcial |
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
| 3 | Lectura | Agente | | Pendiente | |
| 4 | Cambio | Agente | | Pendiente | |
| 5 | Cambio | Agente | | Pendiente | |
| 6 | Cambio | Agente | | Pendiente | |
| 7 | Cambio | Agente | | Pendiente | |

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

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 2 | `omv-env set` (click) interpreta el valor que empieza por `-a` como opción: `Error: No such option: -a`. No se cambió nada (la variable sigue sin valor) | Parada de la ejecución; sin vuelta atrás necesaria | Corregir el RBK: pasar el valor tras `--` (`omv-env set -- KEY VALUE`) o empezarlo de otro modo, verificado antes en solo lectura; `/runbook-plugin:update-rbk RBK-2026-11-04-18-ruido-correos` |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| Pendiente | | |

## Cambios en la configuración

- Pendiente

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-11-05 | Operator Agent | Inicio de la ejecución |
