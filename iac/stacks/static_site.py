from aws_cdk import (
    CfnOutput, 
    RemovalPolicy,
    Stack,
    aws_route53 as r53,
    aws_route53_targets as targets,
    aws_certificatemanager as acm,
    aws_cloudfront as cf,
    aws_cloudfront_origins as cf_origins,
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

        subdomain = config.api.public_bucket.split(".")[0]
        domain = f"{subdomain}.{api_zone.zone_name}"

        # bucket
        site_bucket = s3.Bucket(
            self,
            id="Bucket",
            bucket_name=config.api.public_bucket,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        CfnOutput(self,
            id="BucketName",
            value=config.api.public_bucket,
        )

        # cloudfront
        distribution = self.setup_cloudfront(
            site_bucket=site_bucket,
            config=config,
            default_cert=default_cert,
            main_domain=domain,
        )

        r53.ARecord(
            self,
            id="AliasRecord",
            record_name=domain,
            target=r53.RecordTarget.from_alias(targets.CloudFrontTarget(distribution=distribution)),
            zone=api_zone,
        )

    def setup_cloudfront(
        self,
        config: ProjectSettings,
        default_cert: acm.Certificate,
        site_bucket: s3.Bucket,
        main_domain: str,
    ) -> cf.Distribution:

        # cfOAI
        cloudfront_OAI = cf.OriginAccessIdentity(
            self,
            'CloudfrontOAI',
            comment=f"OAI for {id}"
        )
        cfoai_principal = iam.CanonicalUserPrincipal(
            cloudfront_OAI.cloud_front_origin_access_identity_s3_canonical_user_id
        )

        # Grant access to cloudfront
        policy_stmt = iam.PolicyStatement(
            actions=['s3:GetObject'],
            resources=[site_bucket.arn_for_objects('*')],
            principals=[cfoai_principal]
        )
        site_bucket.add_to_resource_policy(policy_stmt)

        # CloudFront distribution
        domain_names = [main_domain]
        # allow the prod domains into the cloudfront distribution
        domain_names.append(config.api.public_bucket)

        behaviour_options = cf.BehaviorOptions(
            cache_policy=cf.CachePolicy.CACHING_DISABLED,
            origin=cf_origins.S3Origin(
                bucket=site_bucket, 
                origin_access_identity=cloudfront_OAI
            ),
            allowed_methods=cf.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        )

        distribution = cf.Distribution(
            self,
            id="Distribution",
            certificate=default_cert,
            price_class=cf.PriceClass.PRICE_CLASS_100,
            domain_names=domain_names,
            minimum_protocol_version=cf.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_behavior=behaviour_options
        )

        CfnOutput(self,
            id="DistributionDomains",
            value=", ".join(domain_names),
        )

        return distribution
