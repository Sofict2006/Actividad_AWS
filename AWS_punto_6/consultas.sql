-- Punto 6 · Glue Data Catalog + Athena (us-east-2)
-- Ejecutar en Athena, base de datos taller_aws_glue.
-- La base taller_aws_glue se creó en Glue -> Data Catalog -> Databases.

-- 1. Creación manual de la tabla (el crawler no se pudo crear por permisos)
CREATE EXTERNAL TABLE taller_aws_glue.pedidos (
  pedido_id  INT,
  cliente_id INT,
  categoria  STRING,
  total      BIGINT
)
ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION 's3://taller-aws-gr01-user3/glue/'
TBLPROPERTIES ('skip.header.line.count'='1');

-- Ver la definición registrada en el catálogo
SHOW CREATE TABLE taller_aws_glue.pedidos;

-- 2. Conteo (25 con pedidos_inicial.csv, 30 con pedidos_actualizado.csv)
SELECT COUNT(*) AS registros FROM taller_aws_glue.pedidos;

-- 3. Filtro: pedidos de alto valor
SELECT pedido_id, cliente_id, categoria, total
FROM taller_aws_glue.pedidos
WHERE total >= 150000
ORDER BY total DESC;

-- 4. Agrupación: pedidos y ventas por categoría
SELECT categoria, COUNT(*) AS pedidos, SUM(total) AS ventas
FROM taller_aws_glue.pedidos
GROUP BY categoria
ORDER BY ventas DESC;

-- 5. Limpieza
DROP TABLE taller_aws_glue.pedidos;
DROP DATABASE taller_aws_glue;
