from aws_cdk import Duration, Stack, aws_iam as iam
from constructs import Construct


class GithubAccessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        externalOidcProvider = iam.OpenIdConnectProvider(
            self,
            "GithubOIDCProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        self.github_access_role = iam.Role(
            self,
            "GithubAccessRole",
            assumed_by=iam.WebIdentityPrincipal(
                identity_provider=externalOidcProvider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": "repo:data-mermaid/mermaid-*"
                    },
                },
            ),
            max_session_duration=Duration.hours(3),
        )
