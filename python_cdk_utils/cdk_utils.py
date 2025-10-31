"""AWS CDK utility library for common Python Lambda and Stack patterns.

This module provides reusable CDK constructs and helpers that simplify common
AWS infrastructure patterns, particularly for Python Lambda functions with
automatic bundling support and environment-aware stack configurations.

Classes:
    ADLocalBundling: Local bundling implementation for faster development cycles
    CdkUtilLambda: Helper for creating Lambda functions with standardized configs
    CdkUtilStack: Base stack class with environment configuration and auto-tagging
"""
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
    """Local bundling implementation for AWS Lambda Python dependencies.

    Implements CDK's ILocalBundling interface to enable local bundling of Lambda
    dependencies instead of using Docker. This significantly speeds up development
    iteration by avoiding Docker container startup overhead.

    The bundler installs Python dependencies from requirements.txt and copies
    source code to the Lambda asset output directory.
    """

    def try_bundle(self, output_dir, options: BundlingOptions):
        """Attempt to bundle Lambda dependencies locally.

        Called by CDK to perform local bundling. Extracts environment variables
        from bundling options and delegates to the bundle() function.

        Args:
            output_dir: Target directory where bundled assets should be written
            options: BundlingOptions containing environment variables with paths

        Returns:
            bool: Always returns True to indicate successful bundling
        """
        local_env = options.environment

        bundle(
            local_env.get("base_dir"),
            local_env.get("local_base_dir"),
            local_env.get("local_lib"),
            output_dir,
        )
        return True


def bundle(base_dir, local_base_dir, local_lib, output_dir):
    """Bundle Lambda dependencies and source code.

    Installs Python dependencies from requirements.txt and copies source code
    to the output directory for Lambda deployment.

    Args:
        base_dir: Base directory of the CDK project (currently unused)
        local_base_dir: Path to the Lambda function directory containing
            requirements.txt and src/
        local_lib: Path to optional local library to include (currently unused)
        output_dir: Target directory where bundled assets will be written
    """
    os.system(
        f"python -m pip install -r {local_base_dir}/requirements.txt -t {output_dir}"
    )
    shutil.copytree(f"{local_base_dir}/src", output_dir, dirs_exist_ok=True)


class CdkUtilLambda:
    """Helper class for creating Lambda functions with standardized configurations.

    Simplifies Lambda function creation by providing sensible defaults and
    automatic bundling of Python dependencies. Supports setting project-wide
    defaults that apply to all Lambda functions created with this instance.

    Attributes:
        default_env: Default environment variables applied to all Lambda functions
        default_runtime: Default Lambda runtime (defaults to Python 3.13)
        default_log_retention: Default CloudWatch log retention period
    """

    def __init__(
        self,
        default_runtime=_lambda.Runtime.PYTHON_3_13,
        default_log_retention=logs.RetentionDays.ONE_MONTH,
        default_env=None,
    ):
        """Initialize CdkUtilLambda with default configurations.

        Args:
            default_runtime: Default Lambda runtime for all functions
                (defaults to Python 3.13)
            default_log_retention: Default CloudWatch log retention
                (defaults to ONE_MONTH)
            default_env: Dictionary of default environment variables to apply
                to all Lambda functions (defaults to empty dict)
        """
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
        """Create a Lambda function with automatic dependency bundling.

        Creates a Lambda function with local bundling support for faster iteration.
        Automatically installs dependencies from requirements.txt and copies source
        code from src/ directory. Applies default configurations from the instance.

        Expected directory structure:
            {src_path}/{name}/
                requirements.txt
                src/
                    {name}.py  (must contain lambda_handler function)

        Args:
            stack: CDK Stack to add the Lambda function to
            name: Name of the Lambda function (used as construct ID and handler name)
            src_path: Path to directory containing Lambda function folders
            base_path: Base path of the CDK project
            rel_src_path: Relative path from base_path to src_path
            timeout_sec: Function timeout in seconds
            description: Description of the Lambda function
            memory_size: Memory allocation in MB (default: 128)
            retry_attempts: Number of retry attempts on failure (default: 0)
            environment: Dictionary of environment variables (merged with default_env)
            lambda_runtime: Lambda runtime (defaults to instance default)
            log_retention: CloudWatch log retention (defaults to instance default)
            layers: List of Lambda layers to attach (default: empty list)
            reserved_concurrent_executions: Reserved concurrent executions limit
                (default: None)
            dead_letter_queue: SQS queue for failed invocations (default: None)
            role: IAM role for the Lambda function (default: None, auto-created)

        Returns:
            _lambda.Function: The created Lambda function construct
        """
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
    """Base CDK Stack with environment configuration and automatic tagging.

    Extends aws_cdk.Stack to provide environment-specific configuration loading
    from CDK context and automatic resource tagging. Tags are automatically
    propagated to all child resources that support tagging.

    The stack expects a two-level context configuration:
    1. A "config" context variable pointing to the environment name
    2. An environment-specific context object with "project" and "environment" keys

    Example cdk.json context:
        {
            "context": {
                "config": "dev",
                "dev": {
                    "project": "my-app",
                    "environment": "development"
                }
            }
        }

    Attributes:
        ENVIRONMENT_CONFIG_VAR: Context variable name for environment lookup
        cdk_env: Dictionary containing environment-specific configuration
    """
    ENVIRONMENT_CONFIG_VAR = "config"

    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        """Initialize the stack with environment configuration and tags.

        Loads environment-specific configuration from CDK context and automatically
        applies "application" and "environment" tags to all resources in the stack.

        Args:
            scope: Parent construct
            construct_id: Unique identifier for this stack
            **kwargs: Additional keyword arguments passed to Stack constructor
        """
        super().__init__(scope, construct_id, **kwargs)

        self.cdk_env = self.get_environment_specific_config(self.ENVIRONMENT_CONFIG_VAR)

        # Tags added to the stack level propagate to all child resources that support tags
        Tags.of(self).add(key="application", value=self.cdk_env.get("project"))
        Tags.of(self).add(key="environment", value=self.cdk_env.get("environment"))

    def get_environment_specific_config(self, config_name):
        """Retrieve environment-specific configuration from CDK context.

        Performs a two-level lookup in CDK context:
        1. Looks up the value of config_name to get the environment name
        2. Looks up the environment name to get the configuration object

        Args:
            config_name: Name of the context variable containing the environment name
                (typically "config")

        Returns:
            dict: Environment-specific configuration dictionary
        """
        config = self.node.try_get_context(config_name)
        cdk_env = self.node.try_get_context(config)
        return cdk_env
