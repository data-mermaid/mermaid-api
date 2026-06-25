"""
Centralized cdk-nag suppressions for all stacks.

Suppressions are resource-scoped (by construct path) so that new resources
added to a stack are NOT automatically covered — the PR gate will catch them.

Each suppression documents the reason and whether the finding is:
  - ACCEPTED: The current configuration is intentional and appropriate.
  - TODO: Should be addressed in a future ticket.
"""

from aws_cdk import Stack
from cdk_nag import NagPackSuppression, NagSuppressions

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ACCEPTED = "ACCEPTED"
TODO = "TODO"


def _suppress_by_path(
    stack: Stack,
    path: str,
    suppressions: list[NagPackSuppression],
) -> None:
    """Suppress findings on a specific construct by its path relative to the stack."""
    NagSuppressions.add_resource_suppressions_by_path(
        stack,
        f"/{stack.stack_name}/{path}",
        suppressions,
    )


def _path_exists(stack: Stack, path: str) -> bool:
    """True if a construct exists at `path` (slash-separated) relative to the stack.

    Used to gate suppressions for *optional* resources — e.g. the Slack Chatbot
    config, which is only created when both Slack workspace and channel IDs are
    set. Without this guard, cdk-nag raises "suppression path did not match any
    resource" and synth fails whenever Slack is unconfigured.
    """
    node = stack
    for segment in path.split("/"):
        child = node.node.try_find_child(segment)
        if child is None:
            return False
        node = child
    return True


# ---------------------------------------------------------------------------
# GithubAccessStack
# ---------------------------------------------------------------------------


def suppress_github_access(stack: Stack) -> None:
    _suppress_by_path(
        stack,
        "GithubAccessRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{TODO}: GithubAccessRole uses AdministratorAccess — "
                "scope down to specific CDK deployment permissions.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/AdministratorAccess",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "ClassifierReleaseMlflowPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: sagemaker-mlflow exposes no resource-level "
                "ARNs; the release role is scoped liberally to the project's "
                "SageMaker-Studio MLflow apps by design.",
                applies_to=["Action::sagemaker-mlflow:*", "Resource::*"],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "MermaidClassifierReleaseRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: release-role S3 access is prefix-scoped to "
                "dev-datamermaid-sm-data/mlflow/* (read) and "
                "mermaid-config/classifier/* (read+write); the object-level and "
                "ListBucket wildcards are the minimal set the CDK grants emit.",
                applies_to=[
                    "Action::s3:GetObject*",
                    "Action::s3:GetBucket*",
                    "Action::s3:List*",
                    "Action::s3:PutObject*",
                    "Action::s3:DeleteObject*",
                    "Action::s3:Abort*",
                    "Resource::arn:aws:s3:::dev-datamermaid-sm-data/mlflow/*",
                    "Resource::arn:aws:s3:::mermaid-config/classifier/*",
                ],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# CommonStack
# ---------------------------------------------------------------------------


def suppress_common(stack: Stack) -> None:
    # --- VPC ---
    _suppress_by_path(
        stack,
        "Vpc/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-VPC7",
                reason=f"{TODO}: Enable VPC Flow Logs for network traffic auditing.",
            ),
        ],
    )

    # --- Secrets Manager ---
    for secret_path in ["DBCredentialsSecret/Resource", "ReportS3UserSecret/Resource"]:
        _suppress_by_path(
            stack,
            secret_path,
            [
                NagPackSuppression(
                    id="AwsSolutions-SMG4",
                    reason=f"{TODO}: Configure automatic rotation for this secret.",
                ),
            ],
        )

    # --- RDS ---
    _suppress_by_path(
        stack,
        "PostgresRdsV2/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-RDS2",
                reason=f"{TODO}: Enable storage encryption on the RDS instance. "
                "May require a migration for the existing database.",
            ),
            NagPackSuppression(
                id="AwsSolutions-RDS3",
                reason=f"{TODO}: Evaluate multi-AZ for high availability. "
                "Currently single-AZ to manage costs.",
            ),
            NagPackSuppression(
                id="AwsSolutions-RDS11",
                reason=f"{ACCEPTED}: Port obfuscation provides minimal security "
                "benefit; the database is in a private isolated subnet.",
            ),
        ],
    )

    # --- S3 Buckets ---
    s3_bucket_paths = [
        "MermaidApiBackupBucket/Resource",
        "MermaidApiConfigBucket/Resource",
        "MermaidApiDataBucket/Resource",
        "MermaidImageProcessingBackupBucket/Resource",
    ]
    for bucket_path in s3_bucket_paths:
        _suppress_by_path(
            stack,
            bucket_path,
            [
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason=f"{TODO}: Enable server access logging on this S3 bucket.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-S10",
                    reason=f"{TODO}: Add aws:SecureTransport condition to the bucket policy.",
                ),
            ],
        )

    # --- KMS ---
    _suppress_by_path(
        stack,
        "ecsExecKmsKey/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-KMS5",
                reason=f"{TODO}: Enable automatic key rotation on the ECS exec KMS key.",
            ),
        ],
    )

    # --- ASG Instance role (CDK-managed ECS instance policy) ---
    _suppress_by_path(
        stack,
        "AsgInstance/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Wildcard permissions are generated by CDK "
                "for the ECS container instance role (ecs:Submit*, Resource::*).",
                applies_to=[
                    "Action::ecs:Submit*",
                    "Resource::*",
                ],
            ),
        ],
    )

    # --- ASG ---
    _suppress_by_path(
        stack,
        "ASG2/ASG",
        [
            NagPackSuppression(
                id="AwsSolutions-EC26",
                reason=f"{TODO}: Enable EBS encryption on the ASG launch template.",
            ),
            NagPackSuppression(
                id="AwsSolutions-AS3",
                reason=f"{TODO}: Configure SNS notifications for all ASG scaling events.",
            ),
        ],
    )

    # --- CDK-managed ASG drain-hook Lambda ---
    _suppress_by_path(
        stack,
        "ASG2/DrainECSHook/Function/ServiceRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AWSLambdaBasicExecutionRole is the standard "
                "managed policy for Lambda logging, generated by CDK.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "ASG2/DrainECSHook/Function/ServiceRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Wildcard permissions for the drain-hook Lambda "
                "are CDK-generated to manage the ASG lifecycle.",
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "ASG2/DrainECSHook/Function/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-L1",
                reason=f"{ACCEPTED}: The drain-hook Lambda runtime is managed by "
                "the CDK ECS construct and auto-updated on CDK upgrades.",
            ),
        ],
    )

    # --- ASG Lifecycle SNS Topic ---
    _suppress_by_path(
        stack,
        "ASG2/LifecycleHookDrainHook/Topic/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-SNS3",
                reason=f"{TODO}: Add aws:SecureTransport condition to the SNS topic policy.",
            ),
        ],
    )

    # --- ALB ---
    _suppress_by_path(
        stack,
        "MermaidApiLoadBalancer/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-ELB2",
                reason=f"{TODO}: Enable access logging on the Application Load Balancer.",
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "MermaidApiLoadBalancer/SecurityGroup/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-EC23",
                reason=f"{ACCEPTED}: The ALB is internet-facing and must allow "
                "inbound traffic from 0.0.0.0/0 on ports 80/443.",
            ),
        ],
    )

    # --- VPC Flow Logs ---
    _suppress_by_path(
        stack,
        "VpcFlowLogsAccessLogsBucket/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-S1",
                reason=f"{ACCEPTED}: This bucket IS the access logs target — enabling "
                "server access logging on it would be circular.",
            ),
        ],
    )

    _suppress_by_path(
        stack,
        "VpcFlowLogsRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: logs:CreateLogGroup and logs:DescribeLogGroups do not "
                "support resource-level permissions; Resource::* is required by CloudWatch Logs.",
                applies_to=["Resource::*"],
            ),
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Log-stream wildcard (<LogGroup.Arn>:*) is required for "
                "VPC Flow Logs to create and write to individual log streams.",
                applies_to=["Resource::<VpcFlowLogsGroupC5F6A8C5.Arn>:*"],
            ),
        ],
    )

    _suppress_by_path(
        stack,
        "AthenaRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: S3 object-level actions (GetObject/ListBucket) require "
                "the /* wildcard on the VPC flow logs bucket.",
                applies_to=["Resource::<VpcFlowLogsBucket3B29CF33.Arn>/*"],
            ),
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Glue table wildcard is required to query all tables in "
                "the vpc_flow_logs database via Athena.",
                applies_to=[
                    "Resource::arn:aws:glue:us-east-1:554812291621:table/<VpcFlowLogsDatabase>/*"
                ],
            ),
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: S3 object-level actions on Athena results bucket require "
                "the /* wildcard to read/write/delete individual query result objects.",
                applies_to=["Resource::<AthenaResultsBucket879938FA.Arn>/*"],
            ),
        ],
    )

    # --- CICD Bot / CDK Role Policy ---
    _suppress_by_path(
        stack,
        "CDKRolePolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Wildcard on cdk-* roles is required for CDK "
                "bootstrapped deployments via the CICD_Bot user.",
                applies_to=[
                    "Resource::arn:aws:iam::554812291621:role/cdk-*",
                ],
            ),
        ],
    )

    # --- Report S3 User Policy ---
    _suppress_by_path(
        stack,
        "ReportS3UserPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Wildcard on object key (/*) is required for "
                "the report user to read/write objects in the data bucket.",
            ),
        ],
    )

    # --- Cost Anomaly Detection SNS topic ---
    _suppress_by_path(
        stack,
        "CostAlertsTopic/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-SNS2",
                reason=f"{TODO}: Encrypt the cost alerts SNS topic with a KMS CMK.",
            ),
            NagPackSuppression(
                id="AwsSolutions-SNS3",
                reason=f"{TODO}: Add aws:SecureTransport condition to the cost alerts SNS topic policy.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# StaticSiteStack
# ---------------------------------------------------------------------------


def suppress_static_site(stack: Stack) -> None:
    # --- S3 Bucket ---
    for path in ["Bucket/Resource", "Bucket/Policy/Resource"]:
        _suppress_by_path(
            stack,
            path,
            [
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason=f"{TODO}: Enable server access logging on the static site bucket.",
                ),
                NagPackSuppression(
                    id="AwsSolutions-S10",
                    reason=f"{TODO}: Add aws:SecureTransport condition to the bucket policy.",
                ),
            ],
        )

    # --- CloudFront Distribution ---
    _suppress_by_path(
        stack,
        "Distribution/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-CFR1",
                reason=f"{ACCEPTED}: Geo restrictions are not required — "
                "MERMAID is a global marine-data platform.",
            ),
            NagPackSuppression(
                id="AwsSolutions-CFR2",
                reason=f"{TODO}: Evaluate adding AWS WAF to the CloudFront distribution.",
            ),
            NagPackSuppression(
                id="AwsSolutions-CFR3",
                reason=f"{TODO}: Enable CloudFront access logging.",
            ),
            NagPackSuppression(
                id="AwsSolutions-CFR7",
                reason=f"{TODO}: Migrate from Origin Access Identity (OAI) to "
                "Origin Access Control (OAC).",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# ApiStack
# ---------------------------------------------------------------------------

# Common IAM5 suppression for CDK-generated S3/SQS grant wildcards on task roles.
_API_IAM5_SUPPRESSION = NagPackSuppression(
    id="AwsSolutions-IAM5",
    reason=f"{ACCEPTED}: Wildcard permissions are generated by CDK grant helpers "
    "(grant_read_write, grant_send_messages) and scoped to specific bucket/log-group ARNs.",
)

_API_ECS2_SUPPRESSION = NagPackSuppression(
    id="AwsSolutions-ECS2",
    reason=f"{ACCEPTED}: Only non-sensitive configuration values "
    "(ENV_ID, BRANCH_NAME, queue URLs, etc.) are passed as "
    "environment variables. Secrets use Secrets Manager.",
)

_API_EXEC_ROLE_IAM5 = NagPackSuppression(
    id="AwsSolutions-IAM5",
    reason=f"{ACCEPTED}: Execution role wildcard (Resource::*) is CDK-generated "
    "for pulling ECR images and reading Secrets Manager.",
)


def suppress_api(stack: Stack) -> None:
    # Task definition groups: each has TaskRole, Resource, and ExecutionRole paths
    task_def_ids = [
        "ScheduledBackupTaskDef",
        "SummaryCacheTaskDef",
        "ApiTaskDefinition",
        "General/Worker/QueueProcessingTaskDef",
        "ImageProcess/Worker/QueueProcessingTaskDef",
    ]

    _xray_iam4 = NagPackSuppression(
        id="AwsSolutions-IAM4",
        reason=f"{ACCEPTED}: AWSXRayDaemonWriteAccess is the least-privilege AWS managed "
        "policy for X-Ray tracing; no customer-managed equivalent exists.",
        applies_to=[
            "Policy::arn:<AWS::Partition>:iam::aws:policy/AWSXRayDaemonWriteAccess",
        ],
    )

    for td in task_def_ids:
        # Task role: IAM4 for X-Ray managed policy, IAM5 wildcards from CDK grants
        _suppress_by_path(stack, f"{td}/TaskRole/Resource", [_xray_iam4])
        _suppress_by_path(stack, f"{td}/TaskRole/DefaultPolicy/Resource", [_API_IAM5_SUPPRESSION])
        # Task definition resource (ECS2 - env vars)
        _suppress_by_path(stack, f"{td}/Resource", [_API_ECS2_SUPPRESSION])
        # Execution role default policy (IAM5 - ECR/Secrets wildcard)
        _suppress_by_path(stack, f"{td}/ExecutionRole/DefaultPolicy/Resource", [_API_EXEC_ROLE_IAM5])

    # Scheduled backup events role
    _suppress_by_path(
        stack,
        "ScheduledBackupTaskDef/EventsRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Events role wildcard is CDK-generated for "
                "launching scheduled ECS tasks in the cluster.",
            ),
        ],
    )

    # --- SQS Queues (General + ImageProcess workers) ---
    for worker_id in ["General", "ImageProcess"]:
        for queue_path in ["ECSWorker/DLQ/Resource", "ECSWorker/Queue/Resource"]:
            _suppress_by_path(
                stack,
                f"{worker_id}/{queue_path}",
                [
                    NagPackSuppression(
                        id="AwsSolutions-SQS4",
                        reason=f"{TODO}: Add aws:SecureTransport condition to the SQS queue policy.",
                    ),
                ],
            )
        _suppress_by_path(
            stack,
            f"{worker_id}/ECSWorker/Topic/Resource",
            [
                NagPackSuppression(
                    id="AwsSolutions-SNS3",
                    reason=f"{TODO}: Add aws:SecureTransport condition to the SNS topic policy.",
                ),
            ],
        )

    # --- MonitoringAlerts SNS topic ---
    _suppress_by_path(
        stack,
        "Alerts/AlertsTopic/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-SNS2",
                reason=f"{TODO}: Encrypt the alerts SNS topic with a KMS CMK.",
            ),
            NagPackSuppression(
                id="AwsSolutions-SNS3",
                reason=f"{TODO}: Add aws:SecureTransport condition to the alerts SNS topic policy.",
            ),
        ],
    )

    # --- Chatbot Slack channel role ---
    # The Slack Chatbot config (and its role/policy) is only created when both
    # Slack workspace and channel IDs are configured, so gate these suppressions
    # on the resource actually existing.
    if _path_exists(stack, "Alerts/SlackChannelConfigurationRole/Resource"):
        _suppress_by_path(
            stack,
            "Alerts/SlackChannelConfigurationRole/Resource",
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM4",
                    reason=f"{ACCEPTED}: AmazonQDeveloperAccess is an AWS managed policy with no "
                    "customer-managed equivalent for Amazon Q Developer in Slack.",
                    applies_to=[
                        "Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonQDeveloperAccess",
                    ],
                ),
            ],
        )
        _suppress_by_path(
            stack,
            "Alerts/SlackObservabilityPolicy/Resource",
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=f"{ACCEPTED}: Observability read actions (cloudwatch:Get*, ecs:List*, etc.) "
                    "operate on account-wide resources by design — CloudWatch metrics and ECS services "
                    "cannot be scoped to a single ARN without breaking Describe/List semantics.",
                ),
            ],
        )


# ---------------------------------------------------------------------------
# SagemakerStack (dev only)
# ---------------------------------------------------------------------------


def suppress_sagemaker(stack: Stack, prefix: str) -> None:
    # --- SageMaker Execution Role ---
    _suppress_by_path(
        stack,
        f"{prefix}SagemakerExecutionRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{TODO}: Replace AmazonSageMakerFullAccess and "
                "SageMakerStudioFullAccess with scoped customer-managed policies.",
                applies_to=[
                    "Policy::arn:aws:iam::aws:policy/AmazonSageMakerFullAccess",
                    "Policy::arn:aws:iam::aws:policy/SageMakerStudioFullAccess",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        f"{prefix}SagemakerExecutionRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: Wildcard permissions are generated by CDK "
                "grant helpers and scoped to specific bucket ARNs.",
            ),
        ],
    )

    # --- Inline IAM policies ---
    for policy_path in [
        "MlflowRolePolicy/Resource",
        "SagemakerStartSessionPolicy/Resource",
        "GlueSessionPolicy/Resource",
        "SagemakerPassSelfPolicy/Resource",
    ]:
        _suppress_by_path(
            stack,
            policy_path,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=f"{ACCEPTED}: SageMaker, MLflow, and Glue wildcards are "
                    "required for interactive notebook sessions.",
                ),
            ],
        )

    # --- Shared Mermaid SageMaker launcher role's inline policies ---
    # ECR / SageMaker / Logs / S3 wildcards are scoped to specific repos
    # (mermaid-*-jobs), Training+Processing jobs in this account, the
    # /aws/sagemaker/* CloudWatch log groups, and the runs/* prefix of
    # the SageMaker data bucket. Required by the launcher scripts to
    # pull the job image, submit Training/Processing jobs, tail logs,
    # and read/write run data.
    for policy_path in [
        "MermaidSagemakerLauncherEcrPolicy/Resource",
        "MermaidSagemakerLauncherSagemakerPolicy/Resource",
        "MermaidSagemakerLauncherLogsPolicy/Resource",
        "MermaidSagemakerLauncherPassRolePolicy/Resource",
        f"{prefix}MermaidSagemakerLauncherRole/DefaultPolicy/Resource",
    ]:
        _suppress_by_path(
            stack,
            policy_path,
            [
                NagPackSuppression(
                    id="AwsSolutions-IAM5",
                    reason=f"{ACCEPTED}: Wildcards are scoped to mermaid-*-jobs "
                    "ECR repos, SageMaker Training+Processing jobs in this account, "
                    "/aws/sagemaker/* CloudWatch log groups, and the runs/* prefix "
                    "of the SageMaker data bucket.",
                ),
            ],
        )

    # --- SageMaker S3 Buckets ---
    for bucket_path in [
        f"{prefix}SourcesBucket/Resource",
        f"{prefix}DataBucket/Resource",
    ]:
        _suppress_by_path(
            stack,
            bucket_path,
            [
                NagPackSuppression(
                    id="AwsSolutions-S1",
                    reason=f"{TODO}: Enable server access logging on this SageMaker S3 bucket.",
                ),
            ],
        )


# ---------------------------------------------------------------------------
# CloudTrailStack
# ---------------------------------------------------------------------------


def suppress_cloudtrail(stack: Stack) -> None:
    _suppress_by_path(
        stack,
        "CloudTrailBucket/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-S1",
                reason=f"{TODO}: Enable server access logging on the CloudTrail S3 bucket.",
            ),
        ],
    )


# ---------------------------------------------------------------------------
# GuardDutyStack
# ---------------------------------------------------------------------------


def suppress_guardduty(stack: Stack) -> None:
    # --- CreateGuardDutySLR Lambda ---
    _suppress_by_path(
        stack,
        "CreateGuardDutySLR/ServiceRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AWSLambdaBasicExecutionRole is the standard managed policy "
                "for Lambda CloudWatch logging; no customer-managed equivalent exists.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "CreateGuardDutySLR/ServiceRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: iam:CreateServiceLinkedRole and guardduty:UpdateDetector "
                "do not support resource-level scoping; Resource::* is required.",
                applies_to=["Resource::*"],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "CreateGuardDutySLR/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-L1",
                reason=f"{ACCEPTED}: Runtime is PYTHON_3_13 (latest); cdk-nag may lag behind "
                "the actual latest runtime release.",
            ),
        ],
    )

    # --- CDK custom resource provider framework Lambda ---
    _suppress_by_path(
        stack,
        "GuardDutySLRProvider/framework-onEvent/ServiceRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AWSLambdaBasicExecutionRole on CDK-generated provider "
                "framework Lambda; no customer-managed equivalent.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "GuardDutySLRProvider/framework-onEvent/ServiceRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: CDK-generated provider framework policy; wildcard on "
                "the onEvent Lambda ARN is required for invoking the custom resource handler.",
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "GuardDutySLRProvider/framework-onEvent/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-L1",
                reason=f"{ACCEPTED}: CDK custom resource provider framework Lambda; "
                "runtime is managed by CDK and updated on CDK version upgrades.",
            ),
        ],
    )

    # --- GuardDuty service role ---
    _suppress_by_path(
        stack,
        "GuardDutyServiceRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AmazonGuardDutyFullAccess_v2 is the AWS-managed policy "
                "required for GuardDuty malware protection plan operations; no scoped equivalent exists.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonGuardDutyFullAccess_v2",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "GuardDutyServiceRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: EventBridge rule ARNs cannot be pre-determined at deploy time; "
                "Resource::* is required for GuardDuty to manage its own event rules. "
                "S3 object wildcards (bucket/*) are scoped to the specific protected buckets.",
            ),
        ],
    )

    # --- EC2 instance role (SSM + CloudWatch agent) ---
    _suppress_by_path(
        stack,
        "EC2SSMRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AmazonSSMManagedInstanceCore and CloudWatchAgentServerPolicy "
                "are standard managed policies for EC2 SSM and CloudWatch agent; "
                "no customer-managed equivalents exist.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/AmazonSSMManagedInstanceCore",
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/CloudWatchAgentServerPolicy",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "EC2SSMRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: guardduty:CreateDetector and UpdateDetector do not "
                "support resource-level scoping; Resource::* is required.",
                applies_to=["Resource::*"],
            ),
        ],
    )

    # --- ECS execution role ---
    _suppress_by_path(
        stack,
        "ECSExecRole/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM4",
                reason=f"{ACCEPTED}: AmazonECSTaskExecutionRolePolicy is the standard managed "
                "policy for ECS task execution; no customer-managed equivalent exists.",
                applies_to=[
                    "Policy::arn:<AWS::Partition>:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                ],
            ),
        ],
    )
    _suppress_by_path(
        stack,
        "ECSExecRole/DefaultPolicy/Resource",
        [
            NagPackSuppression(
                id="AwsSolutions-IAM5",
                reason=f"{ACCEPTED}: guardduty:CreateDetector and UpdateDetector do not "
                "support resource-level scoping; Resource::* is required.",
                applies_to=["Resource::*"],
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Main entry point — call from app.py after all stacks are created.
# ---------------------------------------------------------------------------


def apply_all(
    gh_access_stack: Stack,
    common_stack: Stack,
    dev_static_site_stack: Stack,
    prod_static_site_stack: Stack,
    dev_api_stack: Stack,
    prod_api_stack: Stack,
    dev_sagemaker_stack: Stack,
    cloudtrail_stack: Stack | None = None,
    guardduty_stack: Stack | None = None,
) -> None:
    suppress_github_access(gh_access_stack)
    suppress_common(common_stack)

    for static_stack in [dev_static_site_stack, prod_static_site_stack]:
        suppress_static_site(static_stack)

    for api_stack in [dev_api_stack, prod_api_stack]:
        suppress_api(api_stack)

    suppress_sagemaker(dev_sagemaker_stack, prefix="dev")

    if cloudtrail_stack:
        suppress_cloudtrail(cloudtrail_stack)
    if guardduty_stack:
        suppress_guardduty(guardduty_stack)
