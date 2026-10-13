# OPS — Ejecución del RBK 07 (MergerFS y carpetas)

| Campo | Valor |
|---|---|
| **Documento** | OPS |
| **Versión** | 1.2 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-13 |
| **Última modificación** | 2026-10-13 |
| **Autor** | Operator Agent |
| **Entregable previo** | RBK v2 (2.1, Aprobado) — RBK-2026-10-09-07-mergerfs-carpetas.md |
| **Resultado** | Completado |
| **Inicio** | 2026-10-13 21:00 |
| **Fin** | 2026-10-13 21:30 |

> Registro a posteriori: la ejecución se hizo el 2026-10-13 y se registra sin re-ejecutar nada,
> a partir de `memory/ops/session-2026-10-13.md` (sección RBK 07). Horas aproximadas.

## Alcance

Fase 07 completa: pool MergerFS `pool` sobre d1 y d2 (paridad excluida), cinco carpetas
compartidas, subcarpetas, propietario `www-data` y prueba de escritura. Todos los pasos los hizo
el Agente por SSH con `omv-rpc` (ningún paso Destructivo).

## Estado inicial

| Comprobación | Resultado |
|---|---|
| RBK 07 v2.1 aprobado | Sí |
| RBK 06 aplicado | Sí (`state/applied.yaml`, OPS-2026-10-13-rbk06 Aprobado) |
| `ssh nas` con clave | Sí |
| Pasos destructivos | No |

## Registro de pasos

| Paso | Riesgo | Ejecutó | Hora | Resultado | Evidencia |
|---|---|---|---|---|---|
| 1. Crear el pool | Cambio | Agente | ~21:00 | OK | E1 |
| 2. Comprobar el pool montado y sus opciones | Lectura | Agente | ~21:05 | OK | E2 |
| 3. Crear las carpetas compartidas | Cambio | Agente | ~21:10 | OK | E3 |
| 4. Crear subcarpetas y propietario www-data | Cambio | Agente | ~21:15 | OK | E4 |
| 5. Comprobar el árbol de carpetas | Lectura | Agente | ~21:20 | OK | E4 |
| 6. Prueba de escritura en el pool | Cambio | Agente | ~21:25 | OK | E5 |

## Evidencias

### E1 — Paso 1: pool (omv-rpc Mergerfs set)

```
pool uuid a64bbd9e-4639-481d-a415-fd4745764fa8, mntentref 5cb09afe-def1-407f-a7ec-6e8c839e844d
ramas: d1 (1d82d7b3…), d2 (56801884…); paridad no incluida
omv-salt deploy run mergerfs: 7 OK, sin Failed
```

### E2 — Paso 2: montaje y opciones

```
/srv/mergerfs/pool  fuse.mergerfs  1.8T
category.create=mfs, minfreespace=20G, cache.files=off, dropcacheonclose=true, category.search=ff
```

### E3 — Paso 3: carpetas compartidas (omv-rpc ShareMgmt set, mode 775)

```
Documentos_persona1 -> Documentos/persona1/
Documentos_persona2 -> Documentos/persona2/
Imagenes, Videos, Archivo
grep: cada nombre 1 vez (5 nombres, sin duplicados)
omv-salt deploy run sharedfolders: módulo inexistente en OMV 8 (no necesario)
```

### E4 — Pasos 4 y 5: subcarpetas y propietarios

```
Imagenes/Moviles, Archivo/nextcloud-aio-backup, Archivo/immich-db creadas
Documentos/persona1, Documentos/persona2, Imagenes, Imagenes/Moviles: www-data:www-data
Documentos (padre): 710 con ACL users:--x (solo atravesar), puesto por OMV
Videos, Archivo: root:users 2775 (setgid)
```

### E5 — Paso 6: prueba de escritura

```
.prueba escrita en la rama d1 (política mfs) y borrada sin error
systemctl --failed: 0 unidades
```

## Incidencias

| Paso | Qué pasó | Acción | Seguimiento |
|---|---|---|---|
| 3 | Incidencia 1 (menor): el módulo salt `sharedfolders` no existe en OMV 8 | Previsto en el Esperado del RBK: anotado y seguido; las carpetas quedan en la base de datos | Opcional: `/runbook-plugin:update-rbk RBK-2026-10-09-07-mergerfs-carpetas` para quitar el deploy |
| 4 | Incidencia 2 (menor): OMV deja `Documentos` (padre) en 710 con ACL `users:--x` | Correcto: solo permite atravesar hasta `persona1`/`persona2` | Ninguno |

## Estado final

| Comprobación | Resultado | OK |
|---|---|---|
| Pool montado | `fuse.mergerfs` | Sí |
| Tamaño | 1.8T | Sí |
| Propietario Imagenes | www-data | Sí |

## Cambios en la configuración

- Pool MergerFS `pool` en `/srv/mergerfs/pool` (entrada fstab/systemd gestionada por OMV).
- Cinco carpetas compartidas en la base de datos de OMV.
- Árbol de carpetas y propietarios en el pool.

## Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-13 | Operator Agent | Registro creado a posteriori |
| 1.1 | 2026-10-13 | Operator Agent | Pasos 1-6 registrados; Resultado Completado; En revisión |
| 1.2 | 2026-10-13 | Operator Agent | Ejecución cerrada y aprobada |
