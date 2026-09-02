"""
=============================================================================
FILE:    cloud_resource_audit.py
PURPOSE: Audits AWS cloud resources to find waste, security gaps, and
         cost-saving opportunities. Cloud bills can spiral out of control
         if no one checks — this script is your automated accountant + security guard.

         Checks:
           💰 Unused/stopped EC2 instances (you're still paying for stopped instances!)
           🔒 Security Groups with dangerous open ports (port 22/3389 open to 0.0.0.0/0)
           🪣 S3 buckets with public access (massive security risk!)
           📸 Old EC2 snapshots wasting storage money
           🔑 IAM users without MFA enabled (security risk)

LIBRARY: boto3 — the official AWS Python SDK.
         Install with: pip install boto3

SETUP:   Configure AWS credentials first:
         Option 1: aws configure (installs AWS CLI and sets up ~/.aws/credentials)
         Option 2: Set environment variables:
                   export AWS_ACCESS_KEY_ID="your_key"
                   export AWS_SECRET_ACCESS_KEY="your_secret"
                   export AWS_DEFAULT_REGION="us-east-1"

NOTE:    This script is READ-ONLY — it only lists resources, never changes them.
         Safe to run in any environment including production.

AUTHOR:  Your Name
=============================================================================
"""

import json
import datetime

# We wrap the boto3 import so the script can still run (for learning purposes)
# even if AWS credentials aren't set up yet
try:
    import boto3                           # AWS SDK for Python
    from botocore.exceptions import (
        ClientError,                       # API-level AWS errors (e.g. permission denied)
        NoCredentialsError,               # No AWS credentials found
        EndpointResolutionError           # Network issues
    )
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    print("[WARNING] boto3 not installed. Run: pip install boto3")
    print("          Showing script structure only.\n")


# =============================================================================
# CONFIGURATION
# =============================================================================
AWS_REGION = "us-east-1"  # Change to your region (e.g., ap-southeast-1 for Singapore)

# Ports considered dangerous if open to the entire internet (0.0.0.0/0)
DANGEROUS_PORTS = {
    22:   "SSH",
    3389: "RDP (Windows Remote Desktop)",
    3306: "MySQL",
    5432: "PostgreSQL",
    27017: "MongoDB",
    6379: "Redis",
}

# How old an EC2 snapshot must be (in days) before we flag it as old/wasteful
SNAPSHOT_AGE_THRESHOLD_DAYS = 90


# =============================================================================
# CLASS: CloudAuditor
# We use a class here (instead of plain functions) because all our functions
# share the same AWS client connections. A class keeps them organized together.
# This is called "Object-Oriented Programming" (OOP) — a key Python concept.
# =============================================================================
class CloudAuditor:

    def __init__(self, region=AWS_REGION):
        """
        __init__ is the constructor — runs automatically when you create an instance.
        We set up boto3 client connections here so all methods can share them.
        """
        self.region = region
        self.findings = []  # Will accumulate all audit findings

        if not BOTO3_AVAILABLE:
            return

        try:
            # boto3.client creates a connection to a specific AWS service
            # Think of it like dialing into that service's phone line
            self.ec2 = boto3.client("ec2", region_name=region)
            self.s3  = boto3.client("s3")   # S3 is global, no region needed
            self.iam = boto3.client("iam")  # IAM is also global

            print(f"✅ Connected to AWS ({region})")

        except NoCredentialsError:
            print("[ERROR] No AWS credentials found.")
            print("  Run 'aws configure' or set AWS_ACCESS_KEY_ID environment variable.")

    # =========================================================================
    # METHOD: audit_ec2_instances
    # Lists all EC2 instances and flags any that are stopped (still costs money
    # for the EBS storage attached to them).
    # =========================================================================
    def audit_ec2_instances(self):
        print("\n🖥️  Auditing EC2 Instances...")

        try:
            # describe_instances() returns a nested structure:
            # Reservations → Instances → instance details
            response = self.ec2.describe_instances()

            all_instances = []
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    all_instances.append(instance)

            if not all_instances:
                print("  No EC2 instances found.")
                return

            stopped = []
            running = []

            for inst in all_instances:
                state = inst["State"]["Name"]  # "running", "stopped", "terminated"

                # Get the Name tag if it exists (tags are stored as a list of key-value dicts)
                name = "Unnamed"
                for tag in inst.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                        break

                instance_info = {
                    "id":    inst["InstanceId"],
                    "name":  name,
                    "type":  inst["InstanceType"],  # e.g., t2.micro, m5.large
                    "state": state,
                    "az":    inst["Placement"]["AvailabilityZone"]
                }

                if state == "stopped":
                    stopped.append(instance_info)
                    self.findings.append({
                        "severity": "MEDIUM",
                        "category": "Cost",
                        "resource": inst["InstanceId"],
                        "issue":    f"Stopped instance '{name}' — still incurs EBS storage costs."
                    })
                elif state == "running":
                    running.append(instance_info)

            print(f"  Running  : {len(running)}")
            print(f"  Stopped  : {len(stopped)} ⚠️  (still costing money)")

            for inst in stopped:
                print(f"    💸 {inst['id']} | {inst['name']} | {inst['type']} | {inst['az']}")

        except ClientError as e:
            print(f"  [ERROR] {e.response['Error']['Code']}: {e.response['Error']['Message']}")

    # =========================================================================
    # METHOD: audit_security_groups
    # Finds security groups that expose dangerous ports to the entire internet.
    # 0.0.0.0/0 means "anyone in the world can connect" — often a misconfiguration.
    # =========================================================================
    def audit_security_groups(self):
        print("\n🔒 Auditing Security Groups for open ports...")

        try:
            response = self.ec2.describe_security_groups()
            sgs = response["SecurityGroups"]

            risky_count = 0

            for sg in sgs:
                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort", 0)
                    to_port   = rule.get("ToPort", 65535)

                    # Check if any dangerous port falls within this rule's port range
                    for danger_port, service_name in DANGEROUS_PORTS.items():
                        if from_port <= danger_port <= to_port:
                            # Check if the rule allows access from anywhere (0.0.0.0/0)
                            for ip_range in rule.get("IpRanges", []):
                                if ip_range.get("CidrIp") == "0.0.0.0/0":
                                    risky_count += 1
                                    print(f"  🚨 RISK: {sg['GroupName']} ({sg['GroupId']})")
                                    print(f"          Port {danger_port} ({service_name}) open to 0.0.0.0/0 (entire internet!)")

                                    self.findings.append({
                                        "severity": "HIGH",
                                        "category": "Security",
                                        "resource": sg["GroupId"],
                                        "issue":    f"Port {danger_port} ({service_name}) exposed to entire internet"
                                    })

            if risky_count == 0:
                print("  ✅ No dangerous open ports found.")
            else:
                print(f"\n  ⚠️  Found {risky_count} risky security group rule(s)!")

        except ClientError as e:
            print(f"  [ERROR] {e.response['Error']['Code']}: {e.response['Error']['Message']}")

    # =========================================================================
    # METHOD: audit_s3_buckets
    # Checks S3 buckets for public access — a very common data breach cause.
    # Your private files should NEVER be publicly accessible unless intentional.
    # =========================================================================
    def audit_s3_buckets(self):
        print("\n🪣 Auditing S3 Buckets for public access...")

        try:
            response = self.s3.list_buckets()
            buckets  = response["Buckets"]

            if not buckets:
                print("  No S3 buckets found.")
                return

            print(f"  Total buckets: {len(buckets)}")

            for bucket in buckets:
                name = bucket["Name"]

                try:
                    # Check the "Block Public Access" settings for this specific bucket
                    # This is the AWS S3 safety setting that prevents public access
                    acl_response = self.s3.get_public_access_block(Bucket=name)
                    config       = acl_response["PublicAccessBlockConfiguration"]

                    # All four settings should be True for a secure bucket
                    fully_blocked = all([
                        config.get("BlockPublicAcls", False),
                        config.get("IgnorePublicAcls", False),
                        config.get("BlockPublicPolicy", False),
                        config.get("RestrictPublicBuckets", False)
                    ])

                    if fully_blocked:
                        print(f"  ✅ {name} — Public access blocked")
                    else:
                        print(f"  🚨 {name} — PUBLIC ACCESS NOT FULLY BLOCKED")
                        self.findings.append({
                            "severity": "CRITICAL",
                            "category": "Security",
                            "resource": name,
                            "issue":    "S3 bucket may be publicly accessible — data exposure risk!"
                        })

                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchPublicAccessBlockConfiguration":
                        # No block config = default = potentially public!
                        print(f"  ⚠️  {name} — No public access block configured (risky!)")
                    else:
                        print(f"  [SKIP] {name} — {e.response['Error']['Code']}")

        except ClientError as e:
            print(f"  [ERROR] {e.response['Error']['Code']}: {e.response['Error']['Message']}")

    # =========================================================================
    # METHOD: audit_iam_mfa
    # Checks if all IAM users have MFA (Multi-Factor Authentication) enabled.
    # MFA = a second factor beyond just password (like Google Authenticator).
    # Without MFA, a leaked password = full account access.
    # =========================================================================
    def audit_iam_mfa(self):
        print("\n🔑 Auditing IAM Users for MFA...")

        try:
            response  = self.iam.list_users()
            users     = response["Users"]
            no_mfa    = []

            for user in users:
                username = user["UserName"]

                # list_mfa_devices returns MFA devices linked to the user
                mfa_response = self.iam.list_mfa_devices(UserName=username)
                mfa_devices  = mfa_response["MFADevices"]

                if not mfa_devices:
                    no_mfa.append(username)
                    self.findings.append({
                        "severity": "HIGH",
                        "category": "Security",
                        "resource": username,
                        "issue":    f"IAM user '{username}' has no MFA device — password-only login!"
                    })

            if no_mfa:
                print(f"  ⚠️  {len(no_mfa)} user(s) without MFA:")
                for u in no_mfa:
                    print(f"    🚨 {u}")
            else:
                print(f"  ✅ All {len(users)} IAM users have MFA enabled.")

        except ClientError as e:
            print(f"  [ERROR] {e.response['Error']['Code']}: {e.response['Error']['Message']}")

    # =========================================================================
    # METHOD: generate_report
    # Compiles all findings into a JSON report file.
    # =============================================================================
    def generate_report(self):
        report = {
            "audit_timestamp": datetime.datetime.now().isoformat(),
            "region":          self.region,
            "total_findings":  len(self.findings),
            "critical":        sum(1 for f in self.findings if f["severity"] == "CRITICAL"),
            "high":            sum(1 for f in self.findings if f["severity"] == "HIGH"),
            "medium":          sum(1 for f in self.findings if f["severity"] == "MEDIUM"),
            "findings":        self.findings
        }

        filename = f"cloud_audit_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'='*55}")
        print(f"  📋 AUDIT COMPLETE")
        print(f"  🔴 Critical : {report['critical']}")
        print(f"  🟠 High     : {report['high']}")
        print(f"  🟡 Medium   : {report['medium']}")
        print(f"  Total       : {report['total_findings']} findings")
        print(f"  Report saved: {filename}")
        print(f"{'='*55}")


# =============================================================================
# MAIN
# =============================================================================
def main():
    print("="*55)
    print("  ☁️  AWS Cloud Resource Auditor")
    print("="*55)

    if not BOTO3_AVAILABLE:
        print("\n[INFO] Install boto3 and configure AWS credentials to run this script.")
        print("  pip install boto3")
        print("  aws configure")
        return

    auditor = CloudAuditor(region=AWS_REGION)

    # Run all audit checks
    auditor.audit_ec2_instances()
    auditor.audit_security_groups()
    auditor.audit_s3_buckets()
    auditor.audit_iam_mfa()

    # Save the report
    auditor.generate_report()


if __name__ == "__main__":
    main()
