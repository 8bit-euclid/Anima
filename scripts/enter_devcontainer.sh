#!/bin/bash

# Extract the container name from the --name runtime argument in devcontainer.json
CONTAINER_NAME=$(jq -r '.runArgs | (index("--name") + 1) as $i | .[$i]' "$(dirname "$0")/../.devcontainer/devcontainer.json")

if [ -n "$CONTAINER_NAME" ]; then
  docker exec -it "$CONTAINER_NAME" bash
else
  echo "No devcontainer found."
fi