import os
import shutil
from typing import Optional

from aws_cdk import (
    BundlingOptions,
    ILocalBundling,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_iam as iam,
    Stack,
    Tags,
    Duration,
)
from constructs import Construct
import jsii


@jsii.implements(ILocalBundling)
class ADLocalBundling:

    def try_bundle(self, output_dir, options: BundlingOptions):
        local_env = options.environment

        bundle(
            local_env.get("base_dir"),
            local_env.get("local_base_dir"),
            local_env.get("local_lib"),
            output_dir,
        )
        return True


def bundle(base_dir, local_base_dir, local_lib, output_dir):
    os.system(
        f"python -m pip install -r {local_base_dir}/requirements.txt -t {output_dir}"
    )
    shutil.copytree(f"{local_base_dir}/src", output_dir, dirs_exist_ok=True)


class CdkUtilLambda:
    def __init__(
        self,
        default_runtime=_lambda.Runtime.PYTHON_3_13,
        default_log_retention=logs.RetentionDays.ONE_MONTH,
        default_env=None,
    ):
        if default_env is None:
            default_env = {}

        self.default_env = default_env
        self.default_runtime = default_runtime
        self.default_log_retention = default_log_retention

    def basic_lambda(
        self,
        stack: Stack,
        name: str,
        src_path: str,
        base_path: str,
        rel_src_path: str,
        timeout_sec: int,
        description: str,
        memory_size=128,
        retry_attempts=0,
        environment=None,
        lambda_runtime=None,
        log_retention=None,
        layers=None,
        reserved_concurrent_executions=None,
        dead_letter_queue=None,
        role: Optional[iam.IRole] = None,
    ) -> _lambda.Function:

        if environment is None:
            environment = {}

        environment.update(self.default_env)

        if lambda_runtime is None:
            lambda_runtime = self.default_runtime

        if log_retention is None:
            log_retention = self.default_log_retention

        if layers is None:
            layers = []

        return _lambda.Function(
            stack,
            name,
            code=_lambda.Code.from_asset(
                os.path.join(src_path, name),
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_13.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt -t /asset-output && cp -r src/. /asset-output",
                    ],
                    local=ADLocalBundling(),
                    environment={
                        "base_dir": base_path,
                        "local_base_dir": os.path.join(base_path, rel_src_path, name),
                    },
                ),
            ),
            handler=f"{name}.lambda_handler",
            runtime=lambda_runtime,
            description=description,
            log_retention=log_retention,
            timeout=Duration.seconds(timeout_sec),
            retry_attempts=retry_attempts,
            environment=environment,
            layers=layers,
            memory_size=memory_size,
            dead_letter_queue=dead_letter_queue,
            role=role,
        )


class CdkUtilStack(Stack):
    ENVIRONMENT_CONFIG_VAR = "config"

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        self.cdk_env = self.get_environment_specific_config(self.ENVIRONMENT_CONFIG_VAR)

        # Slick method of tagging, adding tags to thte top level of the stack will propagate to all child objects that support stacks
        Tags.of(self).add(key="application", value=self.cdk_env.get("project"))
        Tags.of(self).add(key="environment", value=self.cdk_env.get("environment"))

    def get_environment_specific_config(self, config_name):
        config = self.node.try_get_context(config_name)
        cdk_env = self.node.try_get_context(config)
        return cdk_env
