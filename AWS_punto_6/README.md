# Punto 6 · AWS Glue Data Catalog y Athena

Se subió a S3 un CSV de **25 pedidos**, se registró en Glue Data Catalog y se consultó desde Athena con un **filtro** y una **agrupación**. Luego se reemplazó el archivo por uno de **30 pedidos** y el conteo pasó de 25 a 30 sin tocar la tabla. El crawler no se pudo crear porque el usuario del curso no tiene permisos de crawlers (`glue:CreateCrawler`, captura 6.4), así que la tabla se definió **manualmente** con `CREATE EXTERNAL TABLE`. Esa limitación sirve como base de la comparación crawler vs. tabla manual.

## Contenido de la carpeta

| Archivo | Qué es |
| --- | --- |
| `datos/pedidos_inicial.csv` | 25 registros (`pedido_id`, `cliente_id`, `categoria`, `total`) |
| `datos/pedidos_actualizado.csv` | Los mismos 25 + 5 nuevos (30 registros) |
| `consultas.sql` | `CREATE EXTERNAL TABLE`, consultas de Athena y limpieza |
| `evidencias/` | Capturas numeradas (6.1 a 6.9) |

## 1. Qué almacena Glue Data Catalog

El catálogo guarda **metadatos**: bases de datos, tablas, columnas y tipos, formato, delimitador, particiones y la **ubicación en S3** de los archivos. Los registros siguen en S3: crear una tabla no copia los datos al catálogo. Athena lee la definición en el catálogo y escanea los archivos de S3 en cada consulta.

- **Base de datos:** agrupa tablas relacionadas (`taller_aws_glue`).
- **Tabla:** describe la estructura y la ubicación de un conjunto de archivos (`pedidos` → `s3://.../glue/`).
- **Crawler:** recorre un origen de datos, infiere el esquema y crea o actualiza tablas del catálogo; se ejecuta bajo demanda o programado, con un rol IAM que puede leer el origen.

## 2. Cómo reproducirlo

1. Crear un bucket en us-east-2 y subir el archivo con la clave `glue/pedidos.csv`:

```powershell
aws s3 cp .\datos\pedidos_inicial.csv s3://<bucket>/glue/pedidos.csv --region us-east-2
```

2. En **Glue → Data Catalog → Databases → Add database**, crear `taller_aws_glue` (captura 6.2).
3. **Con crawler** (lo que pide el enunciado): fuente `s3://<bucket>/glue/`, un rol con `AWSGlueServiceRole` + lectura del bucket, destino `taller_aws_glue`, frecuencia *On demand* → **Run** (configuración en la captura 6.3).
4. **Sin permisos de crawler** (lo que se hizo): en Athena, configurar la ubicación de resultados y ejecutar el `CREATE EXTERNAL TABLE` de `consultas.sql` (captura 6.5a).
5. Ejecutar el conteo, el filtro y la agrupación de `consultas.sql` (capturas 6.7).
6. Reemplazar el archivo manteniendo la misma clave y repetir las consultas (capturas 6.8 y 6.9):

```powershell
aws s3 cp .\datos\pedidos_actualizado.csv s3://<bucket>/glue/pedidos.csv --region us-east-2
```

## 3. Esquema y correcciones

La definición registrada (captura 6.5b, `SHOW CREATE TABLE`) es:

| Columna | Tipo |
| --- | --- |
| `pedido_id` | int |
| `cliente_id` | int |
| `categoria` | string |
| `total` | bigint |

Delimitador `,`, ubicación `s3://taller-aws-gr01-user3/glue` y `skip.header.line.count = 1`.

Correcciones aplicadas al definir la tabla, que son los errores típicos que habría que revisar en lo que infiere un crawler:

- **Encabezado:** sin `skip.header.line.count = 1` la fila de títulos se leería como un registro más (o el crawler nombraría las columnas `col0`, `col1`…).
- **Tipos numéricos:** IDs como `int` y `total` como `bigint` para poder filtrar `total >= 150000` y sumar sin convertir texto.
- **Ubicación:** la tabla apunta a la **carpeta** `glue/`, no al archivo; por eso solo debe haber un CSV en ese prefijo, o Athena contaría filas de varios archivos.

Además se comprobó un detalle de la carga: el primer intento de subida por consola no se completó y Athena devolvió **0 registros con 0 bytes escaneados**. El archivo se subió de nuevo por CLI y el conteo dio 25.

## 4. Consultas y resultados reales

| Consulta | Pregunta | Con 25 registros | Con 30 registros |
| --- | --- | --- | --- |
| `COUNT(*)` | ¿Cuántos pedidos hay? | 25 (6.7a) | 30 (6.9a) |
| Filtro `total >= 150000` | ¿Qué pedidos son de alto valor? | 6 pedidos (6.7b) | 8 pedidos (6.9b) |
| Agrupación por categoría | ¿Cuántos pedidos y cuánto vendió cada categoría? | 6.7c | 6.9c |

| Categoría | Pedidos (25) | Ventas (25) | Pedidos (30) | Ventas (30) |
| --- | --- | --- | --- | --- |
| Tecnologia | 8 | 1.425.000 | 10 | 1.775.000 |
| Hogar | 8 | 617.000 | 10 | 783.000 |
| Libros | 9 | 383.000 | 10 | 435.000 |

**Interpretación:**

- **Filtro:** los 6 pedidos de 150.000 o más son todos de *Tecnologia*; con la actualización entran dos más (29 y 26), también de *Tecnologia*. Los pedidos costosos se concentran en esa categoría.
- **Agrupación:** *Libros* tiene más pedidos (9) pero es la que menos vende, porque sus pedidos son baratos; *Tecnologia* vende casi 4 veces más que *Libros* con menos pedidos. Tras la actualización las tres categorías quedan con 10 pedidos y el orden por ventas no cambia.

## 5. Agregar registros y actualizar el catálogo

El conteo pasó de 25 a 30 **sin modificar la tabla**: el catálogo solo guarda la descripción y la ubicación, y Athena lee el archivo de S3 en cada consulta. Como el archivo nuevo tiene las mismas columnas, la definición registrada sigue siendo válida y no hubo que actualizarla. Si el esquema cambiara (una columna nueva, otro tipo), habría que actualizar la tabla: volviendo a ejecutar el crawler o con `ALTER TABLE` / recreando la tabla manual.

## 6. Crawler frente a tabla manual

| | Crawler | Tabla manual (`CREATE EXTERNAL TABLE`) |
| --- | --- | --- |
| Esquema | Lo infiere solo | Hay que escribir columnas, tipos, delimitador, encabezado y ubicación |
| Riesgo | Puede equivocarse (encabezados, tipos) y hay que revisar | Control exacto; los errores son de quien la escribe |
| Cambios de esquema | Se detectan al volver a ejecutarlo | Hay que modificar la tabla a mano |
| Permisos | Crear y ejecutar crawlers + un rol que lea S3 | Solo permisos de Glue/Athena para crear tablas |
| Costo | Cada ejecución se cobra en DPU-hora | Gratis (solo la consulta DDL en Athena) |

En este taller la tabla manual fue la única opción por permisos, y para un CSV pequeño y estable resultó suficiente. El crawler conviene cuando hay muchos archivos, particiones o esquemas que cambian.

## 7. ¿Se necesita un secreto?

No. S3, Glue y Athena se autorizan con los **permisos IAM** de la identidad que ejecuta las operaciones; no hay contraseña de base de datos ni credencial de aplicación. Se usaría Secrets Manager si se añadiera una conexión que sí la requiere, por ejemplo una conexión JDBC de Glue a una base de datos.

## 8. Preguntas de costos

- **Crawler:** se cobra por DPU-hora (0,44 USD) mientras se ejecuta, por segundo y con un mínimo por ejecución; dos ejecuciones cortas con 1 DPU rondarían 0,15 USD. En este taller **no se ejecutó** (0 USD).
- **Catálogo:** el primer millón de objetos almacenados y el primer millón de solicitudes al mes son gratis; aquí se usaron 1 base y 1 tabla.
- **S3:** almacenamiento por GB-mes y solicitudes; con archivos de 512 B y 611 B el costo es despreciable. Los resultados de Athena también ocupan S3.
- **Athena:** 5 USD por TB escaneado. Cada consulta escaneó 0,50 KB (25 registros) o 0,60 KB (30 registros); aun aplicando un mínimo de 10 MB por consulta, serían unos 0,00005 USD.
- **Efecto del volumen:** el costo de Athena crece en proporción a los bytes escaneados. Con datos grandes conviene filtrar por particiones, seleccionar solo las columnas necesarias y usar formatos comprimidos y columnares como Parquet.

## 9. Eliminación

Se borraron la tabla `pedidos`, la base `taller_aws_glue`, los objetos de S3 y el bucket. El crawler nunca llegó a existir. El rol `AWSGlueServiceRole-taller` no se pudo borrar (`iam:DeleteRole` denegado); no genera costo y se pidió al profesor eliminarlo.

## 10. Evidencias

| N.º | Captura |
| --- | --- |
| 6.1 | `glue/pedidos.csv` de 25 registros (512 B) en S3 |
| 6.2 | Base de datos `taller_aws_glue` |
| 6.3 | Configuración del crawler |
| 6.4 | Error al crear el crawler (`glue:CreateCrawler`) |
| 6.5a | `CREATE EXTERNAL TABLE` ejecutado en Athena |
| 6.5b | `SHOW CREATE TABLE` (esquema registrado) |
| 6.6 | Error al listar tablas en la consola de Glue (`glue:SearchTables`) |
| 6.7a–c | Conteo, filtro y agrupación con 25 registros |
| 6.8 | Archivo actualizado de 30 registros (611 B), misma clave |
| 6.9a–c | Conteo, filtro y agrupación con 30 registros |
