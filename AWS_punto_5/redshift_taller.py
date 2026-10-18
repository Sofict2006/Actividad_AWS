"""Punto 5: carga dos CSV en Redshift Serverless mediante la Data API.

Antes de ejecutar, configure AWS_PROFILE (si aplica), AWS_REGION=us-east-2,
AWS_BUCKET, REDSHIFT_WORKGROUP y REDSHIFT_SECRET_ARN. El namespace debe tener
un rol IAM predeterminado con s3:ListBucket y s3:GetObject sobre el bucket.
"""

import json
import os
import time
from pathlib import Path

import boto3


REGION = os.getenv("AWS_REGION", "us-east-2")
BUCKET = os.environ["AWS_BUCKET"]
WORKGROUP = os.environ["REDSHIFT_WORKGROUP"]
SECRET_ARN = os.environ["REDSHIFT_SECRET_ARN"]
DATABASE = os.getenv("REDSHIFT_DATABASE", "dev")
BASE = Path(__file__).parent

session = boto3.Session(region_name=REGION)
s3 = session.client("s3")
data_api = session.client("redshift-data")


def run_sql(sql, label):
    statement_id = data_api.execute_statement(
        WorkgroupName=WORKGROUP,
        Database=DATABASE,
        SecretArn=SECRET_ARN,
        Sql=sql,
        StatementName=label,
    )["Id"]
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        info = data_api.describe_statement(Id=statement_id)
        if info["Status"] == "FINISHED":
            break
        if info["Status"] in ("FAILED", "ABORTED"):
            raise RuntimeError(f"{label}: {info.get('Error', info['Status'])}")
        time.sleep(2)
    else:
        raise TimeoutError(f"{label}: la sentencia no terminó en 5 minutos")

    rows = []
    if info.get("HasResultSet"):
        token = None
        while True:
            args = {"Id": statement_id}
            if token:
                args["NextToken"] = token
            page = data_api.get_statement_result(**args)
            names = [column["name"] for column in page["ColumnMetadata"]]
            for record in page["Records"]:
                values = [next(iter(field.values())) for field in record]
                rows.append(dict(zip(names, values)))
            token = page.get("NextToken")
            if not token:
                break
    print(f"\n{label} | {info['Status']} | filas: {len(rows)}")
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    return rows


def main():
    for filename in ("clientes.csv", "pedidos_inicial.csv"):
        source = BASE / "datos" / filename
        key = f"redshift/{filename}"
        s3.upload_file(str(source), BUCKET, key)
        print(f"Subido s3://{BUCKET}/{key}")

    run_sql(
        "CREATE TABLE IF NOT EXISTS taller_clientes "
        "(cliente_id INTEGER, nombre VARCHAR(80), ciudad VARCHAR(80))",
        "crear_clientes",
    )
    run_sql(
        "CREATE TABLE IF NOT EXISTS taller_pedidos "
        "(pedido_id INTEGER, cliente_id INTEGER, categoria VARCHAR(80), total INTEGER)",
        "crear_pedidos",
    )
    run_sql("TRUNCATE TABLE taller_clientes", "limpiar_clientes")
    run_sql("TRUNCATE TABLE taller_pedidos", "limpiar_pedidos")
    run_sql(
        f"COPY taller_clientes FROM 's3://{BUCKET}/redshift/clientes.csv' "
        "IAM_ROLE default FORMAT AS CSV IGNOREHEADER 1 REGION 'us-east-2'",
        "cargar_clientes",
    )
    run_sql(
        f"COPY taller_pedidos FROM 's3://{BUCKET}/redshift/pedidos_inicial.csv' "
        "IAM_ROLE default FORMAT AS CSV IGNOREHEADER 1 REGION 'us-east-2'",
        "cargar_pedidos",
    )
    results = {
        "conteos": run_sql(
            "SELECT (SELECT COUNT(*) FROM taller_clientes) AS clientes, "
            "(SELECT COUNT(*) FROM taller_pedidos) AS pedidos",
            "contar_filas",
        ),
        "filtro": run_sql(
            "SELECT pedido_id, cliente_id, total FROM taller_pedidos "
            "WHERE total >= 150000 ORDER BY total DESC",
            "pedidos_altos",
        ),
        "union": run_sql(
            "SELECT p.pedido_id, c.nombre, c.ciudad, p.total "
            "FROM taller_pedidos p JOIN taller_clientes c "
            "ON p.cliente_id = c.cliente_id "
            "ORDER BY p.pedido_id LIMIT 10",
            "pedidos_con_cliente",
        ),
        "agregacion": run_sql(
            "SELECT c.ciudad, COUNT(*) AS pedidos, SUM(p.total) AS ventas "
            "FROM taller_pedidos p JOIN taller_clientes c "
            "ON p.cliente_id = c.cliente_id GROUP BY c.ciudad ORDER BY ventas DESC",
            "ventas_por_ciudad",
        ),
    }
    output = BASE / "resultados_redshift.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados guardados en {output}")


if __name__ == "__main__":
    main()
