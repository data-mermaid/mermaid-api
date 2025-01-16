from aws_cdk import (
    CfnOutput,
    Stack,
    aws_certificatemanager as acm,
    aws_cloudfront as cf,
    aws_cloudfront_origins as cf_origins,
    aws_iam as iam,
    aws_s3 as s3,
)
from constructs import Construct
from settings.settings import ProjectSettings


class StaticSiteStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        default_cert: acm.Certificate,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # bucket
        self.site_bucket = s3.Bucket(
            self,
            id="Bucket",
            bucket_name=config.api.public_bucket,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        )

        CfnOutput(
            self,
            id="BucketName",
            value=config.api.public_bucket,
        )

        # Set up cloudfront

        # cfOAI
        cloudfront_OAI = cf.OriginAccessIdentity(self, "CloudfrontOAI", comment=f"OAI for {id}")
        cfoai_principal = iam.CanonicalUserPrincipal(
            cloudfront_OAI.cloud_front_origin_access_identity_s3_canonical_user_id
        )

        # Grant access to cloudfront
        policy_stmt = iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[self.site_bucket.arn_for_objects("*")],
            principals=[cfoai_principal],
        )
        self.site_bucket.add_to_resource_policy(policy_stmt)

        # CloudFront distribution
        domain_names = [self.site_bucket.bucket_name]

        behaviour_options = cf.BehaviorOptions(
            cache_policy=cf.CachePolicy.CACHING_DISABLED,
            origin=cf_origins.S3Origin(
                bucket=self.site_bucket, origin_access_identity=cloudfront_OAI
            ),
            allowed_methods=cf.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
            viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        )

        _ = cf.Distribution(
            self,
            id="Distribution",
            certificate=default_cert,
            price_class=cf.PriceClass.PRICE_CLASS_100,
            domain_names=domain_names,
            minimum_protocol_version=cf.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_behavior=behaviour_options,
        )
