"""Diagnóstico paso a paso de la conexión a Neptune (punto 4).

Ejecútalo ANTES de neptune_taller.py, en la misma ventana de PowerShell:
    $env:AWS_PROFILE = 'taller-aws'
    $env:AWS_REGION = 'us-east-2'
    $env:NEPTUNE_ENDPOINT = 'DNS-DEL-ESCRITOR'
    python .\\diagnostico_neptune.py

Revisa credenciales, endpoint, DNS, puerto 8182 y permisos IAM, y en cada
fallo dice qué corregir. No imprime claves ni tokens.
"""

import ipaddress
import os
import socket
import sys


def ok(msg):
    print(f"  [OK]    {msg}")


def fallo(msg, solucion):
    print(f"  [FALLA] {msg}")
    print(f"          Qué hacer: {solucion}")
    sys.exit(1)


print("\n1) Python y Boto3")
try:
    import boto3
    import botocore
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError
except ImportError:
    fallo("Boto3 no está instalado.", "python -m pip install --upgrade boto3 botocore")
ok(f"Python {sys.version.split()[0]}, boto3 {boto3.__version__}, botocore {botocore.__version__}")
if "neptunedata" not in boto3.Session().get_available_services():
    fallo("Tu Boto3 no trae el cliente neptunedata (versión vieja).",
          "python -m pip install --upgrade boto3 botocore")
ok("El cliente neptunedata está disponible")

print("\n2) Variables de entorno")
perfil = os.getenv("AWS_PROFILE")
region = os.getenv("AWS_REGION")
endpoint = os.getenv("NEPTUNE_ENDPOINT", "").strip()
print(f"  AWS_PROFILE      = {perfil}")
print(f"  AWS_REGION       = {region}")
print(f"  NEPTUNE_ENDPOINT = {endpoint}")
if not perfil:
    fallo("AWS_PROFILE está vacío.", "$env:AWS_PROFILE = 'taller-aws'")
if region != "us-east-2":
    fallo("La región no es us-east-2.", "$env:AWS_REGION = 'us-east-2'")
if not endpoint:
    fallo("NEPTUNE_ENDPOINT está vacío.",
          "copia el endpoint Writer de Neptune -> Databases -> tu clúster -> Connectivity & security")
endpoint = endpoint.removeprefix("https://").removeprefix("http://").rstrip("/")
endpoint = endpoint.removesuffix(":8182")
if "cluster-ro-" in endpoint:
    fallo("Copiaste el endpoint de LECTURA (cluster-ro). El script necesita escribir.",
          "usa el endpoint de tipo Writer (dice 'cluster-' sin '-ro')")
if not endpoint.endswith(".neptune.amazonaws.com"):
    fallo("El endpoint no parece de Neptune.", "debe terminar en .neptune.amazonaws.com")
if ".us-east-2." not in endpoint:
    fallo("El endpoint no es de us-east-2.", "revisa que el clúster esté en Ohio")
ok(f"Endpoint con buen formato: {endpoint}")

print("\n3) Credenciales (¿quién soy?)")
try:
    sesion = boto3.Session(region_name=region)
    ident = sesion.client("sts").get_caller_identity()
except NoCredentialsError:
    fallo("No se encontraron credenciales para el perfil.",
          "aws login --profile taller-aws (o aws configure --profile taller-aws) y vuelve a intentar")
except Exception as e:  # sesión expirada, perfil inexistente, etc.
    fallo(f"{type(e).__name__}: {e}",
          "repite aws login --profile taller-aws; si dice que el perfil no existe, revisa el nombre")
ok(f"Autenticada como {ident['Arn']}")

print("\n4) DNS del endpoint")
try:
    ips = sorted({info[4][0] for info in socket.getaddrinfo(endpoint, 8182)})
except socket.gaierror:
    fallo("El nombre no resuelve.",
          "endpoint mal copiado o el clúster ya no existe / aún no está Available")
ok(f"Resuelve a: {', '.join(ips)}")
if all(ipaddress.ip_address(ip).is_private for ip in ips):
    fallo("Solo resuelve a IPs PRIVADAS: el clúster no tiene acceso público.",
          "la instancia necesita 'Public access' activado (motor 1.4.6.x+ y subredes con "
          "Internet Gateway). Si no se puede, toca la alternativa con EC2 bastión")

print("\n5) Puerto 8182 (red / security group)")
try:
    with socket.create_connection((endpoint, 8182), timeout=8):
        pass
except OSError as e:
    fallo(f"No se pudo abrir conexión TCP a 8182 ({e}).",
          "en el security group del clúster, regla de entrada TCP 8182 desde TU IP/32. "
          "Mira tu IP actual en https://checkip.amazonaws.com (cambia si cambias de red/WiFi)")
ok("El puerto 8182 responde")

print("\n6) Permisos IAM sobre los datos (consulta de solo lectura)")
cliente = sesion.client("neptunedata", endpoint_url=f"https://{endpoint}:8182",
                        config=Config(retries={"total_max_attempts": 1}))
try:
    cliente.execute_open_cypher_query(openCypherQuery="RETURN 1 AS prueba")
except ClientError as e:
    err = e.response.get("Error", {})
    fallo(f"{err.get('Code')}: {err.get('Message')}",
          "si es AccessDenied: tu usuario no tiene neptune-db:ReadDataViaQuery/WriteDataViaQuery "
          "sobre este clúster, o el clúster no tiene IAM database authentication. "
          "Envíale este mensaje exacto a tu profesor")
except Exception as e:
    fallo(f"{type(e).__name__}: {e}", "copia este error completo y compártelo")
ok("Consulta de prueba exitosa")

print("\nTodo listo. Ahora ejecuta:  python .\\neptune_taller.py\n")
