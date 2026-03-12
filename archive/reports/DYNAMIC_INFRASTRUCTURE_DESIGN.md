# Dynamic Infrastructure Management Design

## Overview

This document outlines the design for enabling dynamic provisioning and destruction of vector store backends (Qdrant, LanceDB, OpenSearch) directly from the Videolake UI. This moves the platform towards a "fully modular system" where the UI drives the infrastructure state via Terraform.

## Goals

1.  **Dynamic Provisioning**: Allow users to spin up/down backends on demand.
2.  **State Awareness**: UI must reflect the actual state of infrastructure (deployed vs. not deployed).
3.  **Modularity**: Each backend should be independently toggleable.
4.  **User Feedback**: Real-time logs and status updates during long-running operations.

## Architecture

### High-Level Flow

1.  **UI Request**: User clicks "Deploy Qdrant" in the UI.
2.  **API Endpoint**: Frontend calls `POST /api/infrastructure/deploy` with `{"vector_stores": ["qdrant"]}`.
3.  **Background Task**: FastAPI spawns a background task to handle the Terraform operation.
4.  **Terraform Execution**: The backend service executes `terraform apply -target=module.qdrant -auto-approve`.
5.  **Log Streaming**: Terraform output is captured and streamed to the UI via Server-Sent Events (SSE).
6.  **State Update**: Upon completion, the backend syncs the new Terraform state to the resource registry.
7.  **UI Update**: The UI receives the "completed" event and refreshes the resource list.

### Components

#### 1. Terraform Infrastructure Manager (`src/services/terraform_infrastructure_manager.py`)

This service wraps the `terraform` CLI commands.

*   **Responsibilities**:
    *   Execute `terraform apply`, `terraform destroy`, `terraform init`, `terraform plan`.
    *   Manage Terraform state parsing (`terraform.tfstate`).
    *   Estimate costs for deployed resources.
    *   Sync state to the application's resource registry.

*   **Key Methods**:
    *   `deploy_vector_store(store_name)`: Deploys a specific module.
    *   `destroy_vector_store(store_name)`: Destroys a specific module.
    *   `get_deployment_status()`: Returns the current state of all backends.

#### 2. Terraform Operation Tracker (`src/services/terraform_operation_tracker.py`)

This service manages the state of active Terraform operations and their logs.

*   **Responsibilities**:
    *   Track running operations (deploy/destroy).
    *   Store logs in memory for real-time streaming.
    *   Provide an SSE generator for log consumption.

#### 3. API Router (`src/api/routers/infrastructure.py`)

Exposes the functionality to the frontend.

*   **Endpoints**:
    *   `POST /deploy`: Triggers deployment.
    *   `DELETE /destroy`: Triggers destruction.
    *   `GET /status`: Returns current infrastructure status.
    *   `GET /logs/{operation_id}`: SSE endpoint for log streaming.

## Security Considerations

*   **Permissions**: The ECS task running the backend needs IAM permissions to create/destroy the relevant AWS resources (EC2, ECS, OpenSearch, IAM roles, etc.).
*   **State Locking**: Terraform state is stored in S3 with DynamoDB locking to prevent concurrent modifications.
*   **Input Validation**: The API strictly validates the `vector_store` parameter to prevent arbitrary module execution.

## Implementation Details

### Terraform Command Construction

To deploy a specific module without affecting others, we use the `-target` flag:

```bash
terraform apply -target=module.qdrant -var="deploy_qdrant=true" -auto-approve
```

To destroy:

```bash
terraform destroy -target=module.qdrant -auto-approve
```

### Async Operations

Since Terraform operations can take minutes, all state-changing API endpoints are asynchronous:

1.  The API returns an `operation_id` immediately.
2.  The actual work happens in a `BackgroundTasks`.
3.  The frontend subscribes to `/api/infrastructure/logs/{operation_id}` to receive updates.

### State Synchronization

The `TerraformInfrastructureManager` parses the `terraform.tfstate` file directly to determine what is deployed. This ensures the UI always reflects the *actual* infrastructure state, not just a database record.

## Future Improvements

*   **Fine-grained Cost Tracking**: Integrate with AWS Cost Explorer for actual vs. estimated costs.
*   **Scheduled Destruction**: Auto-destroy expensive resources (like OpenSearch) after a set period of inactivity.
*   **Dry Run**: Add a "Plan" button to show users what changes will happen before applying.