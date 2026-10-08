# NRD — NAS familiar con Raspberry Pi 5

| Campo | Valor |
|---|---|
| **Documento** | NRD |
| **Versión** | 1.0 |
| **Estado** | Borrador |
| **Fecha de creación** | 2026-10-08 |
| **Última modificación** | 2026-10-08 |
| **Autor** | Requirements Agent |
| **Responsable** | Administrador del NAS (Adulto 1) |
| **Fuentes** | inputs/nrd/v1/guia-v2.md, sesión de preguntas 2026-10-08 |

## Resumen

NAS doméstico encendido 24/7 que guarda los documentos y las fotos de la familia, sincroniza
4 PC y 3 móviles y sobrevive al fallo de un disco, a un borrado accidental y a un desastre en
casa (rayo, robo, ransomware) sin perder más de un día de trabajo ni más de un mes de fotos.

## 1. Contexto y objetivos

El NAS de 2020 (Raspberry Pi 4 + NextcloudPi + RAID por USB) dependía de una tarjeta SD, no
tenía copia fuera de casa y se apagaba a diario. Se reconstruye desde cero con los discos que ya
hay en casa, pensando en clima tropical y en que las actualizaciones no rompan nada.

| Objetivo | Medida de éxito |
|---|---|
| No perder documentos ni fotos | 0 ficheros perdidos en la prueba semestral de restauración |
| Sincronizar PC y móviles sin intervención | Fotos del móvil en el NAS antes de las 08:00 del día siguiente |
| Aguantar el fallo de un disco | Reconstrucción completa con `snapraid fix` en menos de 24 h |
| Actualizar sin sustos | 100 % de las actualizaciones con plan aprobado y comprobación posterior |
| Temperaturas seguras | Discos ≤ 40 °C y `get_throttled` = 0x0 en el informe mensual |

## 2. Usuarios y dispositivos

| Usuario | Dispositivos | Uso principal | Acceso desde fuera |
|---|---|---|---|
| Adulto 1 (administrador) | PC Windows 11, PC Linux, móvil Android | Documentos, fotos, administración | Sí, solo Nextcloud |
| Adulto 2 | PC Windows 11, móvil Android | Documentos y fotos | Sí, solo Nextcloud |
| Hijo/a | PC Windows 11, móvil Android | Fotos y vídeos | No |

## 3. Datos y capacidad

| Carpeta | Contenido | Volumen actual (GB) | Crecimiento anual (GB) | Criticidad | Fuente del dato |
|---|---|---|---|---|---|
| Documentos | Papeles, trabajo, facturas | 40 | 5 | Irreemplazable | Medido con `du -sh` el 2026-10-08 |
| Fotos | Fotos y vídeos familiares y de los móviles | 380 | 90 | Irreemplazable | Medido con `du -sh` el 2026-10-08 |
| Videos | Películas y series | 600 | 50 | Reemplazable | Medido en el Explorador el 2026-10-08 |
| Archivo | Copias antiguas, instaladores, backup de Nextcloud | 150 | 30 | Mixta: solo el backup de Nextcloud es irreemplazable | Medido con `du -sh` el 2026-10-08 |

Capacidad necesaria a 3 años: 1 695 GB (1 170 GB actuales + 525 GB de crecimiento), frente a
unos 1 800 GB útiles del pool de dos discos de 1 TB con 20 GB libres mínimos por disco.

## 4. Servicios

| Servicio | Para qué | Usuarios | Prioridad |
|---|---|---|---|
| Samba (SMB) | Carpetas de red en Windows y Linux | Todos | Obligatorio |
| Nextcloud AIO | Sincronizar PC y subir fotos del móvil | Todos | Obligatorio |
| SnapRAID + MergerFS | Paridad diaria y un único pool de datos | Sistema | Obligatorio |
| restic | Backup mensual offline y copia fuera de casa | Administrador | Obligatorio |
| NUT | Apagado limpio con el SAI | Sistema | Obligatorio |
| Avisos por correo | SMART, SnapRAID, SAI y actualizaciones | Administrador | Obligatorio |
| Tailscale | Acceso desde fuera sin abrir puertos | Adultos | Opcional |

## 5. Protección de datos

| Escenario | Datos afectados | RPO | RTO | Cómo se cubre |
|---|---|---|---|---|
| Fallo de un disco de datos | Lo guardado en ese disco | 24 h (último sync) | 24 h | SnapRAID: disco nuevo + `fix` |
| Fallo del disco de paridad | Ninguno | 0 | 48 h | Disco nuevo + sync completo |
| Borrado accidental | Ficheros borrados | 24 h | 1 h | SnapRAID `fix -f` antes del sync, papelera de Samba, restic |
| Ransomware o cifrado | Todo lo accesible por red | 1 mes | 48 h | restic al Hitachi desconectado (12 versiones) |
| Rayo, robo o inundación | Todo el NAS | 1 mes | 1 semana | Copia fuera de casa de Documentos y Fotos |
| Fallo del SSD del sistema | Sistema y datos de Nextcloud | 24 h | 24 h | Backup diario de AIO en el pool + reinstalación según RBK |

## 6. Entorno y restricciones

| Restricción | Valor |
|---|---|
| Clima | Tropical húmedo: 24–32 °C y 70–90 % de humedad relativa |
| Ubicación | Estantería abierta del salón, a 1 m del suelo, lejos del aire acondicionado |
| Funcionamiento | 24/7 con spindown de discos mecánicos a 45 min |
| Ruido | Ventilador fijo a baja velocidad, sin cambios de ruido de madrugada |
| Red | Solo Ethernet al router; reserva DHCP en 192.168.1.200 |
| Alimentación | Adaptador 12 V / 5 A al HAT, detrás de un SAI con USB |
| Presupuesto | 150 € para lo que falta comprar (SAI y ventilador) |
| Discos | Se reutilizan los de casa; no se compran discos nuevos de momento |

### Hardware disponible

| Pieza | Modelo | Estado conocido |
|---|---|---|
| Placa | Raspberry Pi 5 8 GB + Active Cooler | Nueva |
| Controladora | Radxa Penta SATA HAT (JMB585) | Nueva |
| Sistema | Toshiba XG5 512 GB NVMe en caja USB 3 | Usado; SMART sin revisar |
| Paridad prevista | WD Blue 1 TB | Usado; candidato a paridad si pasa SMART |
| Datos | Toshiba MK1059 1 TB | Usado, de portátil; vigilar atributo 193 |
| Datos | Samsung QVO 1 TB | Usado, SSD QLC |
| Backup | Hitachi 320 GB en caja USB | Usado; se formatea para restic |

## 7. Seguridad y acceso

- Nunca se exponen a Internet el panel de OMV (8000), el panel de AIO (8080) ni SSH.
- Acceso desde fuera solo a Nextcloud, preferentemente con Tailscale (sin puertos abiertos).
- Un usuario por persona, todos en el grupo `familia`; sin acceso de invitados en Samba.
- Contraseñas, frase de acceso de AIO y contraseña del repositorio restic en el gestor de
  contraseñas, nunca en el repo ni en el NAS.
- Verificación en dos pasos en las cuentas de Nextcloud con acceso desde fuera.

## 8. Operación y mantenimiento

| Tema | Requisito |
|---|---|
| Actualizaciones | Mensuales, a mano, con un plan aprobado (UPD) y comprobación de discos tras cambio de kernel |
| Avisos | Correo al administrador para SMART, SnapRAID, SAI, sistema de ficheros y actualizaciones |
| Ventana de mantenimiento | Sábados de 10:00 a 13:00; nunca entre 02:30 y 05:00 (backup AIO y sync) |
| Revisión semanal | Informe de SnapRAID y backup diario de AIO |
| Revisión mensual | Backup restic al Hitachi, filtro de polvo, SMART 5/197/198/193 |
| Revisión semestral | Restauración de prueba, prueba del SAI, rotación de la copia fuera de casa |
| Responsable | Adulto 1; Adulto 2 sabe apagar el NAS y cambiar el disco de la copia exterior |

## 9. Supuestos y preguntas abiertas

### Supuestos

- Los tres discos de 1 TB pasan el test SMART largo antes de formatearlos.
- El router permite reservas DHCP por nombre de equipo.
- Los datos actuales caben en el pool con margen durante 3 años.

### Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Copia fuera de casa en disco rotado o en la nube? | Adulto 1 | 2026-11-15 |
| ¿Qué modelo de SAI con USB compatible con NUT? | Adulto 1 | 2026-10-31 |

## 10. Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-08 | Requirements Agent | Creación |
