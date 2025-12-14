#!/bin/bash

# MatchEng UI Startup Script

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting MatchEng UI...${NC}"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed or not in PATH${NC}"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source .venv/bin/activate

# Upgrade pip
echo -e "${GREEN}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install/update dependencies
echo -e "${GREEN}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Ensure data and outputs directories exist
mkdir -p data
mkdir -p outputs

# Start the Flask application
echo -e "${GREEN}Starting Flask application...${NC}"
echo -e "${YELLOW}Server will be available at: http://localhost:${PORT:-5000}${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

python3 app.py

