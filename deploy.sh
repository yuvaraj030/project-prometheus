#!/bin/bash
# ============================================
# Ultimate AI Agent - Deployment Script
# Supports: Railway, Render, Fly.io, or any Docker host
# ============================================

set -e

APP_NAME="ultimate-ai-agent"
SERVICE_NAME="agentic-api"

echo "🚀 Deploying $APP_NAME to Production..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running."
  exit 1
fi

# Build image
echo "📦 Building Docker image..."
docker build -t "$APP_NAME:latest" .

# Tag for registry (adjust for your cloud provider)
# e.g., for AWS ECR: docker tag $APP_NAME:latest account-id.dkr.ecr.region.amazonaws.com/$APP_NAME:latest
# e.g., for Railway: railway up
# e.g., for Render: auto-deployed from git

echo "✅ Image built successfully."

# Run locally or push
read -p "Push to cloud? [y/N] " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
  echo "Please select provider:"
  echo "1) Railway"
  echo "2) Render (via git push)"
  echo "3) AWS ECR"
  read -p "Choice: " provider

  case $provider in
    1)
      if command -v railway &> /dev/null; then
        echo "🚄 Deploying to Railway..."
        railway up
      else
        echo "Please install Railway CLI first."
      fi
      ;;
    2)
      echo "🌐 Pushing to Git for Render auto-deploy..."
      git add .
      git commit -m "Deploy: Update agent code"
      git push origin main
      ;;
    3)
      echo "☁️ Pushing to AWS ECR..."
      # Add AWS CLI commands here
      echo "Requires AWS setup."
      ;;
    *)
      echo "Invalid choice."
      ;;
  esac
else
  echo "ℹ️  Run locally with: docker-compose up --build"
fi
