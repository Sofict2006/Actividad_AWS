import json
import boto3

REGION = "us-east-2"
SECRET_NAME = "taller/aws/secret-prueba"

client = boto3.client(
    "secretsmanager",
    region_name=REGION
)

response = client.get_secret_value(
    SecretId=SECRET_NAME
)

secret = json.loads(response["SecretString"])

print("Usuario:", secret["name"])
print("Contraseña:", secret["password"])