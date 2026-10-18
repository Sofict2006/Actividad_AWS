import os, json, boto3
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).parent.parent / ".env")

# 1. Contraseña desde Secrets Manager
sm = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-2"))
secret = json.loads(sm.get_secret_value(SecretId=os.getenv("DOCDB_SECRET"))["SecretString"])
print("Secreto recuperado para el usuario:", secret["username"])

# 2. Conexión por el túnel
client = MongoClient(
    host="localhost", port=int(os.getenv("DOCDB_PORT", "27018")),
    username=secret["username"], password=secret["password"],
    tls=True, tlsCAFile=os.getenv("DOCDB_CA"),
    tlsAllowInvalidHostnames=True, directConnection=True, retryWrites=False,
)
print("Versión del servidor:", client.server_info()["version"])

col = client[os.getenv("DOCDB_NAME", "taller")][os.getenv("DOCDB_COLLECTION", "customers")]
print("Total documentos:", col.count_documents({}))

print("\n--- FILTRO: activos con edad > 30 ---")
for d in col.find({"status": "active", "age": {"$gt": 30}}, {"_id": 0}):
    print(d)

print("\n--- ORDENACIÓN: por amount descendente ---")
for d in col.find({}, {"_id": 0}).sort("amount", -1):
    print(d)

print("\n--- AGREGACIÓN: clientes y monto por ciudad ---")
for d in col.aggregate([
    {"$group": {"_id": "$city", "clientes": {"$sum": 1}, "monto_total": {"$sum": "$amount"}}},
    {"$sort": {"monto_total": -1}},
]):
    print(d)

client.close()