# AWS Secrets Manager

## Requisitos
- Python instalado.
- Boto3 instalado (`pip install boto3`).
- Credenciales de AWS configuradas y permisos para acceder al secreto.

## 1. Crear el secreto
En AWS Secrets Manager, crear un secreto de prueba con un usuario y una contraseña ficticios en formato JSON.

## 2. Configurar permisos
Asignar a la identidad utilizada por Python una política IAM que permita ejecutar `secretsmanager:GetSecretValue` únicamente sobre el ARN del secreto de prueba.

## 3. Recuperar el secreto con Python
Ejecutar el archivo `leer_secreto.py`, que utiliza Boto3 para recuperar el secreto y leer sus valores.

```bash
python leer_secreto.py
```

## 4. Actualizar el secreto
Modificar la contraseña desde AWS Secrets Manager y ejecutar nuevamente el programa. Verificar que se obtiene el valor actualizado sin modificar el código Python.

## 5. Eliminar el secreto
Eliminar el secreto de prueba desde la consola de AWS o mediante AWS CLI, según los permisos disponibles.

## 6. Evidencias
En el documento explicativo
- Creación del secreto.
- Política de acceso.
- Recuperación mediante Python.
- Actualización del secreto y lectura del nuevo valor.
- Eliminación del secreto.

