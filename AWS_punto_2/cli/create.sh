#!/usr/bin/env bash
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-2
P=taller-cli
cat cli_state.env
VPC=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query Vpc.VpcId --output text)
aws ec2 create-tags --resources $VPC --tags Key=Name,Value=$P-vpc
aws ec2 modify-vpc-attribute --vpc-id $VPC --enable-dns-hostnames

AZ1=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].ZoneName' --output text)
AZ2=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[1].ZoneName' --output text)
SN1=$(aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.0.0/24 --availability-zone $AZ1 --query Subnet.SubnetId --output text)
SN2=$(aws ec2 create-subnet --vpc-id $VPC --cidr-block 10.0.1.0/24 --availability-zone $AZ2 --query Subnet.SubnetId --output text)
aws ec2 modify-subnet-attribute --subnet-id $SN1 --map-public-ip-on-launch

IGW=$(aws ec2 create-internet-gateway --query InternetGateway.InternetGatewayId --output text)
aws ec2 attach-internet-gateway --internet-gateway-id $IGW --vpc-id $VPC
RT=$(aws ec2 create-route-table --vpc-id $VPC --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id $RT --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW >/dev/null
RTA1=$(aws ec2 associate-route-table --route-table-id $RT --subnet-id $SN1 --query AssociationId --output text)
RTA2=$(aws ec2 associate-route-table --route-table-id $RT --subnet-id $SN2 --query AssociationId --output text)

SG_EC2=$(aws ec2 create-security-group --group-name $P-ec2 --description ec2 --vpc-id $VPC --query GroupId --output text)
SG_RDS=$(aws ec2 create-security-group --group-name $P-rds --description rds --vpc-id $VPC --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $SG_RDS --protocol tcp --port 5432 --source-group $SG_EC2 >/dev/null

BUCKET=$P-$(date +%s)
aws s3api create-bucket --bucket $BUCKET --create-bucket-configuration LocationConstraint=us-east-2 >/dev/null

AMI=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=al2023-ami-2023*-x86_64" \
      --query 'sort_by(Images,&CreationDate)[-1].ImageId' --output text)
EC2=$(aws ec2 run-instances --image-id $AMI --instance-type t3.micro --subnet-id $SN1 \
      --security-group-ids $SG_EC2 --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$P-ec2}]" \
      --query 'Instances[0].InstanceId' --output text)

aws rds create-db-subnet-group --db-subnet-group-name $P-subnets \
    --db-subnet-group-description taller --subnet-ids $SN1 $SN2 >/dev/null
aws rds create-db-instance --db-instance-identifier $P-db --engine postgres \
    --db-instance-class db.t3.micro --allocated-storage 20 \
    --master-username dbadmin --manage-master-user-password \
    --db-subnet-group-name $P-subnets --vpc-security-group-ids $SG_RDS \
    --no-publicly-accessible --backup-retention-period 0 >/dev/null

cat > cli_state.env <<EOF
VPC=$VPC; SN1=$SN1; SN2=$SN2; IGW=$IGW; RT=$RT; RTA1=$RTA1; RTA2=$RTA2
SG_EC2=$SG_EC2; SG_RDS=$SG_RDS; BUCKET=$BUCKET; EC2=$EC2; P=$P
EOF

aws ec2 wait instance-running --instance-ids $EC2
aws rds wait db-instance-available --db-instance-identifier $P-db
echo "Todo creado"