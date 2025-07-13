#!/bin/bash
# new-feature.sh
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ -z "$1" ]; then
  echo -e "${YELLOW}Usage: ./new-feature.sh <feature-name-in-kebab-case>${NC}"
  exit 1
fi

FEATURE_NAME=$1
BRANCH_NAME="feature/$FEATURE_NAME"

echo -e "${GREEN}🚀 Creating new feature environment for: $FEATURE_NAME...${NC}"
git checkout main
git pull
git checkout -b $BRANCH_NAME

mkdir -p src/features/$FEATURE_NAME
touch src/features/$FEATURE_NAME/$FEATURE_NAME.controller.js
touch src/features/$FEATURE_NAME/$FEATURE_NAME.service.js
touch src/features/$FEATURE_NAME/$FEATURE_NAME.test.js

SAFE_FEATURE_NAME=$(printf '%s\n' "$FEATURE_NAME" | sed 's/[&/\\^$*.[()]/\\&/g')
CONTEXT=$(grep --color=never -E "^\s*-\s*\[ \]\s*.*${SAFE_FEATURE_NAME}.*" PROJECT_CONTEXT.md)

if [ -n "$CONTEXT" ]; then
  if command -v pbcopy >/dev/null 2>&1; then
    echo -e "$CONTEXT" | pbcopy
    echo -e "${GREEN}✅ Context for '$FEATURE_NAME' extracted and COPIED TO CLIPBOARD.${NC}"
  elif command -v xclip >/dev/null 2>&1; then
    echo -e "$CONTEXT" | xclip -selection clipboard
    echo -e "${GREEN}✅ Context for '$FEATURE_NAME' extracted and COPIED TO CLIPBOARD.${NC}"
  else
    echo -e "${YELLOW}Clipboard utility not found. Copy context manually.${NC}"
  fi
fi

echo -e "${GREEN}✅ Branch '$BRANCH_NAME' created. You can start coding now!${NC}"
