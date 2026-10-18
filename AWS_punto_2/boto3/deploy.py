import sys, json, time
import boto3

REGION, P, STATE = "us-east-2", "taller-boto3", "boto3_state.json"
s = boto3.Session(region_name=REGION)
ec2, rds, s3 = s.client("ec2"), s.client("rds"), s.client("s3")

def tag(t):
    return [{"ResourceType": t, "Tags": [{"Key": "Name", "Value": f"{P}-{t}"},
                                         {"Key": "Project", "Value": P}]}]

def create():
    st = {}
    try:
        st["vpc"] = ec2.create_vpc(CidrBlock="10.0.0.0/16", TagSpecifications=tag("vpc"))["Vpc"]["VpcId"]
        ec2.modify_vpc_attribute(VpcId=st["vpc"], EnableDnsHostnames={"Value": True})

        azs = [z["ZoneName"] for z in ec2.describe_availability_zones()["AvailabilityZones"]][:2]
        st["subnets"] = []
        for i, az in enumerate(azs):
            sn = ec2.create_subnet(VpcId=st["vpc"], CidrBlock=f"10.0.{i}.0/24",
                                   AvailabilityZone=az, TagSpecifications=tag("subnet"))["Subnet"]["SubnetId"]
            ec2.modify_subnet_attribute(SubnetId=sn, MapPublicIpOnLaunch={"Value": True})
            st["subnets"].append(sn)

        st["igw"] = ec2.create_internet_gateway(TagSpecifications=tag("internet-gateway"))["InternetGateway"]["InternetGatewayId"]
        ec2.attach_internet_gateway(InternetGatewayId=st["igw"], VpcId=st["vpc"])

        st["rt"] = ec2.create_route_table(VpcId=st["vpc"], TagSpecifications=tag("route-table"))["RouteTable"]["RouteTableId"]
        ec2.create_route(RouteTableId=st["rt"], DestinationCidrBlock="0.0.0.0/0", GatewayId=st["igw"])
        st["rt_assoc"] = [ec2.associate_route_table(RouteTableId=st["rt"], SubnetId=sn)["AssociationId"]
                          for sn in st["subnets"]]

        st["sg_ec2"] = ec2.create_security_group(GroupName=f"{P}-ec2", Description="ec2", VpcId=st["vpc"])["GroupId"]
        st["sg_rds"] = ec2.create_security_group(GroupName=f"{P}-rds", Description="rds", VpcId=st["vpc"])["GroupId"]
        ec2.authorize_security_group_ingress(GroupId=st["sg_rds"], IpPermissions=[{
            "IpProtocol": "tcp", "FromPort": 5432, "ToPort": 5432,
            "UserIdGroupPairs": [{"GroupId": st["sg_ec2"]}]}])

        st["bucket"] = f"{P}-{int(time.time())}"
        s3.create_bucket(Bucket=st["bucket"], CreateBucketConfiguration={"LocationConstraint": REGION}) 

        ami = ec2.describe_images(Owners=["amazon"], Filters=[
            {"Name": "name", "Values": ["al2023-ami-2023*-x86_64"]}])["Images"]
        ami = sorted(ami, key=lambda i: i["CreationDate"])[-1]["ImageId"]
        st["ec2"] = ec2.run_instances(ImageId=ami, InstanceType="t3.micro", MinCount=1, MaxCount=1,
                                      SubnetId=st["subnets"][0], SecurityGroupIds=[st["sg_ec2"]],
                                      TagSpecifications=tag("instance"))["Instances"][0]["InstanceId"]

        st["subnet_group"] = f"{P}-subnets"
        rds.create_db_subnet_group(DBSubnetGroupName=st["subnet_group"],
                                   DBSubnetGroupDescription="taller", SubnetIds=st["subnets"])
        st["rds"] = f"{P}-db"
        rds.create_db_instance(DBInstanceIdentifier=st["rds"], Engine="postgres",
                               DBInstanceClass="db.t3.micro", AllocatedStorage=20,
                               MasterUsername="dbadmin", ManageMasterUserPassword=True,
                               DBSubnetGroupName=st["subnet_group"],
                               VpcSecurityGroupIds=[st["sg_rds"]],
                               PubliclyAccessible=False, BackupRetentionPeriod=0)

        print("Esperando EC2 y RDS...")
        ec2.get_waiter("instance_running").wait(InstanceIds=[st["ec2"]])
        rds.get_waiter("db_instance_available").wait(DBInstanceIdentifier=st["rds"])
        print("Listo:", json.dumps(st, indent=2))
    finally:
        json.dump(st, open(STATE, "w"), indent=2)   # sin contraseñas, solo IDs

def delete():
    st = json.load(open(STATE))
    if st.get("ec2"):
        ec2.terminate_instances(InstanceIds=[st["ec2"]])
        ec2.get_waiter("instance_terminated").wait(InstanceIds=[st["ec2"]])
    if st.get("rds"):
        rds.delete_db_instance(DBInstanceIdentifier=st["rds"], SkipFinalSnapshot=True,
                               DeleteAutomatedBackups=True)
        rds.get_waiter("db_instance_deleted").wait(DBInstanceIdentifier=st["rds"])
    if st.get("subnet_group"):
        rds.delete_db_subnet_group(DBSubnetGroupName=st["subnet_group"])
    if st.get("bucket"):
        s3.delete_bucket(Bucket=st["bucket"])
    for k in ("sg_rds", "sg_ec2"):
        if st.get(k): ec2.delete_security_group(GroupId=st[k])
    for a in st.get("rt_assoc", []): ec2.disassociate_route_table(AssociationId=a)
    if st.get("rt"): ec2.delete_route_table(RouteTableId=st["rt"])
    if st.get("igw"):
        ec2.detach_internet_gateway(InternetGatewayId=st["igw"], VpcId=st["vpc"])
        ec2.delete_internet_gateway(InternetGatewayId=st["igw"])
    for sn in st.get("subnets", []): ec2.delete_subnet(SubnetId=sn)
    if st.get("vpc"): ec2.delete_vpc(VpcId=st["vpc"])
    print("Todo eliminado")

{"create": create, "delete": delete}[sys.argv[1]]()