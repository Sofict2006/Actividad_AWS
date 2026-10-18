# Despliegue con Terraform, Boto3 y AWS CLI

## Requisitos
- Cuenta de AWS con permisos suficientes.
- Usuario o identidad autorizada para trabajar con AWS.
- Terraform, AWS CLI, Python y Boto3 instalados.
- Credenciales configuradas sin utilizar la cuenta raíz.

## 1. Configurar el acceso
Configurar las credenciales de `user_cli` para utilizar AWS CLI, Boto3 y Terraform. Asignar los permisos IAM necesarios para crear y eliminar buckets S3, instancias EC2, instancias RDS y los componentes de red requeridos.

Verificar la identidad configurada:

```bash
aws sts get-caller-identity
```

## 2. Desplegar con Terraform
Revisar los archivos de configuración, inicializar Terraform, planificar y aplicar los cambios:

```bash
terraform init
terraform plan
terraform apply
```

Verificar la creación de los recursos y eliminarlos antes de continuar:

```bash
terraform destroy
```

## 3. Desplegar con Boto3
Ejecutar el programa Python que crea los recursos de S3, EC2, RDS y sus componentes de red. Verificar su creación y eliminarlos antes de pasar al siguiente método.

## 4. Desplegar con AWS CLI
Ejecutar los comandos CLI para crear los mismos recursos, comprobar su existencia y eliminarlos antes de finalizar el ejercicio.

Los tres despliegues deben realizarse secuencialmente para evitar mantener recursos duplicados y generar costos innecesarios.

## 5. Seguridad y costos
Documentar los permisos IAM utilizados, el mecanismo de autenticación de las herramientas, la administración de la contraseña de RDS mediante Secrets Manager cuando sea compatible y los riesgos de almacenar información sensible en el estado de Terraform.

La comparación entre los tres métodos y la estimación de costos por una hora y una semana se encuentra en el documento teorico.

## 6. Evidencias
En el documento teórico
- Identidad y permisos utilizados.
- Archivos de Terraform y ejecución del despliegue.
- Creación y eliminación de recursos con Terraform.
- Creación y eliminación con Boto3.
- Creación y eliminación con AWS CLI.
- Estado final de los recursos en AWS.

