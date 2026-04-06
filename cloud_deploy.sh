#!/bin/bash
# Cloud Deployment Script for Ultimate AI Agent
# Runs on Ubuntu 20.04/22.04 LTS

echo "🚀 Starting Ultimate Agent Cloud Deployment..."

# 1. Update System
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git fail2ban

# 2. Install Docker
if ! command -v docker &> /dev/null
then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo "Docker installed."
else
    echo "Docker already installed."
fi

# 3. Install Docker Compose
if ! command -v docker-compose &> /dev/null
then
    echo "Installing Docker Compose..."
    sudo apt-get install -y docker-compose-plugin
else
    echo "Docker Compose already installed."
fi

# 4. Setup Firewall (UFW)
echo "Configuring Firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8001/tcp
sudo ufw --force enable

# 5. Launch Agent
echo "Building and Launching Agent Container..."
# Assuming we are in the repo directory
sudo docker compose up -d --build

echo "✅ Deployment Complete! The Agent is now alive."
echo "Monitor logs with: sudo docker compose logs -f"
