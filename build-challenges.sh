#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
for file in $(find $SCRIPT_DIR/challenges -name docker-compose.yaml); do
    pushd $(dirname $file)
    docker-compose build $@
    popd
done
