"""Punto 4: grafo de ejemplo en Neptune con openCypher y Boto3.

Configure AWS_PROFILE (si aplica), AWS_REGION=us-east-2 y NEPTUNE_ENDPOINT
con el DNS del escritor, sin https:// ni :8182.

Dos formas de conexión:
- Endpoint público (IAM auth activada): requiere neptune-db:ReadDataViaQuery
  y WriteDataViaQuery.
- Túnel SSH por EC2 (Neptune privado, IAM auth desactivada): abra el túnel y
  defina NEPTUNE_TUNNEL=1.
"""

import json
import os
from pathlib import Path

import boto3
from botocore.config import Config


REGION = os.getenv("AWS_REGION", "us-east-2")
ENDPOINT = os.environ["NEPTUNE_ENDPOINT"].strip()
# Tolera que se pegue con https:// o :8182 por error.
ENDPOINT = ENDPOINT.removeprefix("https://").rstrip("/").removesuffix(":8182")
BASE = Path(__file__).parent

# Modo túnel SSH: con NEPTUNE_TUNNEL=1 el programa se conecta a localhost:8182,
# que el túnel (ssh -L 8182:ENDPOINT:8182 ec2-user@EC2) reenvía hasta Neptune
# privado. El certificado TLS es de *.neptune.amazonaws.com y no coincide con
# "localhost", por eso en ese modo no se verifica el nombre del certificado.
# La conexión sigue cifrada con TLS y además viaja dentro del túnel SSH.
TUNNEL = os.getenv("NEPTUNE_TUNNEL") == "1"
if TUNNEL:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

client = boto3.Session(region_name=REGION).client(
    "neptunedata",
    endpoint_url="https://localhost:8182" if TUNNEL else f"https://{ENDPOINT}:8182",
    verify=not TUNNEL,
    config=Config(read_timeout=None, retries={"total_max_attempts": 1}),
)


def query(statement):
    return client.execute_open_cypher_query(openCypherQuery=statement).get("results", [])


def main():
    nodes = [
        ("Cliente", "c1", "Ana"),
        ("Cliente", "c2", "Luis"),
        ("Cliente", "c3", "Sofia"),
        ("Cliente", "c4", "Mateo"),
        ("Cliente", "c5", "Valentina"),
        ("Producto", "p1", "Libro de datos"),
        ("Producto", "p2", "Audifonos"),
        ("Producto", "p3", "Lampara"),
        ("Categoria", "k1", "Estudio"),
        ("Categoria", "k2", "Hogar"),
    ]
    for label, node_id, name in nodes:
        query(f"MERGE (n:{label} {{id: '{node_id}', nombre: '{name}'}})")

    purchases = [
        ("c1", "p1"), ("c1", "p2"), ("c1", "p3"),
        ("c2", "p1"), ("c2", "p2"),
        ("c3", "p1"), ("c3", "p3"),
        ("c4", "p1"), ("c4", "p2"), ("c4", "p3"),
        ("c5", "p2"), ("c5", "p3"),
    ]
    for customer_id, product_id in purchases:
        query(
            f"MATCH (c:Cliente {{id: '{customer_id}'}}), "
            f"(p:Producto {{id: '{product_id}'}}) "
            "MERGE (c)-[:COMPRO]->(p)"
        )

    for product_id, category_id in (("p1", "k1"), ("p2", "k1"), ("p3", "k2")):
        query(
            f"MATCH (p:Producto {{id: '{product_id}'}}), "
            f"(k:Categoria {{id: '{category_id}'}}) "
            "MERGE (p)-[:PERTENECE_A]->(k)"
        )

    queries = {
        "conteos": "MATCH (n) WITH count(n) AS vertices "
        "MATCH ()-[r]->() RETURN vertices, count(r) AS relaciones",
        "productos_de_ana": "MATCH (c:Cliente)-[:COMPRO]->(p:Producto) "
        "WHERE c.nombre = 'Ana' RETURN c.nombre AS cliente, p.nombre AS producto "
        "ORDER BY producto",
        "clientes_de_estudio": "MATCH (c:Cliente)-[:COMPRO]->(p:Producto)"
        "-[:PERTENECE_A]->(k:Categoria) WHERE k.nombre = 'Estudio' "
        "RETURN DISTINCT c.nombre AS cliente ORDER BY cliente",
        "coincidencias_de_ana": "MATCH (a:Cliente)-[:COMPRO]->(p:Producto)"
        "<-[:COMPRO]-(otro:Cliente) WHERE a.nombre = 'Ana' "
        "AND otro.id <> a.id RETURN otro.nombre AS cliente, "
        "count(DISTINCT p) AS productos_compartidos "
        "ORDER BY productos_compartidos DESC, cliente",
    }
    results = {}
    for name, statement in queries.items():
        results[name] = query(statement)
        print(f"\n{name}: {json.dumps(results[name], ensure_ascii=False)}")
    output = BASE / "resultados_neptune.json"
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Resultados guardados en {output}")


if __name__ == "__main__":
    main()
