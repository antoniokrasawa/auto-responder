#!/bin/bash
docker rm -f auto-responder 2>/dev/null
docker run -d --name auto-responder --restart unless-stopped \
  --env-file /opt/bots/auto-responder/.env \
  -v /opt/bots/auto-responder/whitelist.json:/app/whitelist.json \
  -v /opt/bots/auto-responder/conversations.json:/app/conversations.json \
  -v /opt/bots/auto-responder/auto_responder_session.session:/app/auto_responder_session.session \
  -v /opt/bots/auto-responder/failed_leads.json:/app/failed_leads.json \
  auto-responder-img
