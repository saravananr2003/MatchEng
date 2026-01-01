#!/bin/bash

# Matching Engine UI Startup Script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting Matching Engine Configuration UI...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed${NC}"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

echo -e "${GREEN}Installing dependencies...${NC}"
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

mkdir -p config data outputs templates static

echo -e "${GREEN}Starting Flask application...${NC}"
echo -e "${YELLOW}Server: http://localhost:${PORT:-5000}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python3 app.py

