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

WORKDIR=$(pwd)
DEPLOY_DIR="/tmp/deploy-$SHA1"
rm -f -R DEPLOY_DIR || true
mkdir $DEPLOY_DIR
cp -R ".platform" "$DEPLOY_DIR/"

# Substitute ENV name into Dockerrun.aws.json file.
sed "s/<TAG>/$ENV/" <ci_cd/Dockerrun.aws.json.template >"$DEPLOY_DIR/Dockerrun.aws.json"
cat "$DEPLOY_DIR/Dockerrun.aws.json"

cd $DEPLOY_DIR
zip -r $WORKDIR/$ARCHIVE_NAME ./
cd $WORKDIR
unzip -l $WORKDIR/$ARCHIVE_NAME

echo "Copy archive to S3"
aws s3 cp $ARCHIVE_NAME s3://$EB_BUCKET/$ARCHIVE_NAME
rm -f -R DEPLOY_DIR || true

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
