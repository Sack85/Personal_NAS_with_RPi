# runbook-plugin

Autor de runbooks. Convierte el HLD **Aprobado** en un runbook (RBK) por fase de la instalación,
con pasos numerados que dicen el riesgo, quién ejecuta, dónde, el comando, qué comprobar antes y
después y qué hacer si falla. El operador solo ejecuta runbooks aprobados.

## Fases

| Nº | Fase | Secciones de la guía |
|---|---|---|
| 01 | Material y montaje | 1 |
| 02 | Grabar el sistema en el SSD | 2 |
| 03 | Primer arranque y HAT | 3 |
| 04 | OpenMediaVault 8, plugins y correo | 4 |
| 05 | Discos: revisión SMART y formateo | 5 |
| 06 | SnapRAID | 6 |
| 07 | MergerFS y carpetas compartidas | 7 |
| 08 | Usuarios y Samba | 8 |
| 09 | Spindown con hd-idle | 9 |
| 10 | Nextcloud AIO | 10 |
| 11 | Backups con restic | 11 |
| 12 | SAI y NUT | 12 |
| 13 | Temperatura y mantenimiento | 13 |
| 14 | Acceso exterior (opcional) | 14 |

## Skills

| Skill | Comando | Qué hace |
|---|---|---|
| create-rbk | `/runbook-plugin:create-rbk <fase>` | Escribe el runbook de una fase desde el HLD aprobado |
| update-rbk | `/runbook-plugin:update-rbk <fichero>` | Cambia un runbook (p. ej. tras un HLD nuevo) |
| validate-rbk | `/runbook-plugin:validate-rbk` | Reglas de seguridad de los pasos |
| approve-rbk | `/runbook-plugin:approve-rbk <fichero>` | Aprueba un runbook concreto |
| apply-learnings | `/runbook-plugin:apply-learnings` | Convierte correcciones en reglas |

## Salida

`outputs/rbk/vN/RBK-AAAA-MM-DD-<NN>-<fase>.md`, un fichero por fase.

## Reglas que el validador bloquea

- Paso sin riesgo (Lectura / Cambio / Destructivo), sin quién ejecuta o sin dónde.
- Comando destructivo (según la misma lista que el guard SSH) en un paso no marcado Destructivo.
- Paso Destructivo ejecutado por el agente, sin comprobación previa o sin "Si falla".
- Sin verificación final ni citar el HLD aprobado.
