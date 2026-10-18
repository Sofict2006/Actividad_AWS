# Amazon DocumentDB

## 1. Objetivos
Comparar Amazon DocumentDB con MongoDB e identificar al menos tres diferencias que puedan afectar una aplicación existente.

Comparar una instancia aprovisionada con DocumentDB Serverless, considerando la región, el tiempo de uso y la capacidad mínima de 0,5 DCU. Justificar cuál resulta más económica para la práctica e incluir el costo de la instancia EC2 utilizada como túnel SSH.

## 2. Desplegar DocumentDB
Crear un clúster de Amazon DocumentDB con una configuración de bajo costo y guardar su contraseña en AWS Secrets Manager.

## 3. Configurar la conexión
Crear una instancia EC2 dentro de la misma VPC que DocumentDB. Configurar los grupos de seguridad, el certificado TLS y el túnel SSH para permitir la conexión desde MongoDB Compass y Python.

Incluir un diagrama que represente la conexión entre el computador local, EC2 y DocumentDB.

## 4. Operaciones con Python
Recuperar la contraseña desde Secrets Manager y conectarse a DocumentDB mediante Python.

Crear una base de datos y una colección, insertar al menos diez documentos y ejecutar:
- Una búsqueda con filtro.
- Una consulta con ordenación.
- Una agregación.


## 5. Evidencias y eliminación
Se encuentran en el documento teórico
- Clúster de DocumentDB creado.
- Configuración del túnel SSH y conexión desde Compass.
- Conexión desde Python y recuperación de credenciales.
- Inserción de documentos y ejecución de las consultas.
- Eliminación del clúster y de los recursos asociados, incluida la instancia EC2 y los recursos de prueba que ya no se necesiten.

