#!/bin/bash
# Pod-side backstop: terminate this pod after $1 seconds regardless of the devbox.
sleep "${1:-14400}"
curl -s -X POST https://api.runpod.io/graphql \
  -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" \
  -d "{\"query\":\"mutation { podTerminate(input:{podId:\\\"$RUNPOD_POD_ID\\\"}) }\"}"
