#!/bin/bash
# filepath: /workspaces/Anima/scripts/enter_devcontainer.sh

# Find container by project label
CONTAINER_ID=$(docker ps --filter "label=project=anima" --filter "status=running" --format "{{.ID}}" | head -n1)

if [ -n "$CONTAINER_ID" ]; then
    docker exec -it "$CONTAINER_ID" bash
else
    echo "No running devcontainer found for project 'anima'."
    exit 1
fi