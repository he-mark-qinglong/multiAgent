#!/bin/bash
set -e

NAMESPACE="multiagent"
DEPLOY_DIR="$(dirname "$0")/../k8s"

echo "Deploying multiagent to Kubernetes..."

# Apply namespace
kubectl apply -f "$DEPLOY_DIR/namespace.yaml"

# Apply secrets first (replace with actual values via sealed-secrets or external-secrets in prod)
echo "Applying secrets..."
envsubst < "$DEPLOY_DIR/secrets.yaml" | kubectl apply -f -

# Apply configmap
kubectl apply -f "$DEPLOY_DIR/configmap.yaml"

# Apply deployment
kubectl apply -f "$DEPLOY_DIR/deployment.yaml"

# Apply service
kubectl apply -f "$DEPLOY_DIR/service.yaml"

# Apply ingress
kubectl apply -f "$DEPLOY_DIR/ingress.yaml"

# Wait for rollout
echo "Waiting for rollout..."
kubectl rollout status deployment/multiagent -n "$NAMESPACE"

echo "Deployment complete!"
