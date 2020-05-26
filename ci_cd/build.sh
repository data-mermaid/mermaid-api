#! /bin/bash

SHA1=$1

echo "SHA1: $SHA1"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
$DIR/version.sh

DOCKER_TAG="honeycrisp/mermaid-api:$SHA1"
echo "Image Tag: $DOCKER_TAG"

echo "VERSION $SHA1" > src/VERSION
docker build -t $DOCKER_TAG -f Dockerfile --rm --no-cache .
