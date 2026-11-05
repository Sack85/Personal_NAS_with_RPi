# Excepción puntual — arreglo de mtime en Nextcloud (2026-11-05)

Persona 1 eligió la opción A (orden puntual, sin RBK) para los dos `Leerme.htm` con mtime -1243042226
en `oc_filecache` (diagnóstico en `session-2026-11-02.md`).

```
occ files:scan --path='carlos/files/Mis Documentos/Estudios/Apuntes Universidad/6 OPTATIVAS/Fundamentos de Programacion'
→ 79 carpetas, 916 ficheros, Updated 2, Errors 0
oc_filecache: filas con mtime<=0 o storage_mtime<=0 = 0 (de 264437); los dos Leerme.htm → 2026-10-19 23:38:00
```

Pendiente: comprobar en el cliente del PC que desaparece el bucle de sincronización y el aviso de
«fecha de modificación inválida». Si se repite con otros ficheros, escribirlo como paso del RBK 10.
