#!/bin/sh
set -e

CDK_VERSION=2.29.1

echo "Installing AWS CDK CLI"
npm install -g aws-cdk@$CDK_VERSION

echo "Installing AWS CDK Python Libs"
pip install aws-cdk-lib==$CDK_VERSION

