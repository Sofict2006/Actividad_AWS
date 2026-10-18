output "bucket"      { value = aws_s3_bucket.main.bucket }
output "ec2_id"      { value = aws_instance.main.id }
output "rds_endpoint" { value = aws_db_instance.main.endpoint }
output "secret_arn"  { value = aws_db_instance.main.master_user_secret[0].secret_arn }