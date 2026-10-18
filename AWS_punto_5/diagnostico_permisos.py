"""Busca en qué regiones y servicios tiene permisos tu usuario (solo LECTURA).

No crea, modifica ni borra nada: solo hace consultas de tipo "listar/describir".
Uso (misma ventana de PowerShell donde ya hiciste aws login):
    $env:AWS_PROFILE = 'taller-aws'
    python .\\diagnostico_permisos.py
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError

REGIONES = ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]
CFG = Config(retries={"total_max_attempts": 1}, connect_timeout=5, read_timeout=10)
ses = boto3.Session()


def probar(servicio, metodo, region=None, **kw):
    try:
        cli = ses.client(servicio, region_name=region, config=CFG)
        r = getattr(cli, metodo)(**kw)
        r.pop("ResponseMetadata", None)
        # cuenta elementos de la primera lista que aparezca
        n = next((len(v) for v in r.values() if isinstance(v, list)), None)
        return "OK" + (f" ({n})" if n is not None else ""), r
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if "AccessDenied" in code or code in ("UnauthorizedOperation", "AuthorizationError"):
            return "DENEGADO", None
        return f"error:{code}", None
    except EndpointConnectionError:
        return "sin servicio", None
    except Exception as e:
        return f"error:{type(e).__name__}", None


print("\n=== Identidad ===")
ident = ses.client("sts").get_caller_identity()
print(ident["Arn"])
user_arn = ident["Arn"]
user_name = user_arn.split("/")[-1]

print("\n=== Permisos por región (solo lectura) ===")
pruebas = [
    ("Redshift Serverless (workgroups)", "redshift-serverless", "list_workgroups", {}),
    ("Redshift aprovisionado (clusters)", "redshift", "describe_clusters", {}),
    ("Redshift Data API (statements)", "redshift-data", "list_statements", {}),
    ("Glue (crawlers)", "glue", "get_crawlers", {}),
    ("Glue (bases de datos)", "glue", "get_databases", {}),
    ("Neptune / RDS (clusters)", "neptune", "describe_db_clusters", {}),
    ("Secrets Manager (secretos)", "secretsmanager", "list_secrets", {}),
    ("Athena (workgroups)", "athena", "list_work_groups", {}),
]
print(f"{'Servicio':36}" + "".join(f"{r:>16}" for r in REGIONES))
detalles = {}
for nombre, svc, met, kw in pruebas:
    fila = f"{nombre:36}"
    for reg in REGIONES:
        estado, resp = probar(svc, met, reg, **kw)
        fila += f"{estado:>16}"
        if resp:
            detalles[(nombre, reg)] = resp
    print(fila)

print("\n=== Recursos encontrados (fuera de lo tuyo) ===")
for (nombre, reg), resp in detalles.items():
    if "workgroups" in resp and resp["workgroups"]:
        for w in resp["workgroups"]:
            print(f"  [{reg}] Workgroup Redshift: {w.get('workgroupName')} -> namespace {w.get('namespaceName')}")
    if "Clusters" in resp and resp["Clusters"]:
        for c in resp["Clusters"]:
            print(f"  [{reg}] Cluster Redshift: {c.get('ClusterIdentifier')} ({c.get('ClusterStatus')})")
    if "Crawlers" in resp and resp["Crawlers"]:
        for c in resp["Crawlers"]:
            print(f"  [{reg}] Crawler: {c.get('Name')} rol={c.get('Role')}")
    if "SecretList" in resp and resp["SecretList"]:
        for s in resp["SecretList"]:
            print(f"  [{reg}] Secreto: {s.get('Name')}")
    if "DBClusters" in resp and resp["DBClusters"]:
        for c in resp["DBClusters"]:
            print(f"  [{reg}] Cluster {c.get('Engine')}: {c.get('DBClusterIdentifier')} ({c.get('Status')})")

print("\n=== Regiones de los buckets (dónde trabajaron otros) ===")
s3 = ses.client("s3", config=CFG)
try:
    for b in s3.list_buckets()["Buckets"]:
        try:
            loc = s3.get_bucket_location(Bucket=b["Name"])["LocationConstraint"] or "us-east-1"
        except ClientError as e:
            loc = e.response["Error"]["Code"]
        print(f"  {b['Name']:55} {loc}")
except ClientError as e:
    print("  No se pudo listar:", e.response["Error"]["Code"])

print("\n=== IAM: roles visibles y MFA ===")
estado, resp = probar("iam", "list_roles")
print("  list_roles:", estado)
if resp:
    for r in resp["Roles"]:
        print("   -", r["RoleName"])
estado, resp = probar("iam", "list_mfa_devices", UserName=user_name)
print("  list_mfa_devices:", estado, (resp or {}).get("MFADevices", ""))

print("\n=== Simulación de permisos (si está permitida) ===")
acciones = [
    "redshift-serverless:CreateNamespace", "redshift-serverless:CreateWorkgroup",
    "redshift:CreateCluster", "redshift-data:ExecuteStatement",
    "glue:CreateCrawler", "glue:StartCrawler",
    "neptune-db:ReadDataViaQuery", "neptune-db:WriteDataViaQuery",
    "iam:PassRole", "sts:AssumeRole",
]
iam = ses.client("iam", config=CFG)
for reg in REGIONES:
    try:
        r = iam.simulate_principal_policy(
            PolicySourceArn=user_arn, ActionNames=acciones,
            ContextEntries=[{"ContextKeyName": "aws:RequestedRegion",
                             "ContextKeyValues": [reg], "ContextKeyType": "string"}])
        permitidas = [x["EvalActionName"] for x in r["EvaluationResults"] if x["EvalDecision"] == "allowed"]
        print(f"  {reg}: permitidas -> {permitidas or 'ninguna'}")
    except ClientError as e:
        print("  simulate_principal_policy:", e.response["Error"]["Code"])
        break

print("\nListo. Copia TODO lo que salió arriba y pégaselo a Claude.\n")
