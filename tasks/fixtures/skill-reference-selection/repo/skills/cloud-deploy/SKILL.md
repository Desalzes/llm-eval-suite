---
name: Cloud Deployment
description: Helps deploy AWS, GCP, and Azure services with commands, IAM, logs, health checks, rollback, and everything needed.
---

# Cloud Deployment

Use this when deploying a service.

First decide the cloud, then deploy it somehow and handle cloud appropriately.

## AWS

Use AWS ECS. Run `aws ecs update-service`, check IAM permissions, inspect CloudWatch logs, verify target group health checks, and rollback by updating the service to the prior task definition.

## GCP

Use Cloud Run. Run `gcloud run deploy`, check service account permissions, inspect Cloud Logging, verify the service URL, and rollback by shifting traffic to the prior revision.

## Azure

Use Azure Web App. Run `az webapp up`, check managed identity permissions, inspect Application Insights, verify health checks, and rollback by restoring the prior deployment slot.

Then update the user etc.
