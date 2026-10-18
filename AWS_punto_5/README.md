# Punto 5 · Amazon Redshift

El punto quedó **preparado pero sin poder desplegarse**. Se hicieron la cotización, el conjunto de datos, el programa en Boto3 con la Data API, el bucket y el rol IAM para el `COPY`. Redshift no se pudo crear porque el usuario del curso (`de-gr01-user-3`) no tiene ningún permiso de `redshift-serverless` ni de `redshift` en ninguna región (capturas 5.5 a 5.7). Los resultados de la sección 6 son **los esperados**, calculados a partir de los CSV; **no se obtuvieron en Redshift**.

## Contenido de la carpeta

| Archivo | Qué es |
| --- | --- |
| `redshift_taller.py` | Sube los CSV a S3, crea las tablas, carga con `COPY` y ejecuta las consultas con la Data API usando el secreto de Secrets Manager |
| `datos/clientes.csv` | 10 clientes (`cliente_id`, `nombre`, `ciudad`) |
| `datos/pedidos_inicial.csv` | 25 pedidos (`pedido_id`, `cliente_id`, `categoria`, `total`), relacionados por `cliente_id` |
| `politicas/confianza_rol_redshift.json` | Política de confianza del rol `RedshiftS3-taller-user3` |
| `politicas/politica_bucket.json` | Política del bucket que le da lectura al rol |
| `diagnostico_permisos.py` | Revisa, solo con lecturas, qué permisos tiene el usuario en 4 regiones |
| `evidencias/` | Capturas numeradas (5.1 a 5.7) |

## 1. Qué es Redshift y frente a RDS

Amazon Redshift es un almacén de datos administrado para **análisis** sobre grandes volúmenes: guarda los datos por columnas y reparte el cómputo en paralelo, lo que acelera consultas que filtran, unen y agregan muchas filas. Sus componentes principales son el cómputo (nodos de un clúster aprovisionado o RPU en Serverless), el almacenamiento administrado, las bases de datos y tablas, los roles IAM para leer otras fuentes como S3 y las herramientas de consulta (Query Editor v2, Data API, clientes SQL). En Serverless, el **namespace** agrupa bases de datos, usuarios y almacenamiento, y el **workgroup** aporta el cómputo y la red.

| | Redshift | RDS |
| --- | --- | --- |
| Carga de trabajo | Analítica (OLAP): pocas consultas grandes | Transaccional (OLTP): muchas operaciones pequeñas |
| Almacenamiento | Columnar, comprimido | Por filas |
| Caso típico | Ventas por ciudad y categoría de los últimos 3 años | Registrar una compra y consultar el pedido de un cliente en una app |

## 2. Modalidad y costo

Cotización en AWS Pricing Calculator, us-east-2, misma base para las dos (2 h diarias durante un mes; captura 5.1):

| Modalidad | Configuración | Mensual (2 h/día) | Por hora |
| --- | --- | --- | --- |
| Serverless | Base 4 RPU, 1 GB de almacenamiento administrado | 87,86 USD | ≈ 1,44 USD (4 RPU × ~0,36 USD/RPU-h) |
| Aprovisionado | 1 nodo `dc2.large`, On-Demand | 15,21 USD | ≈ 0,25 USD |

**Elección: Serverless con base de 4 RPU.** Por hora de cómputo el aprovisionado es más barato, pero cobra todo el tiempo que permanece encendido, aunque no se use, y tarda varios minutos en crearse y borrarse. Serverless solo cobra mientras ejecuta consultas (por segundo, con un mínimo de 60 segundos), y el script de este punto hace unas 10 sentencias de pocos segundos cada una: el cómputo real serían pocos minutos (≈ 0,24 USD por 10 minutos a 4 RPU). El valor por defecto de Serverless (128 RPU) debe bajarse a 4 explícitamente.

## 3. Contraseña en Secrets Manager y rol IAM para `COPY`

- **Contraseña:** al crear el namespace se elige *Manage admin credentials in AWS Secrets Manager*; Redshift genera la contraseña del usuario `admin` y la guarda en un secreto administrado. El programa solo recibe el **ARN del secreto** (`REDSHIFT_SECRET_ARN`) y lo pasa a la Data API; la contraseña nunca aparece en el código.
- **Rol IAM:** se creó `RedshiftS3-taller-user3` con confianza en `redshift.amazonaws.com` (captura 5.3a). El usuario no puede adjuntar políticas a roles (`iam:AttachRolePolicy`, `iam:PutRolePolicy` e `iam:CreatePolicy` denegados, captura 5.3b), así que la lectura se concedió con una **política de bucket** basada en recursos: el bucket autoriza al rol a listarlo y a leer el prefijo `redshift/` (captura 5.4, archivo `politicas/politica_bucket.json`). Ese rol se asociaría al namespace como rol predeterminado para que funcione `COPY ... IAM_ROLE default`.

## 4. Cómo reproducirlo (con un usuario que tenga permisos)

1. Crear un bucket en us-east-2 sin acceso público y aplicarle `politicas/politica_bucket.json` (cambiando `<ID-CUENTA>` y el nombre del bucket).
2. Crear el rol para Redshift con `politicas/confianza_rol_redshift.json`.
3. Crear namespace y workgroup Serverless (base 4 RPU, base de datos `dev`, contraseña administrada en Secrets Manager, rol como predeterminado):

```powershell
aws redshift-serverless create-namespace --namespace-name taller-ns --db-name dev --admin-username admin --manage-admin-password --iam-roles arn:aws:iam::<ID-CUENTA>:role/RedshiftS3-taller-user3 --default-iam-role-arn arn:aws:iam::<ID-CUENTA>:role/RedshiftS3-taller-user3 --region us-east-2
aws redshift-serverless create-workgroup --workgroup-name taller-wg --namespace-name taller-ns --base-capacity 4 --no-publicly-accessible --region us-east-2
```

4. Copiar el ARN del secreto (`adminPasswordSecretArn` en la salida de `create-namespace`) y ejecutar:

```powershell
$env:AWS_PROFILE = 'taller-aws'
$env:AWS_REGION = 'us-east-2'
$env:AWS_BUCKET = '<bucket>'
$env:REDSHIFT_WORKGROUP = 'taller-wg'
$env:REDSHIFT_SECRET_ARN = '<arn-del-secreto>'
$env:REDSHIFT_DATABASE = 'dev'
python .\redshift_taller.py
```

El programa sube `clientes.csv` y `pedidos_inicial.csv` a `s3://<bucket>/redshift/`, crea `taller_clientes` y `taller_pedidos`, las vacía para no duplicar datos, ejecuta `COPY ... IAM_ROLE default FORMAT AS CSV IGNOREHEADER 1`, espera a que cada sentencia termine (`describe_statement`) y recupera los resultados (`get_statement_result`), que guarda en `resultados_redshift.json`.

## 5. Por qué no se pudo desplegar

| Intento | Resultado |
| --- | --- |
| Consola → Redshift sin servidor → Crear grupo de trabajo | `redshift-serverless:ListWorkgroups` y `ListTracks` denegados; el formulario no carga (captura 5.5) |
| CLI `create-namespace` (con región) | `AccessDeniedException ... not authorized to perform: redshift-serverless:CreateNamespace on resource: arn:aws:redshift-serverless:us-east-2:<ID-CUENTA>:namespace/*` |
| CLI `create-namespace` (primer intento, sin región) | `NoRegion` (captura 5.6) |
| Diagnóstico en us-east-1, us-east-2, us-west-1 y us-west-2 | Redshift Serverless y aprovisionado **DENEGADO** en las cuatro; solo la Data API está permitida (captura 5.7) |

## 6. Consultas y resultados esperados (no ejecutados en Redshift)

> Estos valores se calcularon aplicando las mismas consultas SQL a los CSV fuera de Redshift. Son lo que el programa **debería** devolver; no son resultados obtenidos en AWS.

**Conteos.** Pregunta: ¿se cargaron todos los registros? Esperado: **10 clientes y 25 pedidos**.

**Filtro.** Pregunta: ¿qué pedidos superan o igualan 150.000?

```sql
SELECT pedido_id, cliente_id, total FROM taller_pedidos WHERE total >= 150000 ORDER BY total DESC;
```

| pedido_id | cliente_id | total |
| --- | --- | --- |
| 5 | 5 | 250000 |
| 17 | 7 | 220000 |
| 11 | 1 | 200000 |
| 2 | 2 | 180000 |
| 20 | 10 | 175000 |
| 14 | 4 | 150000 |

Se esperan 6 pedidos de alto valor, de 6 clientes distintos; ningún cliente concentra las compras grandes.

**Unión.** Pregunta: ¿qué cliente y qué ciudad corresponden a cada pedido?

```sql
SELECT p.pedido_id, c.nombre, c.ciudad, p.total
FROM taller_pedidos p JOIN taller_clientes c ON p.cliente_id = c.cliente_id
ORDER BY p.pedido_id LIMIT 10;
```

| pedido_id | nombre | ciudad | total |
| --- | --- | --- | --- |
| 1 | Ana | Medellin | 45000 |
| 2 | Luis | Bogota | 180000 |
| 3 | Sofia | Cali | 80000 |
| 4 | Mateo | Medellin | 35000 |
| 5 | Valentina | Bogota | 250000 |
| 6 | Daniel | Barranquilla | 60000 |
| 7 | Laura | Cali | 50000 |
| 8 | Juan | Medellin | 120000 |
| 9 | Camila | Bogota | 95000 |
| 10 | Nicolas | Barranquilla | 40000 |

La unión por `cliente_id` enriquece cada pedido con el nombre y la ciudad del cliente, información que no está en la tabla de pedidos.

**Agregación.** Pregunta: ¿cuánto se vendió por ciudad?

```sql
SELECT c.ciudad, COUNT(*) AS pedidos, SUM(p.total) AS ventas
FROM taller_pedidos p JOIN taller_clientes c ON p.cliente_id = c.cliente_id
GROUP BY c.ciudad ORDER BY ventas DESC;
```

| ciudad | pedidos | ventas |
| --- | --- | --- |
| Bogota | 8 | 808000 |
| Medellin | 8 | 777000 |
| Cali | 5 | 535000 |
| Barranquilla | 4 | 305000 |

Se espera que Bogotá lidere las ventas por poco frente a Medellín, con el mismo número de pedidos; Barranquilla vendería menos de la mitad que Bogotá.

## 7. Preguntas de costos

- **¿Qué modalidad cuesta menos?** Serverless con 4 RPU, porque el cómputo real del taller son pocos minutos y no cobra mientras está inactivo (sección 2).
- **¿Cómo se cobran cómputo y almacenamiento?** Serverless: RPU-hora mientras hay consultas (por segundo, mínimo 60 s) más almacenamiento administrado por GB-mes. Aprovisionado: horas de nodo mientras el clúster está encendido; en `dc2` el almacenamiento va incluido en el nodo y en `ra3` se cobra aparte por GB-mes.
- **¿Qué puede seguir cobrando después de las consultas?** El almacenamiento del namespace, las instantáneas manuales, los archivos en S3, el secreto de la contraseña (≈ 0,40 USD/mes) y, en aprovisionado, el clúster completo si no se elimina o pausa.

## 8. Eliminación

No se llegó a crear namespace ni workgroup (`get-namespace` devuelve `ResourceNotFoundException`). Se eliminaron los objetos de S3 y el bucket, con lo que también desapareció su política. El rol `RedshiftS3-taller-user3` no se pudo borrar (`iam:DeleteRole` denegado); está vacío, no genera costo y se pidió al profesor eliminarlo.

## 9. Evidencias

| N.º | Captura |
| --- | --- |
| 5.1 | Cotización Serverless 4 RPU frente a `dc2.large` |
| 5.2 | Bucket en us-east-2 |
| 5.3a | Rol `RedshiftS3-taller-user3` y su relación de confianza |
| 5.3b | Error al adjuntar `AmazonS3ReadOnlyAccess` al rol |
| 5.4 | Política del bucket que da lectura al rol |
| 5.5 | Error de la consola al abrir los grupos de trabajo |
| 5.6 | Primer intento de `create-namespace` (sin región) |
| 5.7 | Diagnóstico de permisos en 4 regiones |
