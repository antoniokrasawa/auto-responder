#!/bin/bash
# Deploy auto-responder to Hetzner server
# Usage: bash deploy.sh

set -e
SERVER="root@77.42.69.208"
REMOTE_DIR="/opt/bots/auto-responder"

echo "=== 1. Committing changes ==="
git add -A
if git diff --cached --quiet; then
    echo "No changes to commit, pushing existing..."
else
    read -p "Commit message (or Enter for default): " MSG
    MSG="${MSG:-update auto-responder}"
    git commit -m "$MSG"
fi

echo "=== 2. Pushing to GitHub ==="
git push

echo "=== 3. Updating server ==="
ssh $SERVER "cd $REMOTE_DIR && git pull && docker build -t auto-responder-img . && bash /tmp/r.sh"

echo "=== 4. Checking logs ==="
sleep 2
ssh $SERVER "docker logs auto-responder --tail 15"

echo ""
echo "=== Done! ==="
