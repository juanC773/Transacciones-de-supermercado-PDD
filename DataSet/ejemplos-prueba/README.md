# CSV de prueba (ingestión)

Archivos pequeños para probar la validación en el dashboard (**+** en una tienda).  
La **misma validación** corre en el navegador al elegir el archivo y otra vez en la API al pulsar «Agregar al CSV».

## Tienda de ejemplo: 111

1. En el sidebar: **+ Nueva** → id `111`, nombre `Tienda Ejemplo Prueba`.
2. Pulsa **+** en esa tienda y sube uno de los archivos de esta carpeta.

| Archivo | Resultado esperado |
|---------|-------------------|
| `111_valido_ejemplo.csv` | OK — 10/10 líneas; columna tienda = `111` |
| `111_error_tienda_incorrecta.csv` | Error — filas con tienda `102` o `103` en columna 2 |
| `111_error_formato.csv` | Error — encabezado, fecha inválida, cliente no numérico, sin ítems |

## Probar tienda del curso (102)

Con la tienda **102** ya existente, sube `102_error_tienda_incorrecta.csv` al modal de la tienda 102.  
Debe fallar con mensaje del tipo: `tienda 103 debe ser 102`.

## Formato (igual que el dataset)

```text
fecha|tienda|id_cliente|item1 item2 ...
2013-01-15|111|5001|21 5 189
```

Columna 2 = **id numérico** de la tienda seleccionada en el modal (no el nombre visible).

## Después de un CSV válido

Pulsa **Procesar nuevos datos** en el sidebar para regenerar Parquet y ML.
