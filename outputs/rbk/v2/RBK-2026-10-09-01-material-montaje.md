# RBK 01 — Material y montaje

| Campo | Valor |
|---|---|
| **Documento** | RBK |
| **Fase** | 01 — Material y montaje |
| **Versión** | 2.0 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-09 |
| **Última modificación** | 2026-10-09 |
| **Autor** | Runbook Agent |
| **Entregable previo** | HLD v2 (2.0, Aprobado) — HLD-2026-10-09-nas-familiar.md |
| **Riesgo máximo** | Cambio |
| **Duración estimada** | 3 h (sin contar compras ni impresión) |

## Objetivo

Reunir el material del HLD §2, montar el HAT, la caja y el aire, y dejar cada disco identificado
por su número de serie y su bahía (1 = WD Blue paridad, 2 = vacía, 3 = Toshiba MK1059 D1,
4 = Samsung QVO D2). Los discos quedan en sus bahías pero sin conectar al FFC hasta el RBK 03.

## Prerrequisitos

- [ ] HLD v2 2.0 aprobado
- [ ] Los datos de los discos viejos (WD Blue, Toshiba MK1059, Samsung QVO) copiados a los PC: el RBK 05 los borra
- [ ] Disco USB externo de 4 TB y caja USB con paso de SMART (`smartctl -d sat`) comprados (HLD §2, ADR-017)
- [ ] Caja impresa en PETG o ASA (nunca PLA)

## Pasos

### Paso 1: Comprobar el material contra el HLD

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2 Hardware |

Marca cada pieza en el OPS. El SAI es opcional hasta que se resuelva la pregunta abierta del HLD (RBK 12).

Esperado: todas las piezas de la tabla del HLD §2 presentes: Pi 5 8 GB + Active Cooler, Radxa Penta SATA HAT + FFC, adaptador 12 V / 5 A (5,5 × 2,5 mm, centro positivo), XG5 en caja USB 3, WD Blue, Toshiba MK1059, Samsung QVO, disco USB de 4 TB, ventilador 120 mm, filtro, cable Ethernet. El Hitachi 320 GB queda fuera.

Si falla: si falta una pieza, para y anótala en el OPS; sin adaptador de 12 V / 5 A o sin caja de PETG/ASA no se sigue.

### Paso 2: Anotar modelo y número de serie de cada disco

| Campo | Valor |
|---|---|
| **Riesgo** | Lectura |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2, §5 |

Estos números de serie son la referencia de todos los pasos destructivos de los RBK 05 y 11.

Esperado: tabla en el OPS con Rol → modelo → número de serie (de la etiqueta) para WD Blue, Toshiba MK1059, Samsung QVO y el disco USB de 4 TB; una etiqueta adhesiva con el rol (PARIDAD, D1, D2, BACKUP) en cada disco.

Si falla: si una etiqueta no se lee, anótalo; el número de serie se leerá con `lsblk` en el RBK 03.

### Paso 3: Montar la Pi, el Active Cooler y el HAT

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2 |

Sin alimentación conectada en ningún momento de este paso.

Esperado: Active Cooler atornillado; HAT sobre el GPIO; FFC con la cara negra hacia fuera y los dos pestillos cerrados.

Si falla: si un pestillo no cierra, no fuerces: saca el FFC y vuelve a insertarlo recto.

### Paso 4: Colocar los discos en sus bahías

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2 (bahías) |

Esperado: bahía 1 = WD Blue, bahía 2 = vacía, bahía 3 = Toshiba MK1059 (la de más aire), bahía 4 = Samsung QVO (la de menos aire). Los dos mecánicos separados por la bahía vacía. Discos sin conectar al HAT hasta el RBK 03 paso 12.

Si falla: si la caja impresa no deja la bahía 3 en la entrada de aire, cambia de bahía a Toshiba y QVO y anótalo en el OPS para actualizar el HLD.

### Paso 5: Montar el ventilador y el filtro

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2, §9 |

Esperado: ventilador de 120 mm a velocidad fija baja soplando sobre los discos y el HAT; filtro en la entrada de aire.

Si falla: si el ventilador hace ruido variable, usa un adaptador de velocidad fija (resistencia o regulador manual).

### Paso 6: Ubicar el NAS

| Campo | Valor |
|---|---|
| **Riesgo** | Cambio |
| **Ejecuta** | Usuario |
| **Dónde** | Físico |
| **HLD** | §2 (ubicación), §9 |

Esperado: NAS en balda alta y abierta, lejos del sol, del suelo y del chorro del aire acondicionado; cable Ethernet hasta el router; higrómetro cerca.

Si falla: si no hay sitio que cumpla, para y consulta al arquitecto: el riesgo de condensación es Alto (HLD §12).

## Verificación final

| Comprobación | Comando | Esperado |
|---|---|---|
| Piezas | `inspección visual` | todas las del HLD §2 |
| Bahías | `inspección visual` | 1 WD, 2 vacía, 3 Toshiba, 4 QVO |
| Números de serie | `tabla del OPS` | 4 discos con rol y serie |

## Vuelta atrás

Nada es irreversible: desmontar en orden inverso. Ningún disco se ha escrito.

## Evidencias

- Tabla Rol → modelo → número de serie en el OPS
- Foto 1.1 (HAT con los discos) y foto 1.2 (NAS en su sitio) en el OPS

## Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Hay SAI con USB compatible con NUT? Decide si se ejecuta el RBK 12 | Persona 1 | 2026-10-31 |

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-09 | Runbook Agent | Creación |
| 1.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
| 2.0 | 2026-10-09 | Runbook Agent | Escenario A: revisado contra HLD v2 (2.0, Aprobado); cita la nueva versión. Comprobado que identifica los discos por by-id o UUID, nunca por `/dev/sdX` (ADR-022) |
| 2.0 | 2026-10-09 | Runbook Agent | Estado cambiado a Aprobado |
