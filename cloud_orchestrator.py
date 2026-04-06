"""
Cloud Orchestrator — Auto-scaling and provisioning on AWS via Boto3.
Allows the agent to spin up clones of itself when it encounters high load.
"""

import os
import logging
import json
import base64

try:
    import boto3
    from botocore.exceptions import NoCredentialsError, PartialCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

class CloudOrchestrator:
    def __init__(self, region_name="us-east-1"):
        self.logger = logging.getLogger("CloudOrchestrator")
        self.region_name = os.getenv("AWS_DEFAULT_REGION", region_name)
        if BOTO3_AVAILABLE:
            try:
                self.ec2 = boto3.client('ec2', region_name=self.region_name)
            except Exception as e:
                self.logger.warning(f"Failed to initialize AWS EC2 client: {e}")
                self.ec2 = None
        else:
            self.ec2 = None
            self.logger.warning("boto3 is not installed. Cloud provisioning disabled.")

    def provision_agent_node(self, instance_type="t3.medium", ami_id=None):
        """
        Provisions a new EC2 instance to run an agent clone.
        Uses UserData to automatically fetch and start the agent on boot.
        """
        if not self.ec2:
            self.logger.error("EC2 client not available. Cannot provision node.")
            return {"status": "error", "message": "Boto3 client not initialized or missing credentials"}

        # Use an Ubuntu 22.04 LTS AMI if not provided (us-east-1 example)
        ami_id = ami_id or "ami-0c7217cdde317cfec" 

        user_data_script = """#!/bin/bash
        apt-get update
        apt-get install -y python3-pip git
        # Note: This requires credentials or a public repo
        git clone https://github.com/your-repo/ultimate-ai-agent.git /opt/agent
        cd /opt/agent
        pip3 install -r requirements.txt
        export HEADLESS_MODE=true
        python3 ultimate_agent.py &
        """

        try:
            self.logger.info(f"☁️ Provisioning new agent node on AWS ({instance_type})...")
            response = self.ec2.run_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                UserData=user_data_script,
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'UltimateAgent-Clone'},
                            {'Key': 'Role', 'Value': 'Autonomous-Node'}
                        ]
                    }
                ]
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            self.logger.info(f"✅ Successfully provisioned instance {instance_id}")
            return {"status": "success", "instance_id": instance_id}

        except Exception as e:
            self.logger.error(f"Failed to provision EC2 instance: {e}")
            return {"status": "error", "message": str(e)}

