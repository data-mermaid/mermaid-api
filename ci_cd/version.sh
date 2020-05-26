#! /bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
VERSION=`git describe --tags --abbrev=0`
echo "VERSION: $VERSION"
rm -f $DIR/VERSION.txt
echo $VERSION >> $DIR/VERSION.txt
