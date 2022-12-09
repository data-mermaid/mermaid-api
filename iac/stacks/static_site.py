from aws_cdk import (
    CfnOutput, 
    RemovalPolicy,
    Stack,
    aws_route53 as r53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_cloudfront as cf,
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3Deploy,
)
# from static_site import StaticSitePublicS3, StaticSitePrivateS3
from constructs import Construct
from iac.settings import ProjectSettings


class StaticSiteStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        api_zone: r53.HostedZone,
        default_cert: acm.Certificate,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # zone

        # cert
        
        name = "public"
        site_domain = f"{config.env_id}-{name}.{api_zone.zone_name}"

        # cfOAI
        cloudfront_OAI = cf.OriginAccessIdentity(
            self,
            'CloudfrontOAI',
            comment=f"OAI for {id}"
        )
        cfoai_principal = iam.CanonicalUserPrincipal(
            cloudfront_OAI.cloud_front_origin_access_identity_s3_canonical_user_id
        )

        CfnOutput(
            self,
            'StaticSite',
            value=f"https://{site_domain}")

        # bucket
        site_bucket = s3.Bucket(
            self,
            id="Bucket",
            bucket_name=site_domain,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy= RemovalPolicy.DESTROY if config.env_id == "dev" else RemovalPolicy.RETAIN,
            auto_delete_objects= (config.env_id == "dev")
        )

        # Grant access to cloudfront
        policy_stmt = iam.PolicyStatement(
            actions=['s3.GetObject'],
            resources=[site_bucket.arn_for_objects('*')],
            principals=[cfoai_principal]
        )
        site_bucket.add_to_resource_policy(policy_stmt)

        # CloudFront distribution
        domain_names = [site_domain]

        # allow the prod domains into the cloudfront distribution
        if config.env_id == "prod":
            domain_names.append("public.datamermaid.org")

        distribution = cf.Distribution(
            self,
            id="Distribution",
            certificate=default_cert,
            price_class=cf.PriceClass.PRICE_CLASS_100,
            default_root_object="index.html",
            domain_names=domain_names,
            minimum_protocol_version=cf.SecurityPolicyProtocol.TLS_V1_2_2021,
            # error_responses=TODO
            # default_behavior=TODO
        )

        CfnOutput(self,
            id="DistributionId",
            value=distribution.distribution_id,
        )

        r53.ARecord(
            self,
            id="AliasRecord",
            record_name=site_domain,
            target=r53.RecordTarget.from_alias(targets.CloudFrontTarget(distribution=distribution)),
            zone=api_zone,
        )

        # Deploy site contents to S3 bucket
        s3_asset = s3Deploy.Source.asset('../site')

        s3Deploy.BucketDeployment(
            self,
            id="DeployWithInvalidation",
            sources=[s3_asset],
            destination_bucket=site_bucket,
            distribution=distribution,
            distribution_paths=['/*']
        )
