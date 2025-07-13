#!/bin/bash
# status.sh
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ ! -f "PROJECT_CONTEXT.md" ]; then
    echo -e "${RED}Error: PROJECT_CONTEXT.md not found. Run this from the project root.${NC}"
    exit 1
fi

git pull origin main > /dev/null 2>&1

echo -e "${CYAN}--- Project Status Report ---${NC}"
echo -e "\n${GREEN}✅ Completed Features:${NC}"
grep --color=never -E "^\s*-\s*\[x\]" PROJECT_CONTEXT.md | sed 's/- \[x\]/  -/'

echo -e "\n${YELLOW}📋 Planned Features (Not Started):${NC}"
grep --color=never -E "^\s*-\s*\[ \]" PROJECT_CONTEXT.md | sed 's/- \[ \]/  -/'

echo -e "\n${CYAN}🚧 Features In Progress (Active Branches):${NC}"
git branch --list 'feature/*' | sed 's/.*feature\//  - /'

echo -e "\n${CYAN}---------------------------${NC}"
