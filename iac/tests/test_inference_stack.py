# mermaid-api/iac/tests/test_inference_stack.py
import json

import aws_cdk as cdk
from aws_cdk import aws_ecr as ecr, aws_s3 as s3, aws_sns as sns
from aws_cdk.assertions import Match, Template
from settings.dev import DEV_SETTINGS
from stacks.inference import InferenceStack


def _template():
    app = cdk.App()
    env = cdk.Environment(account="111111111111", region="us-east-1")
    deps = cdk.Stack(app, "deps", env=env)
    repo = ecr.Repository(deps, "Repo", repository_name="mermaid-inference-pyspacer")
    config_bucket = s3.Bucket(deps, "Config", bucket_name="mermaid-config")
    image_bucket = s3.Bucket(deps, "Img", bucket_name="mermaid-image-processing")
    alerts_topic = sns.Topic(deps, "Alerts")
    stack = InferenceStack(
        app,
        "dev-mermaid-inference",
        env=env,
        config=DEV_SETTINGS,
        inference_repo=repo,
        config_bucket=config_bucket,
        image_bucket=image_bucket,
        alerts_topic=alerts_topic,
    )
    return Template.from_stack(stack)


def test_function_config():
    template = _template()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "PackageType": "Image",
            "MemorySize": 10240,
            "Timeout": 600,
            "Architectures": ["arm64"],
            "ReservedConcurrentExecutions": 20,
            "TracingConfig": {"Mode": "Active"},
            "EphemeralStorage": {"Size": 2048},
            "Environment": {
                "Variables": {
                    "CONFIG_BUCKET": "mermaid-config",
                    "INFERENCE_NUM_THREADS": "6",
                }
            },
        },
    )


def test_function_role_can_read_both_buckets():
    template = _template()
    # The function role must read BOTH buckets: the config bucket scoped to the
    # classifier/* prefix, and the image bucket. grant_read emits one s3 read
    # statement per bucket, so two distinct statements must be present and the
    # config grant must carry the classifier/* prefix — neither can silently drop.
    read_stmts = [
        stmt
        for policy in template.find_resources("AWS::IAM::Policy").values()
        for stmt in policy["Properties"]["PolicyDocument"]["Statement"]
        if "s3:GetObject*"
        in (stmt["Action"] if isinstance(stmt["Action"], list) else [stmt["Action"]])
    ]
    assert len(read_stmts) >= 2, "expected a read grant for each of the two buckets"
    assert "classifier/*" in json.dumps(read_stmts), "config bucket must be classifier/*-scoped"


def test_errors_and_throttles_alarms_exist():
    template = _template()
    # Errors + Throttles (AWS/Lambda) + ProcessingErrors (log-metric-filter) = 3.
    template.resource_count_is("AWS::CloudWatch::Alarm", 3)
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm", {"MetricName": "Errors", "Namespace": "AWS/Lambda"}
    )
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm", {"MetricName": "Throttles", "Namespace": "AWS/Lambda"}
    )


def test_processing_errors_alarm_from_log_metric_filter():
    template = _template()
    # A metric filter turns the handler's "[classify.processing_error]" marker
    # into a counted metric in a MERMAID/<env>/Inference namespace.
    template.has_resource_properties(
        "AWS::Logs::MetricFilter",
        {
            "FilterPattern": '"[classify.processing_error]"',
            "MetricTransformations": Match.array_with(
                [
                    Match.object_like(
                        {
                            "MetricName": "ProcessingErrors",
                            "MetricNamespace": "MERMAID/dev/Inference",
                        }
                    )
                ]
            ),
        },
    )
    # ...alarmed on a count threshold (>=5 in a 5-minute window).
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "MetricName": "ProcessingErrors",
            "Namespace": "MERMAID/dev/Inference",
            "Threshold": 5,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        },
    )


def test_no_local_delivery_infrastructure():
    template = _template()
    # Alarms publish to ApiStack's shared topic — InferenceStack creates neither
    # its own SNS topic nor a second Chatbot config.
    template.resource_count_is("AWS::SNS::Topic", 0)
    template.resource_count_is("AWS::Chatbot::SlackChannelConfiguration", 0)


def test_function_log_group_has_retention():
    template = _template()
    # An explicit log group with finite retention (not Lambda's never-expire
    # default), removed with the stack.
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/lambda/dev-mermaid-inference-pyspacer",
            "RetentionInDays": 30,
        },
    )


def test_inference_settings_use_model_build_tag():
    from settings.dev import DEV_SETTINGS

    # The image tag is the model-build tag vN-K, not a semver.
    assert DEV_SETTINGS.inference.image_tag == "v2-1"
    assert not hasattr(DEV_SETTINGS.inference, "image_version")
