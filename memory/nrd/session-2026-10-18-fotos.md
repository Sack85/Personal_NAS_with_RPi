# Sesión 2026-10-18 — Reorganización de las fotos

Entrada para el próximo `update-nrd` / `update-hld`. Todavía no es un entregable: persona 1 pidió
dejar los documentos para cuando Immich termine, pero que no se pierda nada de lo hablado.

## Medido en el NAS (solo lectura)

- `Imagenes`: ~405 GB. Vídeos 269 GB (3 525), fotos 130 GB (57 885), otros 5 GB (zip partidos).
- Repetidos con el mismo nombre y tamaño: 10 638 ficheros, ~117 GB (casi todo en `Imagenes/Carlos`).
- WhatsApp (`-WA` en el nombre): 10 410 ficheros, 7 GB.
- Los 700 vídeos más grandes (212 GB): 504 en H.264 a ~10 Mbps (ahorro estimado al pasar a H.265
  "sin pérdida visible": ~105 GB, ~50 %); 174 ya en HEVC (no compensa); unos pocos MJPEG, WMV y DV.
- Pool: 588 GiB ocupados (Documentos 210 GiB, Imagenes 378 GiB), 1,3 TB libres.
- Immich (dos bibliotecas externas sobre la misma carpeta → 122 386 elementos): tras ~14 h, 10 710
  miniaturas, 10 688 CLIP y 5 666 caras (~9 %); 71 °C y carga ~20. Con la configuración por defecto
  convierte los vídeos que no son H.264 (82 convertidos, 2,9 GB).

## Respuestas de persona 1

| # | Pregunta | Respuesta |
|---|---|---|
| 1 | Discos antiguos | 5 HDD USB de 2,5" de Sabrina con fotos y documentos; el de 750 GB es uno de ellos |
| 2 | Otras fuentes | Tarjetas SD y HDD; ninguna nube |
| 3 | Películas | No hay (los `.mkv` y vídeos largos son familiares) |
| 4 | RAW o escaneos | No |
| 5 | Vídeos sin comprimir | Ninguno |
| 6 | Fecha de "comunes" | Sin fecha exacta, ~10 años (propuesta: corte en 2016) |
| 7 | Cómo se miran | Immich; carpetas por evento deseables |
| 8 | Carpetas actuales | Conservar las que tienen nombre de evento; los volcados (p. ej. WhatsApp) se reordenan |
| 9 | Visibilidad | Cada uno ve todo, pero el otro no debe poder borrar fácilmente |
| 10 | Dos versiones | Se queda la mejor |
| 11 | Basura | Memes, capturas, tickets, ráfagas; las fotos de documentos van a una sección especial y se borran a mano |
| 12 | PCs | PC de Sabrina: 4 GB libres de 250 GB; los dos querrían todas las fotos en local |
| 13 | Tiempo | El mínimo: automatizar al máximo |

## Propuesta (pendiente de NRD → HLD → RBK)

1. Catálogo en solo lectura de cada disco y SD desde el PC (comparación por contenido).
2. El de 750 GB: su contenido único al NAS, test SMART y pasa a backup restic provisional
   (restic guarda una vez lo repetido); con el de 4 TB, pasa a copia fuera de casa.
3. Lo único del resto de discos y SD a `Imagenes/_Importar/<origen>/`.
4. Repetidos: se queda la mejor versión; el resto a cuarentena 2 meses, sin borrado inmediato.
5. Colocación automática: antes de 2016 → `Antiguas/<persona>` (según el origen); desde 2016 →
   `Familia/`; carpetas con nombre de evento se conservan con prefijo `AAAA-MM`; volcados por año/mes.
6. Todos los vídeos a H.265 en el PC (script que conserva fecha y GPS); Immich debe aceptar HEVC.
7. Immich analiza una sola vez el resultado, con una biblioteca y compartición de pareja (solo ver);
   memes/capturas a "Revisar"; fotos de documentos a una carpeta especial para revisar a mano.
8. Sincronización completa en los dos PCs cuando el de Sabrina tenga sitio (SSD de 1 TB o más).
