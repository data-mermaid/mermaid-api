#!/bin/sh
set -e

CDK_CLI_VERSION=2.1145.0
CDK_LIB_VERSION=2.273.0
CDK_NAG_VERSION=3.0.2

echo "Installing AWS CDK CLI"
npm install -g aws-cdk@$CDK_CLI_VERSION

echo "Installing AWS CDK Python Libs"
pip install aws-cdk-lib==$CDK_LIB_VERSION

echo "Installing cdk-nag"
pip install cdk-nag==$CDK_NAG_VERSION

