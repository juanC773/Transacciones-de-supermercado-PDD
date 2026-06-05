# Dataset de transacciones

Los archivos CSV del curso **no se versionan** en Git por su tamaño. Deben copiarse localmente antes de ejecutar el ETL.

## Estructura requerida

```
DataSet/
└── DataSet/
    ├── Transactions/
    │   ├── 102_Tran.csv
    │   ├── 103_Tran.csv
    │   ├── 107_Tran.csv
    │   └── 110_Tran.csv
    └── Products/
        ├── Categories.csv
        └── ProductCategory.csv
```

## Formato de transacciones

Archivos sin encabezado, separador `|`:

```text
fecha|tienda|id_cliente|item1 item2 item3 ...
2013-01-01|102|530|20 3 1
```

| Campo | Descripción |
|-------|-------------|
| fecha | `AAAA-MM-DD` |
| tienda | ID de punto de venta (102, 103, 107, 110) |
| id_cliente | Identificador del comprador |
| ítems | Números separados por espacio; repetición = más unidades |

### Interpretación de ítems por tienda

| Tienda | Significado de los números |
|--------|----------------------------|
| 102 | ID de categoría (1–50) |
| 103, 107, 110 | SKU de producto → mapeo a categoría vía `ProductCategory.csv` |

## Catálogo de productos

- **Categories.csv:** `id|nombre` — 50 categorías de producto
- **ProductCategory.csv:** `sku|categoria` — relación producto → categoría

## Ejemplos para probar ingestión

CSV pequeños (válidos y con errores) en [ejemplos-prueba/](ejemplos-prueba/README.md).  
Útiles para ver la validación en el front antes de subir y en la API al confirmar.

## Generación de agregados

Desde la raíz del proyecto:

```powershell
python -m src.etl.load_transactions
```

Salida en `data/processed/aggregates/` (ver [docs/instalacion.md](../docs/instalacion.md)).
