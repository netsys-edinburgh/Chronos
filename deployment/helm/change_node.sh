#!/bin/bash

# change_node.sh <num>
# This script changes the value of 'numberGNBNodes:' in values.yaml to <num>.
# Usage: ./change_node.sh 5

if [ $# -ne 1 ]; then
    echo "Usage: $0 <num>"
    exit 1
fi

NUM="$1"
YAML_FILE="values.yaml"

if [ ! -f "$YAML_FILE" ]; then
    echo "Error: $YAML_FILE not found in current directory."
    exit 2
fi

# Update numberGNBNodes in values.yaml
# -i'' works on both GNU and BSD/macOS sed
sed -i'' -E "s/^(numberGNBNodes:)[[:space:]]*[0-9]+/\1 $NUM/" "$YAML_FILE"

echo "numberGNBNodes set to $NUM in $YAML_FILE"
