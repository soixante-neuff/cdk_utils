# Python CDK Utils

A shared utility library for AWS CDK Python projects, providing reusable constructs and helpers for common Lambda and Stack patterns.

## Features

- **CdkUtilLambda**: Simplified Lambda function creation with bundling support
- **CdkUtilStack**: Base stack class with environment configuration and automatic tagging
- **ADLocalBundling**: Local bundling support for faster development iterations

## Installation

```bash
pip install python-cdk-utils
```

## Usage

### Basic Lambda Function

```python
from cdk_utils import CdkUtilLambda
from aws_cdk import Stack
from constructs import Construct

class MyStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        lambda_util = CdkUtilLambda()

        my_function = lambda_util.basic_lambda(
            stack=self,
            name="my-function",
            src_path="./lambdas",
            base_path=".",
            rel_src_path="lambdas",
            timeout_sec=30,
            description="My Lambda function",
            memory_size=256
        )
```

### Using CdkUtilStack with Environment Configuration

```python
from cdk_utils import CdkUtilStack
from constructs import Construct

class MyStack(CdkUtilStack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Access environment-specific configuration
        project_name = self.cdk_env.get("project")
        environment = self.cdk_env.get("environment")
```

In your `cdk.json`:

```json
{
  "context": {
    "config": "dev",
    "dev": {
      "project": "my-project",
      "environment": "development"
    }
  }
}
```

## Requirements

- Python 3.7+
- aws-cdk-lib >= 2.0.0
- jsii

## License

MIT
