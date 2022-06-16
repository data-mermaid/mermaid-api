from aws_cdk import Stack
from constructs import Construct

from cdk.settings import ProjectSettings


class MainStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        config: ProjectSettings,
        **kwargs,
    ) -> None:
        super().__init__(scope, id, **kwargs)

        # Put CDK code here
