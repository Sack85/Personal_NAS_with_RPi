# NRD — NAS familiar con Raspberry Pi 5

| Campo | Valor |
|---|---|
| **Documento** | NRD |
| **Versión** | 1.3 |
| **Estado** | Aprobado |
| **Fecha de creación** | 2026-10-08 |
| **Última modificación** | 2026-10-08 |
| **Autor** | Requirements Agent |
| **Responsable** | Persona 1 (administrador único del NAS, sin sustituto; decisión del usuario, 2026-10-08) |
| **Fuentes** | inputs/nrd/v1/guia-v2.md, sesión de preguntas 2026-10-08 |

## Resumen

NAS doméstico encendido 24/7 que se usa L-V 18:00-23:00 y fines de semana de día (fuera de ese
horario, discos parados y sin acceso desde fuera) y guarda unos 1 200 GB de documentos e imágenes de dos personas,
sincroniza sus 2 PC Windows y 2 móviles (fotos de los móviles con Immich; documentos y
sincronización a los PC con Nextcloud), y aguanta el fallo de un disco, un borrado accidental,
un ransomware y un desastre en casa (rayo, robo, inundación) sin perder más de un día de trabajo
en el pool ni más de un mes en el peor caso.

## 1. Contexto y objetivos

El NAS de 2020 (Raspberry Pi 4 + NextcloudPi) dependía de una tarjeta SD, no tenía copia fuera
de casa y se apagaba a diario. Se reconstruye con Raspberry Pi 5, el HAT Radxa Penta SATA y los
discos de 1 TB que ya hay en casa (guía v2, "Qué cambia respecto a la v1"). El disco Hitachi de
320 GB previsto en la guía para el backup se descarta: no cabe 1,2 TB y da problemas (decisión
del usuario, 2026-10-08).

### Fuera de alcance (proyecto futuro)

Raspberry Pi 4 aparte con Pi-hole y descarga de películas: descarga en su propio disco USB y
mueve las películas a la carpeta Vídeos del NAS, sin backup (decisión del usuario, 2026-10-08).
Este NRD y el HLD **solo** reservan para ella una IP fija en la red de casa y un acceso SMB
a Vídeos; su instalación y su configuración quedan fuera de este proyecto.

| Objetivo | Medida de éxito |
|---|---|
| No perder documentos ni imágenes | 0 ficheros perdidos en la restauración de prueba semestral desde restic |
| Sincronizar PC y móviles sin intervención | Fotos del álbum Cámara y del álbum WhatsApp de cada móvil en el pool (vía Immich) antes de las 08:00 del día siguiente, y en el D: de ambos PC (vía Nextcloud) en la siguiente sesión de uso |
| Limpieza de fotos sin pérdidas | 0 fotos borradas automáticamente: la limpieza solo mueve a "Revisar"; borra el usuario |
| Aguantar el fallo de un disco del pool | Reconstrucción con SnapRAID en ≤ 24 h desde que llega el disco nuevo |
| Actualizar sin sustos | 100 % de las actualizaciones con plan aprobado (UPD) y comprobación de discos posterior |
| Temperaturas seguras | Discos entre 25 y 40 °C (alarma a 45 °C), Pi < 70 °C y `get_throttled` = 0x0 (guía §1, §13) |
| Copia fuera de casa al día | Disco de backup fuera de casa con un snapshot restic de ≤ 31 días |
| Acceso de emergencia | Persona 2 descarga desde su propia cuenta de Nextcloud un documento y una foto de persona 1 sin ayuda técnica (prueba semestral) |
| Consumo fuera de horario | Discos parados ≥ 90 % de las horas sin uso y 0 accesos desde fuera en esas horas; consumo en W lo fija el HLD |

## 2. Usuarios y dispositivos

| Usuario | Dispositivos | Uso principal | Acceso desde fuera |
|---|---|---|---|
| Persona 1 (administrador) | PC Windows (cliente Nextcloud), móvil (app Immich) | Documentos, imágenes, administración del NAS | Sí, solo Nextcloud e Immich y vía Tailscale |
| Persona 2 | PC Windows (cliente Nextcloud), móvil (app Immich) | Documentos e imágenes; con su cuenta ve todo lo de persona 1 (sección 7.1) | Sí, solo Nextcloud e Immich y vía Tailscale |

### 2.1 Móviles: copia de fotos con Immich (Prioridad Media)

- App Immich en cada móvil con copia automática **solo** del álbum Cámara y del álbum WhatsApp.
- Las fotos subidas quedan **dentro del pool**, protegidas por SnapRAID y restic, y en una
  carpeta bajo Imágenes que Nextcloud sincroniza a los PC (sección 4.1).
- Limpieza **automática** de memes, comida y capturas de pantalla: una tarea programada usa la
  búsqueda inteligente de Immich y **mueve** lo detectado al Archivo / álbum "Revisar".
  **Nunca borra automáticamente**: el usuario revisa y borra. Mismo tratamiento para las fotos
  de WhatsApp ya existentes en Imágenes.

### 2.2 PC: cliente Nextcloud (Prioridad Alta)

- Documentos: cada persona sincroniza completos **solo sus** documentos; los de la otra se
  consultan en solo lectura vía web o bajo demanda, sin sincronizarlos.
- Imágenes: sincronización **completa** en los 2 PC (~756 GB hoy, +40–100 GB/año).
- Espacio libre en D: de cada PC: Imágenes + sus Documentos ≈ 966 GB hoy y ≈ 1 296 GB a 3 años
  (756 + 3 × 100 de Imágenes; 210 + 3 × 5 de Documentos) más un 10 % de margen
  [PENDIENTE: medir espacio libre y tamaño del D: de cada PC — responsable: Persona 1, fecha: 2026-10-31].
- Las copias de los PC son copias adicionales, **no sustituyen a restic**: un borrado o un
  ransomware se propaga por la sincronización (sección 5).

## 3. Datos y capacidad

| Carpeta | Contenido | Volumen actual (GB) | Crecimiento anual (GB) | Criticidad | Fuente del dato |
|---|---|---|---|---|---|
| Documentos (persona 1) | Documentos personales y de trabajo (D:\ del PC) | 210 | 5 | Irreemplazable | Medido con `du` el 2026-10-08 |
| Imágenes (persona 1) | Fotos y vídeos propios (D:\ del PC y móvil); crecimiento 20–50 GB/año, se toma el máximo | 378 | 50 | Irreemplazable | Medido con `du` el 2026-10-08 |
| Documentos (persona 2) | Documentos personales | 210 | 5 | Irreemplazable | Estimado igual a persona 1; estimación aceptada por el usuario (2026-10-08) |
| Imágenes (persona 2) | Fotos y vídeos propios; crecimiento 20–50 GB/año, se toma el máximo | 378 | 50 | Irreemplazable | Estimado igual a persona 1; estimación aceptada por el usuario (2026-10-08) |
| Datos de Immich | Base de datos (álbumes, caras, "Revisar") y miniaturas/vídeos recodificados; las subidas de los móviles van dentro de Imágenes, no aquí | 40 | 5 | Mixta (base de datos: se respalda, rehacerla cuesta días de clasificación; miniaturas: reemplazables) | Supuesto: ~5 % de 756 GB de Imágenes; se mide tras la primera clasificación |
| Vídeos (películas) | Películas de la futura Pi 4 de descargas (fuera de alcance, sección 1) | 0 | 0 | Reemplazable, sin backup | Carpeta vacía hasta el proyecto futuro, que fijará su cuota |

Total actual: ~1 176 GB (≈ 1,2 TB) de datos + ~40 GB de Immich. Crecimiento de imágenes
40–100 GB/año entre las dos personas (dato del usuario); el de documentos (5 GB/año por
persona) y el de Immich (5 GB/año) son supuestos. La primera limpieza no reduce el volumen:
mueve a "Revisar", y solo baja si el usuario borra.

Capacidad necesaria a 3 años: 1 561 GB (1 216 GB actuales + 3 × 115 GB/año en el peor caso),
frente a ~2 000 GB del pool previsto en la guía (§7, dos discos de datos de 1 TB). Ocupación
inicial ~61 %, ~78 % a 3 años; con el peor crecimiento el pool se llena en 5–6 años, así que
hay que prever ampliación antes de ese plazo. Vídeos no entra en el cálculo: cuando exista,
tendrá cuota propia para no llenar el pool con datos sin backup.

Backup: el repositorio restic (Documentos, Imágenes y base de datos de Immich; sin miniaturas
ni Vídeos) ronda 1 200 GB hoy y ~1 550 GB a 3 años, sin contar versiones: cabe en el disco USB
de ≥ 2 TB; el HLD comprueba el margen con 12 versiones mensuales.

## 4. Servicios

| Servicio | Para qué | Usuarios | Prioridad |
|---|---|---|---|
| Samba (SMB) | Carpetas de red en los PC Windows | Persona 1, persona 2 | Obligatorio |
| Nextcloud AIO | Documentos y compartición; sincronizar los PC (sus Documentos e Imágenes completas, sección 2.2); papelera y versiones ≥ 30 días | Persona 1, persona 2 | Obligatorio |
| Immich | Copia de fotos de los móviles, búsqueda inteligente, caras y limpieza a "Revisar" (sección 4.1) | Persona 1, persona 2 | Prioridad Media |
| SnapRAID + MergerFS | Paridad diaria y un único pool de datos | Sistema | Obligatorio |
| restic a disco USB externo | Backup versionado offline y copia fuera de casa | Administrador | Obligatorio |
| Tailscale | Acceso a Nextcloud desde fuera sin abrir puertos | Persona 1, persona 2 | Obligatorio |
| NUT | Apagado limpio con el SAI en cortes de luz | Sistema | Obligatorio |
| Avisos por correo | SMART, SnapRAID, SAI y actualizaciones | Administrador | Obligatorio |
| hd-idle | Spindown de los discos mecánicos a 30–45 min | Sistema | Obligatorio |
| Horario de funcionamiento | Encendido 24/7, discos parados y sin acceso exterior fuera del horario de uso (sección 6.1) | Sistema | Prioridad Media |
| Compartición entre cuentas | Imágenes compartidas en lectura y escritura; Documentos de cada uno visibles en solo lectura para el otro (sección 7.1) | Persona 1, persona 2 | Prioridad Alta |
| Monitorización de temperatura | Temperatura SMART de los discos con alarma a 45 °C y aviso/apagado (sección 6.2) | Sistema | Prioridad Alta |
| Acceso SMB para la futura Pi 4 | IP fija reservada y usuario SMB propio con escritura solo en Vídeos (sección 1, fuera de alcance) | Pi 4 de descargas | Prioridad Baja |

### 4.1 Immich (Prioridad Media)

- Biblioteca externa = la carpeta Imágenes existente, **sin duplicar** fotos; se pueden excluir
  rutas de la biblioteca.
- Búsqueda inteligente y reconocimiento de caras.
- Las subidas de los móviles (sección 2.1) se guardan en el pool, dentro de Imágenes, en una
  carpeta que Nextcloud sincroniza a los PC; nunca solo en el SSD del sistema.
- Primera clasificación pesada: puede tardar **días** en la Pi; opción de ejecutar el
  aprendizaje automático en el PC (ML remoto) para acelerarla. El HLD decide y fija cómo se
  limita para respetar 6.1 y 6.2.
- La base de datos de Immich entra en el backup (restic); las miniaturas pueden excluirse
  porque se regeneran.
- Tarea programada de limpieza (sección 2.1): solo mueve a Archivo / álbum "Revisar", nunca borra.
## 5. Protección de datos

En lenguaje llano: el **RPO** responde a "si pasa algo, ¿de cuándo es la última copia buena?",
es decir, cuánto trabajo reciente se puede perder (24 h = como mucho lo hecho desde la noche
anterior; 1 mes = como mucho lo hecho desde la última copia mensual). El **RTO** responde a
"¿cuánto tardo en volver a tenerlo todo funcionando?". El usuario acepta márgenes holgados
("tranquilidad, meses"): el RPO de 1 mes de la copia externa queda aceptado y un RTO de días o
semanas es aceptable en todos los escenarios; los RTO de la tabla son objetivos, no límites
duros (decisión del usuario, 2026-10-08). SnapRAID no es un backup.

| Escenario | Datos afectados | RPO | RTO | Cómo se cubre |
|---|---|---|---|---|
| Fallo de un disco de datos | Lo guardado en ese disco | 24 h (último sync diario, en horario según 6.1) | 24 h desde que llega el disco | SnapRAID: disco nuevo + reconstrucción |
| Fallo del disco de paridad | Ninguno | 0 | 48 h | Disco nuevo + sync completo |
| Borrado accidental | Ficheros borrados (también los que la sincronización propaga a los PC) | 24 h | 1 h | Umbral de 50 borrados que frena el sync, SnapRAID, papelera y versiones de Nextcloud ≥ 30 días, restic |
| Ransomware o cifrado | Todo lo accesible por red y las copias de los PC (la sincronización lo propaga) | 1 mes | 48 h | restic al disco USB desconectado, 12 versiones mensuales; versiones de Nextcloud ≥ 30 días como primer recurso |
| Error de la limpieza automática de Immich | Fotos mal clasificadas como memes/comida/capturas | 0 | 1 h | La tarea solo mueve a "Revisar", nunca borra; el usuario las devuelve |
| Pérdida de la base de datos de Immich | Álbumes, caras y "Revisar" (las fotos están en Imágenes) | 1 mes | Días (reclasificación) | restic de la base de datos de Immich |
| Rayo, robo o inundación | Todo el NAS | 1 mes | 1 semana | Disco USB de backup guardado fuera de casa entre copias |
| Fallo del SSD del sistema | Sistema y datos de Nextcloud | 24 h | 24 h | Backup diario de AIO en el pool + reinstalación según RBK |

## 6. Entorno y restricciones

| Restricción | Valor |
|---|---|
| Clima de la sala | Verano: 35 °C y 90 % HR (dato del usuario, 2026-10-08). Ver requisito 6.2 (Alta) |
| Ubicación | Ventilada y lejos del sol directo; ni en el suelo, ni en mueble cerrado, ni bajo el aire acondicionado (guía §1) |
| Funcionamiento | Encendido 24/7; uso real L-V 18:00-23:00 y fines de semana de día; ver 6.1 |
| Ruido | Ventilador de 120 mm a velocidad fija baja, sin cambios de madrugada (guía §13.1) |
| Red | Solo Ethernet al router; sin WiFi |
| Alimentación | Adaptador 12 V / 5 A al HAT, detrás de un SAI con USB compatible con NUT (no se sabe si hay SAI; ver Preguntas abiertas) |
| Apagado por corte | NUT apaga el NAS si la luz falta más de 5 min (guía §12) |
| Presupuesto | Disco USB externo de backup ≥ 2 TB: 60–80 €; SAI, si no hay uno: 60–90 €; resto [PENDIENTE: presupuesto de ventilador activo y caja (6.2) — responsable: Persona 1, fecha: 2026-10-31] |
| Copias en la nube | No se usan (decisión del usuario, 2026-10-08) |

### 6.1 Horario de funcionamiento (Prioridad Media)

Decisión del usuario (2026-10-08): **encendido 24/7** con discos parados por hd-idle y
**corte del acceso exterior (Tailscale) fuera del horario de uso**. Se descarta el apagado
programado con despertar por el RTC del Pi 5.

- El NAS está encendido 24/7; en horas sin uso (L-V 23:00-18:00; fines de semana de noche) los
  discos mecánicos están parados por hd-idle salvo durante las tareas programadas.
- En horas sin uso el NAS **no es accesible desde fuera de casa** (Tailscale cortado); en la red
  de casa sigue disponible.
- Las tareas programadas (SnapRAID sync/scrub, backup diario de AIO, restic) deben caer dentro
  del horario de uso o pegadas a él (p. ej. justo al terminar, 23:00-01:00), no a las 03:00-05:00,
  para no despertar los discos de madrugada. La tarea de limpieza de Immich sigue la misma regla.
- Excepción temporal: la primera clasificación de Immich (días) puede mantener los discos
  activos fuera de horario; el HLD decide si se trocea por horario o se hace con ML remoto.
- El HLD define cómo se implementa el corte por horario (mecanismo, programación y vuelta atrás),
  el consumo estimado en W y kWh/año, y cómo afecta a NUT.

### 6.2 Temperatura y humedad (Prioridad Alta)

Rebajado de CRÍTICO a Alta (decisión del usuario, 2026-10-08): en La Reunión los portátiles
funcionan años sin problema en estas condiciones. **No bloquea la puesta en producción.**

- Riesgo que se mantiene: con 35 °C de ambiente los discos pueden superar 40 °C (objetivo
  25–40 °C, alarma a 45 °C), y los HDD toleran peor el calor y la humedad que un portátil: por
  encima de 40 °C aumentan los fallos y se acorta la vida útil. Con 90 % HR hay riesgo de
  condensación y corrosión en placa, conectores y discos.
- Mitigación obligatoria:
  - Monitorizar la temperatura SMART de cada disco con alarma a 45 °C, aviso por correo y
    apagado limpio si se mantiene (umbral y tiempo de apagado los fija el HLD).
  - Ventilador activo en la caja.
  - Ubicación ventilada y lejos del sol directo.
  - Medir temperatura y humedad de la sala en verano (higrómetro) y revisar este requisito con
    el dato.

### Hardware disponible

| Pieza | Modelo | Estado conocido |
|---|---|---|
| Placa | Raspberry Pi 5 8 GB + Active Cooler | SMART no aplica; estado a confirmar en el primer arranque |
| Controladora | Radxa Penta SATA HAT (JMB585) | A confirmar en el primer arranque |
| Sistema | Toshiba XG5 512 GB NVMe en caja USB 3 | Usado; SMART pendiente |
| Disco 1 TB | WD Blue 1 TB | Usado; SMART pendiente (test largo) |
| Disco 1 TB | Toshiba MK1059 1 TB | Usado, de portátil; SMART pendiente, vigilar atributo 193 |
| Disco 1 TB | Samsung QVO 1 TB (SSD QLC) | Usado; SMART pendiente, vigilar desgaste |
| Backup | Disco USB externo ≥ 2 TB | Por comprar (60–80 €) |
| SAI | Con USB compatible con NUT | [PENDIENTE: confirmar si hay SAI y su modelo, o presupuestarlo (60–90 €) — responsable: Persona 1, fecha: 2026-10-31] |
| Descartado | Hitachi 320 GB | No se usa: capacidad insuficiente para 1,2 TB |

## 7. Seguridad y acceso

- Nunca se exponen a Internet el panel de OMV (8000), el panel de AIO (8080) ni SSH.
- No se abre ningún puerto en el router (tampoco 443): el acceso desde fuera es solo por Tailscale.
- Desde fuera solo se usan Nextcloud e Immich, siempre vía Tailscale; cada dispositivo con
  acceso exterior lleva la app de Tailscale. Nunca se publica Immich en Internet.
- Un usuario por persona; sin acceso de invitados en Samba. La futura Pi 4 (fuera de alcance)
  tiene su propio usuario SMB con escritura solo en Vídeos.
- Si se usa ML remoto de Immich en el PC, solo dentro de la red de casa.
- Contraseñas, frase de acceso de AIO, contraseña del repositorio restic y claves de Tailscale
  en el gestor de contraseñas, nunca en el repo; la contraseña de restic, además, fuera del NAS.
- El disco de backup está desconectado del NAS salvo durante la copia mensual.
- Fuera del horario de uso (6.1) el NAS no es accesible desde fuera de casa.

### 7.1 Compartición y acceso de emergencia (Prioridad Alta)

El administrador es único y no tiene sustituto. El acceso de emergencia se simplifica
(decisión del usuario, 2026-10-08): la compartición diaria entre cuentas ya da a persona 2
(su mujer) acceso a todo **sin conocimientos técnicos**.

- Cada persona tiene su propia cuenta de Nextcloud.
- Imágenes: carpeta totalmente compartida, lectura y escritura para ambos.
- Documentos: cada persona ve y descarga los documentos de la otra en solo lectura; solo el
  dueño los modifica.
- Herencia: con su propia cuenta, persona 2 ya accede a todos los Documentos e Imágenes de
  persona 1; no hace falta cuenta de emergencia aparte.
- Hoja impresa sencilla, sin contraseñas, guardada en lugar conocido por persona 2: cómo entrar
  en Nextcloud y descargarlo todo, y cómo leer el disco USB de backup.
- La contraseña del repositorio restic, en el gestor de contraseñas con acceso de emergencia a
  favor de persona 2.
- Prueba semestral: persona 2 descarga un documento y una foto de persona 1.

## 8. Operación y mantenimiento

| Tema | Requisito |
|---|---|
| Actualizaciones | Mensuales, a mano, con plan aprobado (UPD); comprobar `lsblk` tras cambio de kernel (guía §4.5) |
| Avisos | Correo al administrador para SMART, SnapRAID, SAI y actualizaciones |
| Ventana de mantenimiento | Dentro del horario de uso (6.1) y nunca a la vez que el backup de AIO o el sync de SnapRAID |
| Revisión semanal | Informe de SnapRAID por correo y backup diario de AIO terminado |
| Revisión mensual | Traer el disco USB, backup restic + check, llevarlo de nuevo fuera de casa; filtro de polvo; SMART 5/197/198/193 |
| Revisión semestral | Restauración de prueba desde restic, prueba del SAI desenchufándolo y prueba de acceso de emergencia de persona 2 (7.1) |
| Revisión de verano | Temperatura de discos (alarmas de 45 °C del periodo) y medida de temperatura y humedad de la sala según 6.2 |
| Responsable | Persona 1, único, sin sustituto (decisión del usuario, 2026-10-08); cubre la ausencia el requisito 7.1 |

## 9. Supuestos y preguntas abiertas

### Supuestos

- Las carpetas de la persona 2 ocupan lo mismo que las de la persona 1 (~588 GB): estimación aceptada por el usuario (2026-10-08) sin medir.
- El crecimiento de Documentos es de 5 GB/año por persona.
- RPO y RTO de cada escenario son los de la guía (sync diario, restic mensual); el usuario acepta el RPO de 1 mes de la copia externa y RTO de días o semanas en todos los escenarios (2026-10-08).
- Riesgo aceptado: calor y humedad de la sala en verano, mitigados según 6.2 sin bloquear la puesta en producción.
- Los tres discos de 1 TB pasan el test SMART largo; si alguno falla, el pool de ~2 TB no existe y hay que revisar la capacidad.
- Riesgo aceptado: un único disco USB de backup hace de copia offline y de copia fuera de casa; durante la copia mensual no hay copia fuera de casa. Mejora futura: segundo disco USB rotatorio (guía §11.4).
- El responsable del NAS es la persona 1, sin sustituto.
- El disco de backup se guarda fuera de casa en casa de un familiar o en el trabajo (al usuario le es indiferente).

- Datos de Immich ~40 GB (~5 % de Imágenes) + 5 GB/año; se mide tras la primera clasificación.
- La Pi 5 de 8 GB soporta Immich junto a Nextcloud AIO; la primera clasificación tarda días.
- Las subidas de los móviles y el acceso a Immich desde fuera van por Tailscale, igual que Nextcloud.
- Las fotos de WhatsApp ya existentes están dentro de Imágenes (ya contadas en los 756 GB).

### Preguntas abiertas

| Pregunta | Responsable | Fecha límite |
|---|---|---|
| ¿Hay SAI en casa? Si sí, modelo y si tiene USB compatible con NUT; si no, presupuestarlo (60–90 €; el usuario está mirando precios) | Persona 1 | 2026-10-31 |
| ¿Humedad y temperatura medidas con higrómetro en la sala del NAS en verano? (no bloquea; revisa 6.2) | Persona 1 | 2027-02-28 |
| ¿Tamaño y espacio libre del D: de cada PC? Debe caber ≈ 1 296 GB a 3 años + 10 % (sección 2.2) | Persona 1 | 2026-10-31 |

## 10. Historial de versiones

| Versión | Fecha | Autor | Cambio |
|---|---|---|---|
| 1.0 | 2026-10-08 | Requirements Agent | Creación |
| 1.1 | 2026-10-08 | Requirements Agent | Persona 2 estimada aceptada; clima 35 °C/90 % HR con requisito crítico 6.2; SAI como pregunta abierta; RPO/RTO explicados y aceptados; responsable único y requisito de acceso de emergencia 7.1; segundo disco USB como mejora futura y riesgo aceptado; ubicación de la copia exterior; requisito de horario de funcionamiento 6.1 |
| 1.2 | 2026-10-08 | Requirements Agent | RPO/RTO holgados aceptados; 6.1: encendido 24/7 + hd-idle + corte de Tailscale fuera de horario, descartado apagado por RTC; 6.2 rebajado de CRÍTICO a Alta con mitigación obligatoria (alarma SMART 45 °C, ventilador, ubicación ventilada, medición en verano); 7.1 simplificado a compartición entre cuentas (Imágenes lectura/escritura, Documentos solo lectura), hoja impresa sin contraseñas y prueba semestral; SAI sigue abierto (presupuestar) |
| 1.3 | 2026-10-08 | Requirements Agent | Nuevo servicio Immich (Media): biblioteca externa sobre Imágenes, búsqueda inteligente y caras, subidas de móviles en el pool y en carpeta sincronizada; móviles con copia de Cámara y WhatsApp y limpieza automática a "Revisar" sin borrar; PC con cliente Nextcloud (solo sus Documentos, Imágenes completas, requisito de espacio en D:); papelera y versiones de Nextcloud ≥ 30 días; Nextcloud para documentos y compartición; capacidad a 3 años 1 561 GB; escenarios de protección nuevos; Pi 4 de Pi-hole/descargas fuera de alcance (solo IP y SMB a Vídeos) |
| 1.3 | 2026-10-08 | Requirements Agent | Estado cambiado a Aprobado |
