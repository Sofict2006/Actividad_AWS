# Actividad AWS · Ingeniería de Datos 2026-2 (Universidad EIA)

Repositorio con el código, las consultas, los resultados y las evidencias de los seis puntos de la Actividad AWS. Cada punto está en su propia carpeta con una guía para reproducirlo. Las evidencias de los puntos 1 a 3 están en el documento teórico; las de los puntos 4 a 6 están además en la carpeta `evidencias/` de cada punto.

Integrantes:

- Sofia Ceballos Toro (puntos 1, 2 y 3)
- Manuela Echeverri Castrillón (puntos 4, 5 y 6)

## Índice

| Punto | Servicio | Guía del punto | Estado |
| --- | --- | --- | --- |
| 1 | AWS Secrets Manager | [`AWS_punto_1/punto1.md`](AWS_punto_1/punto1.md) | Completo |
| 2 | Terraform, Boto3 y AWS CLI (S3, EC2, RDS) | [`AWS_punto_2/punto2.md`](AWS_punto_2/punto2.md) | Completo |
| 3 | Amazon DocumentDB (túnel SSH por EC2) | [`AWS_punto_3/DocumentDB/punto3.md`](AWS_punto_3/DocumentDB/punto3.md) | Completo |
| 4 | Amazon Neptune | [`AWS_punto_4/README.md`](AWS_punto_4/README.md) | Completo (acceso por túnel SSH) |
| 5 | Amazon Redshift | [`AWS_punto_5/README.md`](AWS_punto_5/README.md) | Preparado; bloqueado por permisos de la cuenta del curso |
| 6 | AWS Glue Data Catalog + Athena | [`AWS_punto_6/README.md`](AWS_punto_6/README.md) | Completo, con tabla manual (crawler bloqueado por permisos) |

La parte teórica y las capturas comentadas también están en el documento Word de la entrega.

## Condiciones generales

- **Región única:** `us-east-2` (Ohio).
- **Cuenta:** se usaron usuarios IAM entregados por el profesor, con políticas ya definidas. Algunas acciones no estaban permitidas; cada punto documenta qué se bloqueó y cómo se resolvió.
- **Costo:** antes de cada despliegue se cotizó en AWS Pricing Calculator y se eligió la configuración de menor costo. Al terminar se eliminaron los recursos (el profesor indicó que no es obligatorio adjuntar evidencia de eliminación; algunos puntos la incluyen igual).
- **Secretos:** toda contraseña de base de datos se gestiona con AWS Secrets Manager y los programas la recuperan en ejecución. No hay contraseñas en el código.

## Requisitos para reproducir

- Python 3.10 o superior con `pip install --upgrade boto3 botocore` (el punto 3 usa además `pymongo` y `python-dotenv`).
- AWS CLI v2 autenticada con un usuario IAM, nunca con la cuenta raíz (`aws configure --profile <perfil>` o `aws login --profile <perfil>`).
- Terraform para el punto 2.
- En PowerShell: `$env:AWS_PROFILE = '<perfil>'` y `$env:AWS_REGION = 'us-east-2'`.

## Resumen por punto

1. **Secrets Manager:** secreto de prueba `taller/aws/secret-prueba`; `obtener_secreto.py` lo recupera con Boto3 y obtiene la versión actual (`AWSCURRENT`) después de modificarlo, sin cambiar el código.
2. **Terraform, Boto3 y CLI:** el mismo conjunto (bucket S3, EC2, RDS y red) creado y eliminado tres veces, de forma secuencial: `terraform/`, `boto3/deploy.py` y `cli/create.sh` / `cli/delete.sh`, con las salidas de cada ejecución en `evidencias/`. RDS con contraseña administrada en Secrets Manager.
3. **DocumentDB:** clúster privado al que se accede con un túnel SSH por una EC2 en la misma VPC, con TLS; contraseña desde Secrets Manager; `taller.py` inserta documentos y ejecuta filtro, ordenación y agregación.
4. **Neptune:** clúster `db.t4g.medium`; grafo de 10 vértices y 15 relaciones; tres consultas openCypher desde Python. El endpoint público con IAM funcionó en red pero faltaban permisos de datos, así que se usó Neptune privado con túnel SSH por una EC2 bastión.
5. **Redshift:** cotización (Serverless 4 RPU frente a `dc2.large`), datos, programa con Data API y secreto, y rol IAM con política de bucket. No se pudo crear el namespace por falta de permisos `redshift-serverless`; se documentan los resultados **esperados**.
6. **Glue + Athena:** CSV de 25 → 30 registros en S3, base de datos en el catálogo, tabla definida manualmente, consultas con filtro y agrupación desde Athena.

## Seguridad del repositorio

- No se suben claves de acceso, llaves privadas (`*.pem`), archivos `.env`, estados ni planes de Terraform (`*.tfstate`, `tfplan`) ni valores de secretos.
- En las capturas se ocultaron el número de cuenta y las IP públicas personales; en los textos aparece `<ID-CUENTA>`.
