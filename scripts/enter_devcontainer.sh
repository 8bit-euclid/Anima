#!/bin/bash

# The container name is specified in devcontainer.json after the --name flag in runArgs
DEVCONT_PATH="$(dirname "$0")/../.devcontainer/devcontainer.json"
DEVCONT_NAME=$(jq -r '.runArgs | (index("--name") + 1) as $i | .[$i]' "$DEVCONT_PATH")

# Check if devcontainer name was found
if [ -z "$DEVCONT_NAME" ]; then
  echo "No devcontainer name found in '$DEVCONT_PATH'."
  echo "Please check your devcontainer.json configuration."
  exit 1
fi

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${DEVCONT_NAME}$"; then
  echo "Devcontainer '$DEVCONT_NAME' is not running."
  echo "Please start the devcontainer first."
  exit 1
fi

echo "Entering devcontainer '$DEVCONT_NAME'..."
docker exec -it "$DEVCONT_NAME" bash
