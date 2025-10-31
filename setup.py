import setuptools
from setuptools import find_packages
from pathlib import Path


setuptools.setup(
    name="python_cdk_utils",
    version="0.1.1",
    author="fn_ln",
    description="Shared library for python cdk projects",
    packages=find_packages(),
    install_requires=[
        "jsii>=1.0.0",
        "aws-cdk-lib>=2.0.0",
        "constructs>=10.0.0",
    ],
    python_requires=">=3.7"
)
