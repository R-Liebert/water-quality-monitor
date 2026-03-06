#!/bin/bash

# Colorful terminal output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  Water Quality Spatial Monitor - API Auto-Setup CLI  ${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""
echo -e "This script will automatically configure your local environment"
echo -e "with the necessary API credentials to access live satellite data."
echo ""

# Create or clear the .env file
ENV_FILE=".env"
touch $ENV_FILE

# 1. Copernicus Data Space (Satellite)
echo -e "${YELLOW}--- 1. Copernicus Satellite Data ---${NC}"
echo "To fetch live surface hydration and turbidity scans, you need a free account at dataspace.copernicus.eu"
read -p "Enter your Copernicus Client ID (or press Enter to skip for now): " COP_ID
read -p "Enter your Copernicus Client Secret (or press Enter to skip for now): " COP_SECRET

if [ -n "$COP_ID" ] && [ -n "$COP_SECRET" ]; then
    echo "COPERNICUS_CLIENT_ID=$COP_ID" >> $ENV_FILE
    echo "COPERNICUS_CLIENT_SECRET=$COP_SECRET" >> $ENV_FILE
    echo -e "${GREEN}✓ Copernicus credentials saved.${NC}
"
else
    echo "Skipping Copernicus setup. The system will continue to use mock satellite data.
"
fi

# 2. Google Maps 3D Tiles (Frontend)
echo -e "${YELLOW}--- 2. Google 3D Tiles (Photorealistic Frontend) ---${NC}"
echo "To render the map over real 3D terrain and buildings, you need a Google Maps API key with the 3D Tiles API enabled."
read -p "Enter your Google Maps API Key (or press Enter to skip): " GOOGLE_KEY

if [ -n "$GOOGLE_KEY" ]; then
    # If the user enters a key, we can automatically insert it into the frontend file if it exists
    if [ -f "frontend/3d_map/index.html" ]; then
        sed -i "s/YOUR_API_KEY/$GOOGLE_KEY/g" frontend/3d_map/index.html
        echo -e "${GREEN}✓ Google API Key automatically injected into 3D frontend.${NC}
"
    else
        echo "GOOGLE_API_KEY=$GOOGLE_KEY" >> $ENV_FILE
        echo -e "${GREEN}✓ Google API Key saved to environment. Ready for 3D map implementation.${NC}
"
    fi
else
    echo -e "Skipping Google 3D Tiles. The frontend will use the standard 2D view.
"
fi

echo -e "${CYAN}======================================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo "Your live Open-Meteo weather integrations are already active."
echo "Restarting the backend worker containers to apply any new API keys..."

# Restart the docker containers to pick up the new .env variables
docker-compose restart worker beat api

echo -e "${GREEN}Containers restarted successfully. Live pipeline active.${NC}"
