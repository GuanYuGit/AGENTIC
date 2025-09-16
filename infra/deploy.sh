#!/bin/bash

# AWS ECS Deployment Script
set -e

PROJECT_NAME="agentic"
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "🚀 Deploying $PROJECT_NAME to AWS ECS..."

# 1. Build and push Docker image
echo "📦 Building Docker image..."
docker build -f Dockerfile.api -t $PROJECT_NAME-api .

echo "🏷️ Tagging image for ECR..."
docker tag $PROJECT_NAME-api:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-api:latest

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "⬆️ Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$PROJECT_NAME-api:latest

# 2. Deploy infrastructure
echo "🏗️ Deploying infrastructure with Terraform..."
cd infra
terraform init
terraform apply -auto-approve

echo "✅ Deployment complete!"
echo "🌐 API URL: $(terraform output -raw api_url)"
echo "📊 ECS Console: https://console.aws.amazon.com/ecs/home?region=$AWS_REGION#/clusters"
