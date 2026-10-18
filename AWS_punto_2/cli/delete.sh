#!/usr/bin/env bash
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-2
source cli_state.env

aws ec2 terminate-instances --instance-ids $EC2 >/dev/null
aws ec2 wait instance-terminated --instance-ids $EC2
aws rds delete-db-instance --db-instance-identifier $P-db --skip-final-snapshot --delete-automated-backups >/dev/null
aws rds wait db-instance-deleted --db-instance-identifier $P-db
aws rds delete-db-subnet-group --db-subnet-group-name $P-subnets
aws s3api delete-bucket --bucket $BUCKET
aws ec2 delete-security-group --group-id $SG_RDS
aws ec2 delete-security-group --group-id $SG_EC2
aws ec2 disassociate-route-table --association-id $RTA1
aws ec2 disassociate-route-table --association-id $RTA2
aws ec2 delete-route-table --route-table-id $RT
aws ec2 detach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC
aws ec2 delete-internet-gateway --internet-gateway-id $IGW
aws ec2 delete-subnet --subnet-id $SN1
aws ec2 delete-subnet --subnet-id $SN2
aws ec2 delete-vpc --vpc-id $VPC
echo "Todo eliminado"