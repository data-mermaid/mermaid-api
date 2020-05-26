#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
COMMIT=`git log --format="%H" -n 1`
echo "Commit id: $COMMIT"
VERSION=`git describe --contains "$COMMIT" || git rev-parse --abbrev-ref HEAD`
echo "VERSION: $VERSION"
rm -f $DIR/VERSION.txt
echo $VERSION >> $DIR/VERSION.txt
