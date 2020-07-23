#! /bin/bash

ENV=$1
SHA1=$2
APPLICATION=$3

if [[ $ENV != "mermaid-dev-api2" ]] && [[ $ENV != "mermaid-prod-api2" ]]; then
    echo "Valid environments are 'mermaid-dev-api2' or 'mermaid-prod-api2'"
    exit
fi

# Create new Elastic Beanstalk version
EB_BUCKET=mermaid-circleci-deployments2
ARCHIVE_NAME=$ENV-archive.zip
VERSION="$SHA1"

# Substitute ENV name into Dockerrun.aws.json file.
sed "s/<TAG>/$ENV/" < ci_cd/Dockerrun.aws.json.template > Dockerrun.aws.json
cat Dockerrun.aws.json

# Create a zip with run file and .ebextensions
zip $ARCHIVE_NAME Dockerrun.aws.json
zip $ARCHIVE_NAME -r .ebextensions

echo "Copy archive to S3"
aws s3 cp $ARCHIVE_NAME s3://$EB_BUCKET/$ARCHIVE_NAME

echo "Create application version: $VERSION"
aws elasticbeanstalk create-application-version \
  --application-name $APPLICATION \
  --version-label "$VERSION" \
  --source-bundle S3Bucket=$EB_BUCKET,S3Key=$ARCHIVE_NAME

echo "Update Environment: $ENV"
# Update Elastic Beanstalk environment to new version
aws elasticbeanstalk update-environment \
  --environment-name $ENV \
  --version-label "$VERSION"
