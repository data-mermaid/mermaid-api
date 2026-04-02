from typing import List

from aws_cdk import CustomResource, Duration, Stack
from aws_cdk import aws_guardduty as guardduty
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import custom_resources as cr
from constructs import Construct


class GuardDutyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, s3_buckets: List[str], **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda to create the service-linked role
        create_slr_lambda = lambda_.Function(
            self,
            "CreateGuardDutySLR",
            runtime=lambda_.Runtime.PYTHON_3_13,
            handler="index.handler",
            code=lambda_.InlineCode("""
import boto3
from botocore.exceptions import ClientError

def handler(event, context):
    iam = boto3.client('iam')
    gd = boto3.client('guardduty')
    if event['RequestType'] in ['Create', 'Update']:
        for service in [
            'guardduty.amazonaws.com',
            'malware-protection.guardduty.amazonaws.com'
        ]:
            try:
                iam.create_service_linked_role(AWSServiceName=service)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                if error_code == 'InvalidInput' and 'has been taken' in error_message:
                    # Role already exists, ignore
                    pass
                else:
                    raise

        # Get existing detector ID
        detectors = gd.list_detectors()
        if detectors['DetectorIds']:
            detector_id = detectors['DetectorIds'][0]

            # Enable runtime monitoring with agent deployment
            gd.update_detector(
                DetectorId=detector_id,
                Features=[
                    {
                        'Name': 'RUNTIME_MONITORING',
                        'Status': 'ENABLED',
                        'AdditionalConfiguration': [
                            {
                                'Name': 'EC2_AGENT_MANAGEMENT',
                                'Status': 'ENABLED'
                            },
                            {
                                'Name': 'ECS_FARGATE_AGENT_MANAGEMENT',
                                'Status': 'ENABLED'
                            }
                        ]
                    }
                ]
            )
    return {'Status': 'SUCCESS'}
            """),
            timeout=Duration.seconds(300),
            initial_policy=[
                iam.PolicyStatement(actions=["iam:CreateServiceLinkedRole"], resources=["*"]),
                iam.PolicyStatement(
                    actions=["guardduty:UpdateDetector", "guardduty:ListDetectors"],
                    resources=["*"],
                ),
            ],
        )

        # Create Custom Resource to trigger the Lambda
        provider = cr.Provider(self, "GuardDutySLRProvider", on_event_handler=create_slr_lambda)

        create_slr_resource = CustomResource(
            self,
            "CreateGuardDutyServiceLinkedRole",
            service_token=provider.service_token,
        )

        detector = guardduty.CfnDetector(
            self,
            "GuardDutyDetector",
            enable=True,
            features=[
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="S3_DATA_EVENTS", status="ENABLED"
                ),
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="RUNTIME_MONITORING",
                    status="ENABLED",
                    additional_configuration=[
                        guardduty.CfnDetector.CFNFeatureAdditionalConfigurationProperty(
                            name="EC2_AGENT_MANAGEMENT", status="ENABLED"
                        ),
                        guardduty.CfnDetector.CFNFeatureAdditionalConfigurationProperty(
                            name="ECS_FARGATE_AGENT_MANAGEMENT", status="ENABLED"
                        ),
                    ],
                ),
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="EBS_MALWARE_PROTECTION", status="ENABLED"
                ),
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="RDS_LOGIN_EVENTS", status="ENABLED"
                ),
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="LAMBDA_NETWORK_LOGS", status="ENABLED"
                ),
                guardduty.CfnDetector.CFNFeatureConfigurationProperty(
                    name="EKS_AUDIT_LOGS", status="DISABLED"
                ),
            ],
        )
        detector.node.add_dependency(create_slr_resource)

        guardduty_role_name = "AmazonGuardDutyAdminServiceRole"
        guardduty_role = iam.Role(
            self,
            "GuardDutyServiceRole",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("malware-protection-plan.guardduty.amazonaws.com"),
                iam.ServicePrincipal("guardduty.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonGuardDutyFullAccess_v2"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            ],
            role_name=guardduty_role_name,
        )

        guardduty_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "events:PutRule",
                    "events:DeleteRule",
                    "events:PutTargets",
                    "events:RemoveTargets",
                    "events:DescribeRule",
                    "events:ListTargetsByRule",
                ],
                resources=["*"],
            )
        )

        for idx, bucket_name in enumerate(s3_buckets):
            protection_plan = guardduty.CfnMalwareProtectionPlan(
                self,
                f"MalwareProtectionPlan-{self.region}-{idx}",
                protected_resource=guardduty.CfnMalwareProtectionPlan.CFNProtectedResourceProperty(
                    s3_bucket=guardduty.CfnMalwareProtectionPlan.S3BucketProperty(
                        bucket_name=bucket_name,
                    )
                ),
                role=guardduty_role.role_arn,
                actions=guardduty.CfnMalwareProtectionPlan.CFNActionsProperty(
                    tagging=guardduty.CfnMalwareProtectionPlan.CFNTaggingProperty(status="ENABLED")
                ),
            )
            protection_plan.node.add_dependency(guardduty_role)

        # Create an EC2 Instance Role with SSM + CW permissions
        ec2_role = iam.Role(
            self,
            "EC2SSMRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"),
                iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchAgentServerPolicy"),
            ],
        )
        ec2_role.add_to_policy(
            iam.PolicyStatement(
                actions=["guardduty:CreateDetector", "guardduty:UpdateDetector"],
                resources=["*"],
            )
        )

        # Create an ECS Execution Role for Fargate
        ecs_exec_role = iam.Role(
            self,
            "ECSExecRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        ecs_exec_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "service-role/AmazonECSTaskExecutionRolePolicy"
            )
        )
        ecs_exec_role.add_to_policy(
            iam.PolicyStatement(
                actions=["guardduty:CreateDetector", "guardduty:UpdateDetector"],
                resources=["*"],
            )
        )
