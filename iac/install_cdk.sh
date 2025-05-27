#!/bin/sh
set -e

CDK_CLI_VERSION=2.1016.0
CDK_LIB_VERSION=2.196.1

echo "Installing AWS CDK CLI"
npm install -g aws-cdk@$CDK_CLI_VERSION

echo "Installing AWS CDK Python Libs"
pip install aws-cdk-lib==$CDK_LIB_VERSION

