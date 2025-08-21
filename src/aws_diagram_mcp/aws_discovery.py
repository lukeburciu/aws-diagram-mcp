"""AWS resource discovery functions."""

import logging
from typing import Dict, List, Any, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSResourceDiscovery:
    """Discovers AWS resources for diagram generation."""
    
    def __init__(self, region: str = "us-east-1", profile: Optional[str] = None):
        self.region = region
        self.session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        self.ec2 = self.session.client("ec2", region_name=region)
        self.elbv2 = self.session.client("elbv2", region_name=region)
        self.rds = self.session.client("rds", region_name=region)
        self.route53 = self.session.client("route53")
        self.acm = self.session.client("acm", region_name=region)
        self.sts = self.session.client("sts")
    
    def get_account_info(self) -> Dict[str, str]:
        """Get AWS account information."""
        try:
            response = self.sts.get_caller_identity()
            return {
                "account_id": response["Account"],
                "arn": response["Arn"],
                "user_id": response["UserId"]
            }
        except ClientError as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def discover_vpcs(self) -> List[Dict[str, Any]]:
        """Discover all VPCs."""
        try:
            response = self.ec2.describe_vpcs()
            vpcs = []
            for vpc in response["Vpcs"]:
                vpc_info = {
                    "vpc_id": vpc["VpcId"],
                    "cidr_block": vpc["CidrBlock"],
                    "state": vpc["State"],
                    "is_default": vpc.get("IsDefault", False),
                    "tags": self._process_tags(vpc.get("Tags", []))
                }
                vpcs.append(vpc_info)
            return vpcs
        except ClientError as e:
            logger.error(f"Error discovering VPCs: {e}")
            return []
    
    def discover_subnets(self, vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover subnets."""
        try:
            filters = []
            if vpc_id:
                filters.append({"Name": "vpc-id", "Values": [vpc_id]})
            
            response = self.ec2.describe_subnets(Filters=filters)
            subnets = []
            for subnet in response["Subnets"]:
                subnet_info = {
                    "subnet_id": subnet["SubnetId"],
                    "vpc_id": subnet["VpcId"],
                    "cidr_block": subnet["CidrBlock"],
                    "availability_zone": subnet["AvailabilityZone"],
                    "state": subnet["State"],
                    "tags": self._process_tags(subnet.get("Tags", [])),
                    "tier": self._determine_subnet_tier(subnet)
                }
                subnets.append(subnet_info)
            return subnets
        except ClientError as e:
            logger.error(f"Error discovering subnets: {e}")
            return []
    
    def discover_ec2_instances(self, vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover EC2 instances."""
        try:
            filters = []
            if vpc_id:
                filters.append({"Name": "vpc-id", "Values": [vpc_id]})
            
            response = self.ec2.describe_instances(Filters=filters)
            instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    if instance["State"]["Name"] == "running":
                        instance_info = {
                            "instance_id": instance["InstanceId"],
                            "instance_type": instance["InstanceType"],
                            "private_ip": instance.get("PrivateIpAddress"),
                            "public_ip": instance.get("PublicIpAddress"),
                            "subnet_id": instance.get("SubnetId"),
                            "vpc_id": instance.get("VpcId"),
                            "state": instance["State"]["Name"],
                            "name": self._get_tag_value(instance.get("Tags", []), "Name"),
                            "security_groups": [sg["GroupId"] for sg in instance.get("SecurityGroups", [])],
                            "tags": self._process_tags(instance.get("Tags", []))
                        }
                        instances.append(instance_info)
            return instances
        except ClientError as e:
            logger.error(f"Error discovering EC2 instances: {e}")
            return []
    
    def discover_load_balancers(self, vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover load balancers."""
        try:
            response = self.elbv2.describe_load_balancers()
            load_balancers = []
            
            for lb in response["LoadBalancers"]:
                if vpc_id and lb["VpcId"] != vpc_id:
                    continue
                
                lb_arn = lb["LoadBalancerArn"]
                lb_info = {
                    "name": lb["LoadBalancerName"],
                    "arn": lb_arn,
                    "type": lb["Type"],
                    "scheme": lb["Scheme"],
                    "state": lb["State"]["Code"],
                    "vpc_id": lb["VpcId"],
                    "dns_name": lb["DNSName"],
                    "ips": self._get_load_balancer_ips(lb),
                    "target_groups": self._get_target_groups(lb_arn),
                    "listeners": self._get_listeners(lb_arn),
                    "subnets": [az["SubnetId"] for az in lb.get("AvailabilityZones", [])]
                }
                load_balancers.append(lb_info)
            return load_balancers
        except ClientError as e:
            logger.error(f"Error discovering load balancers: {e}")
            return []
    
    def discover_rds_instances(self, vpc_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover RDS instances."""
        try:
            response = self.rds.describe_db_instances()
            rds_instances = []
            
            for db in response["DBInstances"]:
                db_subnet_group = db.get("DBSubnetGroup", {})
                db_vpc_id = db_subnet_group.get("VpcId")
                
                if vpc_id and db_vpc_id != vpc_id:
                    continue
                
                rds_info = {
                    "db_instance_id": db["DBInstanceIdentifier"],
                    "engine": db["Engine"],
                    "engine_version": db["EngineVersion"],
                    "instance_class": db["DBInstanceClass"],
                    "status": db["DBInstanceStatus"],
                    "endpoint": db.get("Endpoint", {}).get("Address"),
                    "port": db.get("Endpoint", {}).get("Port"),
                    "vpc_id": db_vpc_id,
                    "subnet_group": db_subnet_group.get("DBSubnetGroupName"),
                    "availability_zone": db.get("AvailabilityZone"),
                    "security_groups": [sg["VpcSecurityGroupId"] for sg in db.get("VpcSecurityGroups", [])]
                }
                rds_instances.append(rds_info)
            return rds_instances
        except ClientError as e:
            logger.error(f"Error discovering RDS instances: {e}")
            return []
    
    def discover_security_groups(self, group_ids: List[str]) -> Dict[str, Any]:
        """Discover security group rules."""
        if not group_ids:
            return {}
        
        try:
            response = self.ec2.describe_security_groups(GroupIds=group_ids)
            sg_rules = {}
            
            for sg in response["SecurityGroups"]:
                rules = {
                    "ingress": [],
                    "egress": []
                }
                
                for rule in sg.get("IpPermissions", []):
                    processed_rule = self._process_sg_rule(rule, "ingress")
                    if processed_rule:
                        rules["ingress"].append(processed_rule)
                
                for rule in sg.get("IpPermissionsEgress", []):
                    processed_rule = self._process_sg_rule(rule, "egress")
                    if processed_rule:
                        rules["egress"].append(processed_rule)
                
                sg_rules[sg["GroupId"]] = {
                    "name": sg["GroupName"],
                    "description": sg.get("Description", ""),
                    "rules": rules
                }
            
            return sg_rules
        except ClientError as e:
            logger.error(f"Error discovering security groups: {e}")
            return {}
    
    def discover_route53_zones(self) -> List[Dict[str, Any]]:
        """Discover Route53 hosted zones."""
        try:
            response = self.route53.list_hosted_zones()
            zones = []
            
            for zone in response["HostedZones"]:
                zone_id = zone["Id"].split("/")[-1]
                zone_info = {
                    "zone_id": zone_id,
                    "name": zone["Name"],
                    "type": zone["Config"].get("PrivateZone", False) and "Private" or "Public",
                    "records": self._get_route53_records(zone_id)
                }
                zones.append(zone_info)
            return zones
        except ClientError as e:
            logger.error(f"Error discovering Route53 zones: {e}")
            return []
    
    def discover_acm_certificates(self) -> List[Dict[str, Any]]:
        """Discover ACM certificates."""
        try:
            response = self.acm.list_certificates()
            certificates = []
            
            for cert in response["CertificateSummaryList"]:
                cert_info = {
                    "arn": cert["CertificateArn"],
                    "domain": cert["DomainName"],
                    "status": cert.get("Status", "UNKNOWN")
                }
                certificates.append(cert_info)
            return certificates
        except ClientError as e:
            logger.error(f"Error discovering ACM certificates: {e}")
            return []
    
    def _process_tags(self, tags: List[Dict]) -> Dict[str, str]:
        """Process AWS tags into a dictionary."""
        return {tag["Key"]: tag["Value"] for tag in tags}
    
    def _get_tag_value(self, tags: List[Dict], key: str) -> Optional[str]:
        """Get a specific tag value."""
        for tag in tags:
            if tag["Key"] == key:
                return tag["Value"]
        return None
    
    def _determine_subnet_tier(self, subnet: Dict) -> str:
        """Determine subnet tier based on tags and routing."""
        tags = self._process_tags(subnet.get("Tags", []))
        name = tags.get("Name", "").lower()
        
        if "public" in name or "dmz" in name or "presentation" in name:
            return "presentation"
        elif "private" in name or "app" in name or "application" in name:
            return "application"
        elif "data" in name or "db" in name or "restricted" in name:
            return "restricted"
        else:
            return "application"
    
    def _get_load_balancer_ips(self, lb: Dict) -> List[str]:
        """Get IP addresses for a load balancer."""
        ips = []
        for az in lb.get("AvailabilityZones", []):
            for addr in az.get("LoadBalancerAddresses", []):
                if addr.get("PrivateIPv4Address"):
                    ips.append(addr["PrivateIPv4Address"])
        return ips
    
    def _get_target_groups(self, lb_arn: str) -> List[Dict[str, Any]]:
        """Get target groups for a load balancer."""
        try:
            response = self.elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
            target_groups = []
            
            for tg in response["TargetGroups"]:
                tg_arn = tg["TargetGroupArn"]
                targets = self._get_targets(tg_arn)
                target_groups.append({
                    "name": tg["TargetGroupName"],
                    "arn": tg_arn,
                    "port": tg.get("Port"),
                    "protocol": tg.get("Protocol"),
                    "targets": targets
                })
            return target_groups
        except ClientError:
            return []
    
    def _get_targets(self, tg_arn: str) -> List[Dict[str, Any]]:
        """Get targets for a target group."""
        try:
            response = self.elbv2.describe_target_health(TargetGroupArn=tg_arn)
            targets = []
            for target in response["TargetHealthDescriptions"]:
                targets.append({
                    "id": target["Target"]["Id"],
                    "port": target["Target"].get("Port"),
                    "health": target["TargetHealth"]["State"]
                })
            return targets
        except ClientError:
            return []
    
    def _get_listeners(self, lb_arn: str) -> List[Dict[str, Any]]:
        """Get listeners for a load balancer."""
        try:
            response = self.elbv2.describe_listeners(LoadBalancerArn=lb_arn)
            listeners = []
            for listener in response["Listeners"]:
                listener_info = {
                    "port": listener["Port"],
                    "protocol": listener["Protocol"],
                    "certificates": []
                }
                for cert in listener.get("Certificates", []):
                    listener_info["certificates"].append(cert["CertificateArn"])
                listeners.append(listener_info)
            return listeners
        except ClientError:
            return []
    
    def _get_route53_records(self, zone_id: str) -> List[Dict[str, Any]]:
        """Get Route53 records for a hosted zone."""
        try:
            response = self.route53.list_resource_record_sets(HostedZoneId=zone_id)
            records = []
            for record in response["ResourceRecordSets"]:
                if record["Type"] in ["A", "AAAA", "CNAME"]:
                    record_info = {
                        "name": record["Name"],
                        "type": record["Type"],
                        "values": []
                    }
                    if "AliasTarget" in record:
                        record_info["values"].append(record["AliasTarget"]["DNSName"])
                    else:
                        for rr in record.get("ResourceRecords", []):
                            record_info["values"].append(rr["Value"])
                    records.append(record_info)
            return records
        except ClientError:
            return []
    
    def _process_sg_rule(self, rule: Dict, direction: str) -> Optional[Dict[str, Any]]:
        """Process a security group rule."""
        processed = {
            "direction": direction,
            "protocol": rule.get("IpProtocol", "-1"),
            "from_port": rule.get("FromPort"),
            "to_port": rule.get("ToPort"),
            "sources": []
        }
        
        for ip_range in rule.get("IpRanges", []):
            processed["sources"].append({
                "type": "cidr",
                "value": ip_range["CidrIp"]
            })
        
        for sg in rule.get("UserIdGroupPairs", []):
            processed["sources"].append({
                "type": "security_group",
                "value": sg["GroupId"]
            })
        
        if processed["sources"]:
            return processed
        return None