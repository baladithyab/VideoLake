# Terraform ECS Backends Infrastructure Analysis

## Executive Summary

This analysis examines the existing Terraform infrastructure for Videolake's 7 backend configurations. The platform demonstrates a **hybrid maturity state** with some backends fully implemented while critical gaps exist for production-grade ECS deployments.

**Key Findings:**
- ✅ **3 of 7 backends** have complete Terraform modules
- ⚠️ **2 of 7 backends** have partial implementations with significant gaps
- ❌ **2 of 7 backends** lack proper ECS architecture (FSx Lustre support)
- 🔧 **Critical Missing Components**: Service Discovery, Load Balancers, VPC design, proper EC2 launch type for EBS

**Deployment Status:**
- **Production-Ready**: AWS S3Vector (Direct) ✅
- **ECS-Ready**: Qdrant on ECS + EFS ✅, LanceDB on ECS + S3 ✅
- **Needs Work**: LanceDB + EFS, Qdrant + EBS, OpenSearch + S3Vector
- **Missing**: LanceDB + FSx, Qdrant + FSx

---

## 1. Module Inventory & Status

### Current Terraform Module Structure

```
terraform/
├── main.tf                      # Root orchestration
├── variables.tf                 # Deployment flags and config
├── outputs.tf                   # Infrastructure outputs
└── modules/
    ├── s3_data_buckets/        # ✅ COMPLETE - Shared storage
    ├── s3vector/               # ✅ COMPLETE - Direct API bucket
    ├── opensearch/             # ⚠️ PARTIAL - Missing outputs
    ├── lancedb/                # ❌ DEPRECATED - Storage only (no ECS)
    ├── lancedb_ecs/            # ⚠️ PARTIAL - Missing outputs, FSx, EBS
    ├── qdrant/                 # ❌ DEPRECATED - EC2-based (not ECS)
    └── qdrant_ecs/             # ⚠️ PARTIAL - Missing outputs, EBS support
```

### Module Maturity Assessment

| Module | Status | Lines of Code | Resources | Outputs | Tests | Maturity |
|--------|--------|--------------|-----------|---------|-------|----------|
| `s3_data_buckets` | ✅ Complete | 156 | 6 | 3 | ❌ | **Production** |
| `s3vector` | ✅ Complete | 264 | 5 | 8 | ❌ | **Production** |
| `opensearch` | ⚠️ Partial | 160 | 6 | 0 | ❌ | **Beta** |
| `lancedb_ecs` | ⚠️ Partial | 306 | 15 | 0 | ❌ | **Alpha** |
| `qdrant_ecs` | ⚠️ Partial | 236 | 10 | 0 | ❌ | **Alpha** |
| `lancedb` | ❌ Deprecated | 108 | 8 | 0 | ❌ | **Deprecated** |
| `qdrant` | ❌ Deprecated | 230 | 10 | 3 | ❌ | **Deprecated** |

---

## 2. Backend Configuration Analysis

### Backend #1: AWS S3Vector (Direct) ✅

**Status**: **PRODUCTION-READY**

**Architecture**: Direct API calls to AWS S3Vector service (no ECS required)

**Existing Infrastructure**:
```terraform
Module: terraform/modules/s3vector/
- Uses AWS CLI via null_resource (preview service, no Terraform provider)
- Creates vector bucket via: aws s3vectors create-vector-bucket
- Creates default index with configurable dimension/metric
- IAM policy for S3Vector operations
- Proper destroy provisioner for cleanup
```

**Strengths**:
- ✅ Complete implementation with proper lifecycle management
- ✅ Extensive documentation in code
- ✅ Graceful handling of preview service limitations
- ✅ Proper IAM policies
- ✅ 8 outputs for integration

**Gaps**: None - this is the baseline and is production-ready

**Recommendation**: ✅ **No changes needed** - Reference implementation for other backends

---

### Backend #2: OpenSearch + S3Vector ⚠️

**Status**: **PARTIAL - Missing Integration Components**

**Architecture**: AWS OpenSearch Service with S3Vector storage engine

**Existing Infrastructure**:
```terraform
Module: terraform/modules/opensearch/
- OpenSearch domain (OR1 instance types for S3Vector)
- S3Vector engine enablement via AWS CLI
- EBS storage (100GB default)
- Fine-grained access control
- Encryption at rest and in transit
- CloudWatch logging
```

**Strengths**:
- ✅ OR1 instance type configuration (required for S3Vector)
- ✅ S3Vector engine activation via null_resource
- ✅ Security (encryption, HTTPS, TLS)
- ✅ Service-linked role creation

**Critical Gaps**:
- ❌ **No outputs.tf** - Cannot integrate with application layer
- ❌ Missing: Domain endpoint, ARN, dashboard URL
- ❌ Missing: VPC configuration (uses implicit default VPC)
- ❌ Missing: Access policies for application access
- ❌ No: S3Vector bucket integration (separate resources)

**Recommendation**: 🔧 **HIGH PRIORITY - Add outputs and access policies**

---

### Backend #3: LanceDB on ECS + S3 ⚠️

**Status**: **PARTIAL - Missing Service Discovery and Outputs**

**Architecture**: ECS Fargate tasks running LanceDB API wrapper with S3 backend

**Existing Infrastructure**:
```terraform
Module: terraform/modules/lancedb_ecs/
- ECS Cluster (separate per deployment)
- ECS Task Definition (Fargate, 2 vCPU, 8GB RAM)
- ECS Service (desired_count = 1)
- S3 bucket (when backend_type = "s3")
- IAM roles (execution + task roles with S3 access)
- Security groups (port 8000)
- CloudWatch logging
```

**Strengths**:
- ✅ Complete S3 backend implementation
- ✅ Proper IAM policies for S3 access
- ✅ Container Insights enabled
- ✅ Public IP assignment for testing

**Critical Gaps**:
- ❌ **No outputs.tf** - Cannot discover service endpoint
- ❌ Missing: Service Discovery (Cloud Map) for DNS-based routing
- ❌ Missing: Application Load Balancer for stable endpoint
- ❌ Missing: Health checks and autoscaling
- ⚠️ Custom image required: `lancedb/lancedb-api:latest` (needs documentation)
- ⚠️ Hardcoded port 8000 (should be variable)

**Docker Image Gap**:
```yaml
# MISSING: docker/lancedb-api/Dockerfile
# Need: FastAPI wrapper around LanceDB Python library
# Required endpoints:
#   - POST /collections/{name}/add
#   - POST /collections/{name}/search
#   - GET /health
```

**Recommendation**: 🔧 **HIGH PRIORITY - Add outputs, ALB, and Docker image**

---

### Backend #4: LanceDB on ECS + EFS/FSx ⚠️

**Status**: **PARTIAL - EFS works, FSx Lustre missing**

**Architecture**: ECS Fargate with shared filesystem (EFS or FSx Lustre)

**Existing Infrastructure** (EFS):
```terraform
Module: terraform/modules/lancedb_ecs/ (backend_type = "efs")
- EFS file system (generalPurpose performance mode)
- EFS mount target (single subnet)
- EFS security group (NFS port 2049)
- ECS task with EFS volume mount to /mnt/lancedb
- Same ECS infrastructure as S3 backend
```

**Strengths**:
- ✅ EFS creation and mounting
- ✅ Transit encryption enabled
- ✅ Security group properly configured

**Critical Gaps**:
- ❌ **No FSx Lustre support** (required for high-performance option)
- ❌ Single mount target (should be multi-AZ for HA)
- ❌ No EFS performance mode configuration (bursting only)
- ❌ Missing: Provisioned throughput options
- ❌ Same output gaps as S3 backend

**FSx Lustre Requirements** (NOT IMPLEMENTED):
```terraform
# MISSING:
resource "aws_fsx_lustre_file_system" "lancedb" {
  storage_capacity = 1200  # Min size
  subnet_ids       = [subnet.id]
  deployment_type  = "PERSISTENT_1"
  per_unit_storage_throughput = 200
  
  # S3 integration for data repository
  import_path = "s3://${bucket}/lancedb-data/"
  export_path = "s3://${bucket}/lancedb-data/"
}
```

**Recommendation**: 🔧 **MEDIUM PRIORITY - Add FSx Lustre, multi-AZ EFS**

---

### Backend #5: LanceDB on ECS + EBS ❌

**Status**: **BROKEN ARCHITECTURE - Cannot work as implemented**

**Current (Incorrect) Implementation**:
```terraform
Module: terraform/modules/lancedb_ecs/ (backend_type = "ebs")
# PROBLEM: Creates EFS with maxIO performance mode
# This is NOT EBS! It's EFS pretending to be EBS
```

**The Fundamental Problem**:
```
ECS Fargate + EBS = IMPOSSIBLE ❌

Fargate tasks:
- Run on AWS-managed infrastructure
- Cannot attach EBS volumes (no EC2 instance to attach to)
- Only support EFS volume mounts

EBS requires:
- EC2 launch type (not Fargate)
- Instance placement in specific AZ
- Volume attachment to EC2 instance
- Docker volume driver for ECS
```

**What Actually Needs To Exist**:
```terraform
# NEW MODULE REQUIRED: terraform/modules/lancedb_ecs_ec2/

resource "aws_ecs_cluster" "lancedb" {
  # Standard ECS cluster
}

resource "aws_launch_template" "lancedb" {
  # EC2 launch template with EBS volume
  block_device_mappings {
    device_name = "/dev/xvdb"
    ebs {
      volume_size = 100
      volume_type = "gp3"
      iops        = 3000
    }
  }
}

resource "aws_ecs_capacity_provider" "lancedb" {
  name = "lancedb-ec2"
  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.lancedb.arn
  }
}

resource "aws_ecs_service" "lancedb" {
  launch_type = "EC2"  # NOT Fargate!
  # EBS mount via Docker volume
}
```

**Recommendation**: 🔧 **HIGH PRIORITY - Create separate EC2-based module**

---

### Backend #6: Qdrant on ECS + EFS/FSx ⚠️

**Status**: **PARTIAL - EFS works, FSx missing, outputs missing**

**Architecture**: ECS Fargate running Qdrant with EFS persistence

**Existing Infrastructure**:
```terraform
Module: terraform/modules/qdrant_ecs/
- ECS Cluster (Container Insights enabled)
- EFS file system (generalPurpose, bursting)
- EFS mount target with security group
- ECS Task Definition (4 vCPU, 16GB RAM, official Qdrant image)
- ECS Service (Fargate, desired_count = 1)
- Ports: 6333 (REST), 6334 (gRPC)
- CloudWatch logging
```

**Strengths**:
- ✅ Uses official Qdrant image: `qdrant/qdrant:${var.qdrant_version}`
- ✅ Proper EFS mounting to /qdrant/storage
- ✅ Both REST and gRPC ports exposed
- ✅ Higher resource allocation (4 vCPU vs 2 for LanceDB)

**Critical Gaps**:
- ❌ **No outputs.tf** - Cannot discover endpoints
- ❌ **No FSx Lustre option** (same as LanceDB)
- ❌ Missing: Load Balancer for stable endpoint
- ❌ Missing: Service Discovery
- ❌ Missing: Health checks
- ❌ Single mount target (not HA)

**Recommendation**: 🔧 **MEDIUM PRIORITY - Add outputs, ALB, FSx option**

---

### Backend #7: Qdrant on ECS + EBS ❌

**Status**: **BROKEN ARCHITECTURE - Same issue as LanceDB EBS**

**Current State**: 
- No implementation (correctly!) 
- Module `qdrant_ecs` only supports EFS

**The Problem** (same as LanceDB):
```
ECS Fargate + EBS = IMPOSSIBLE ❌
```

**What's Needed**:
```terraform
# NEW MODULE REQUIRED: terraform/modules/qdrant_ecs_ec2/

# EC2 launch type with:
- ASG with EC2 instances
- EBS volumes attached to instances
- Docker volume mount in task definition
- Proper placement in specific AZ
```

**Alternative Approach** (already exists):
```terraform
# EXISTING: terraform/modules/qdrant/ (EC2-based)
# This module actually implements Qdrant + EBS correctly!
# But it's marked as deprecated and not used in main.tf

# Decision: Either un-deprecate this module or create qdrant_ecs_ec2
```

**Recommendation**: 🔧 **MEDIUM PRIORITY - Un-deprecate EC2 module or create ecs_ec2**

---

## 3. ECS Infrastructure Components Analysis

### 3.1 Cluster Architecture

**Current Design**: **Per-Backend Isolated Clusters** ❌

```terraform
# PROBLEM: Each backend creates its own cluster
module "lancedb_s3" {
  # Creates: videolake-lancedb-s3-cluster
}

module "lancedb_efs" {
  # Creates: videolake-lancedb-efs-cluster  
}

module "qdrant" {
  # Creates: videolake-qdrant-cluster
}
```

**Issues**:
- ❌ Resource waste (cluster overhead per backend)
- ❌ Increased cost (CloudWatch Container Insights per cluster)
- ❌ Harder to manage and monitor
- ❌ No resource sharing

**Recommended Design**: **Shared ECS Cluster**

```terraform
# PROPOSAL: Single shared cluster
module "ecs_cluster" {
  source = "./modules/ecs_cluster"
  
  name = "videolake-backends"
  enable_container_insights = true
  
  capacity_providers = {
    fargate = true
    ec2     = true  # For EBS backends
  }
}

# All services use the shared cluster
module "lancedb_s3" {
  cluster_id = module.ecs_cluster.cluster_id
}
```

**Benefits**:
- ✅ Reduced costs (single Container Insights bill)
- ✅ Better resource utilization
- ✅ Centralized monitoring
- ✅ Easier cluster-level configuration

---

### 3.2 Task Definitions Analysis

| Backend | CPU | Memory | Launch Type | Image Source | Health Check |
|---------|-----|--------|-------------|--------------|--------------|
| LanceDB (all) | 2048 | 8192 | Fargate | Custom (missing) | ❌ None |
| Qdrant ECS | 4096 | 16384 | Fargate | Official Docker Hub | ❌ None |

**Issues**:
- ❌ No health check commands in task definitions
- ❌ LanceDB requires custom Docker image (not documented)
- ⚠️ Resource allocation not validated against workload

**Recommended Additions**:
```terraform
container_definitions = [{
  # ... existing config ...
  
  healthCheck = {
    command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
    interval    = 30
    timeout     = 5
    retries     = 3
    startPeriod = 60
  }
}]
```

---

### 3.3 Service Configuration

**Current State**: Basic service with no advanced features

```terraform
resource "aws_ecs_service" "service" {
  name            = "${var.deployment_name}-service"
  cluster         = aws_ecs_cluster.cluster.id
  task_definition = aws_ecs_task_definition.task.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.sg.id]
    assign_public_ip = true  # ⚠️ Not production-ready
  }
}
```

**Missing Features**:
- ❌ No load balancer integration
- ❌ No service discovery
- ❌ No autoscaling
- ❌ No circuit breakers
- ❌ No deployment configuration (rolling updates)

**Production-Grade Service**:
```terraform
resource "aws_ecs_service" "service" {
  # ... existing config ...
  
  # Load Balancer
  load_balancer {
    target_group_arn = aws_lb_target_group.service.arn
    container_name   = "service"
    container_port   = 8000
  }
  
  # Service Discovery
  service_registries {
    registry_arn = aws_service_discovery_service.service.arn
  }
  
  # Autoscaling
  desired_count = 2  # Minimum for HA
  
  # Deployment Configuration
  deployment_configuration {
    maximum_percent         = 200
    minimum_healthy_percent = 100
    
    deployment_circuit_breaker {
      enable   = true
      rollback = true
    }
  }
  
  # Health Checks
  health_check_grace_period_seconds = 60
}
```

---

### 3.4 IAM Roles & Policies

**Current Implementation**: ✅ **Good foundation**

Each ECS module creates:
```terraform
# Task Execution Role (pulls images, writes logs)
resource "aws_iam_role" "ecs_execution" {
  assume_role_policy = ... # ecs-tasks.amazonaws.com
}
resource "aws_iam_role_policy_attachment" "ecs_execution" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Task Role (application permissions)
resource "aws_iam_role" "ecs_task" {
  assume_role_policy = ... # ecs-tasks.amazonaws.com
}
```

**Strengths**:
- ✅ Proper separation of execution vs task roles
- ✅ LanceDB S3 backend has S3 access policy
- ✅ Following AWS best practices

**Gaps**:
- ⚠️ Task roles for EFS/FSx backends have no policies (might be OK)
- ❌ No CloudWatch metrics/logs permissions on task role
- ❌ Missing XRay permissions for tracing
- ❌ No Secrets Manager access for API keys

**Recommendations**:
```terraform
# Add to task role
resource "aws_iam_role_policy" "observability" {
  role = aws_iam_role.ecs_task.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

### 3.5 Networking Architecture

**Current Design**: **Default VPC with Public IPs** ⚠️

```terraform
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

network_configuration {
  subnets          = data.aws_subnets.default.ids
  assign_public_ip = true  # ⚠️ Direct internet access
}
```

**Issues**:
- ⚠️ Relies on default VPC (may not exist, not best practice)
- ⚠️ Public IP assignment (exposes services directly)
- ⚠️ No NAT Gateway (can't use private subnets)
- ⚠️ No multi-AZ configuration
- ⚠️ Security groups allow 0.0.0.0/0 (too permissive)

**Production-Grade Network Design**:
```terraform
# NEW MODULE REQUIRED: terraform/modules/vpc/

module "vpc" {
  name = "videolake-backends"
  cidr = "10.0.0.0/16"
  
  azs             = ["us-east-1a", "us-east-1b", "us-east-1c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
  
  enable_nat_gateway = true
  single_nat_gateway = false  # Multi-AZ NAT for HA
  
  enable_dns_hostnames = true
  enable_dns_support   = true
}

# ECS Services in PRIVATE subnets
network_configuration {
  subnets          = module.vpc.private_subnet_ids
  security_groups  = [aws_security_group.service.id]
  assign_public_ip = false  # Use NAT Gateway
}

# ALB in PUBLIC subnets
resource "aws_lb" "service" {
  subnets         = module.vpc.public_subnet_ids
  security_groups = [aws_security_group.alb.id]
}
```

---

### 3.6 Security Groups

**Current Implementation**: ✅ **Functional but overly permissive**

```terraform
# Example: LanceDB security group
resource "aws_security_group" "lancedb" {
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks  # Default: ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

**Issues**:
- ⚠️ Default allows all internet (0.0.0.0/0)
- ⚠️ Egress allows all (should be restrictive)
- ❌ No separation of ALB traffic vs direct access

**Best Practice Security Groups**:
```terraform
# ALB Security Group
resource "aws_security_group" "alb" {
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr_blocks  # Customer-controlled
  }
}

# ECS Service Security Group
resource "aws_security_group" "service" {
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]  # Only from ALB
  }
  
  egress {
    # Specific destinations only
    to_port         = 443
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]  # HTTPS to AWS APIs
    description     = "AWS API access"
  }
}
```

---

### 3.7 Missing Components Summary

| Component | Status | Priority | Effort | Required For |
|-----------|--------|----------|--------|--------------|
| **VPC Module** | ❌ Missing | HIGH | 2-3 days | Production networking |
| **Application Load Balancer** | ❌ Missing | HIGH | 1-2 days | Stable endpoints, health checks |
| **Service Discovery** | ❌ Missing | MEDIUM | 1 day | Service-to-service communication |
| **Autoscaling** | ❌ Missing | MEDIUM | 1 day | Production traffic handling |
| **FSx Lustre Module** | ❌ Missing | MEDIUM | 2 days | High-performance backends |
| **ECS EC2 Launch Type** | ❌ Missing | HIGH | 3-4 days | EBS-based backends |
| **Shared ECS Cluster** | ❌ Missing | LOW | 1 day | Cost optimization |

---

## 4. Storage Configuration Analysis

### 4.1 S3 Storage

**Backends Using S3**:
- S3Vector (Direct) - ✅ Complete
- LanceDB + S3 - ✅ Complete
- Shared media bucket - ✅ Complete

**Implementation Quality**: ✅ **EXCELLENT**

```terraform
# Example: s3_data_buckets module
resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "data" {
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  # Smart tiering and expiration rules
}

resource "aws_s3_bucket_policy" "bedrock_access" {
  # Proper service access policies
}
```

**Strengths**:
- ✅ Versioning enabled
- ✅ Encryption at rest (SSE-S3 or KMS)
- ✅ Lifecycle policies for cost optimization
- ✅ Service access policies (Bedrock)
- ✅ CORS configuration for web upload
- ✅ Public access blocking

**No gaps** - S3 storage is production-ready ✅

---

### 4.2 EFS Storage

**Backends Using EFS**:
- LanceDB + EFS - ⚠️ Partial
- Qdrant + EFS - ⚠️ Partial

**Current Implementation**:
```terraform
resource "aws_efs_file_system" "storage" {
  performance_mode = "generalPurpose"  # Or "maxIO" for "ebs" type
  throughput_mode  = "bursting"
  encrypted        = true
}

resource "aws_efs_mount_target" "storage" {
  file_system_id  = aws_efs_file_system.storage.id
  subnet_id       = data.aws_subnets.default.ids[0]  # Single AZ!
  security_groups = [aws_security_group.efs.id]
}
```

**Issues**:
- ⚠️ **Single mount target** (single AZ = no HA)
- ⚠️ **Bursting throughput only** (no provisioned option)
- ⚠️ **No performance tuning** (no lifecycle policies, throughput config)
- ⚠️ **Confusing variable naming** (`backend_type = "ebs"` creates EFS!)

**Recommendations**:
```terraform
resource "aws_efs_file_system" "storage" {
  performance_mode = var.performance_mode  # generalPurpose or maxIO
  throughput_mode  = var.throughput_mode   # bursting or provisioned
  
  provisioned_throughput_in_mibps = (
    var.throughput_mode == "provisioned" 
    ? var.provisioned_throughput_mibps 
    : null
  )
  
  lifecycle_policy {
    transition_to_ia = var.transition_to_ia  # Cost optimization
  }
}

# Multi-AZ mount targets
resource "aws_efs_mount_target" "storage" {
  count = length(var.subnet_ids)
  
  file_system_id  = aws_efs_file_system.storage.id
  subnet_id       = var.subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}
```

---

### 4.3 EBS Storage (BROKEN)

**Backends Requiring EBS**:
- LanceDB + EBS - ❌ Not possible with current Fargate implementation
- Qdrant + EBS - ❌ Not possible with current Fargate implementation

**The Fundamental Issue**:

```
┌──────────────────────────────────────────────────┐
│  EBS Volumes CANNOT be used with ECS Fargate     │
│                                                   │
│  Fargate = AWS-managed compute (no EC2 instance) │
│  EBS = Block storage that attaches to EC2        │
│  Result: Architectural impossibility              │
└──────────────────────────────────────────────────┘
```

**Current Modules**:
1. `lancedb_ecs` - Claims to support "ebs" but creates EFS
2. `qdrant_ecs` - Only supports EFS
3. `qdrant` (deprecated) - EC2-based, properly uses EBS

**What's Actually Needed**:

```terraform
# NEW MODULE: lancedb_ecs_ec2/

# EC2 Launch Template with EBS
resource "aws_launch_template" "lancedb" {
  image_id      = data.aws_ami.ecs_optimized.id
  instance_type = var.instance_type
  
  block_device_mappings {
    device_name = "/dev/xvdb"
    
    ebs {
      volume_size           = var.ebs_volume_size
      volume_type           = "gp3"
      iops                  = 3000
      throughput            = 125
      delete_on_termination = false  # Persistent
    }
  }
  
  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    cluster_name = aws_ecs_cluster.cluster.name
  }))
}

# Auto Scaling Group
resource "aws_autoscaling_group" "lancedb" {
  desired_capacity = 1
  max_size         = 1
  min_size         = 1
  
  launch_template {
    id      = aws_launch_template.lancedb.id
    version = "$Latest"
  }
}

# ECS Capacity Provider
resource "aws_ecs_capacity_provider" "lancedb" {
  name = "lancedb-ec2"
  
  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.lancedb.arn
  }
}

# ECS Service (EC2 launch type)
resource "aws_ecs_service" "lancedb" {
  launch_type = "EC2"  # NOT Fargate!
  
  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.lancedb.name
    weight            = 1
  }
}

# Task Definition with Docker volume
resource "aws_ecs_task_definition" "lancedb" {
  requires_compatibilities = ["EC2"]
  
  volume {
    name = "lancedb-data"
    
    docker_volume_configuration {
      scope  = "shared"
      driver = "local"
      driver_opts = {
        type   = "none"
        device = "/dev/xvdb"
        o      = "bind"
      }
    }
  }
}
```

**Effort Estimate**: 3-4 days per backend (LanceDB, Qdrant)

---

### 4.4 FSx Lustre (NOT IMPLEMENTED)

**Backends Requiring FSx**:
- LanceDB + FSx - ❌ Missing
- Qdrant + FSx - ❌ Missing

**Current State**: No FSx implementation exists

**FSx Lustre Use Case**:
- High-performance parallel filesystem
- S3 data repository integration (auto-import/export)
- 200+ MB/s per TiB of storage
- Ideal for ML training workloads

**Required Implementation**:

```terraform
# NEW: Add to lancedb_ecs and qdrant_ecs modules

resource "aws_fsx_lustre_file_system" "storage" {
  count = var.backend_type == "fsx" ? 1 : 0
  
  storage_capacity            = 1200  # Minimum
  subnet_ids                  = [var.subnet_id]
  deployment_type             = "PERSISTENT_1"
  per_unit_storage_throughput = 200
  
  # S3 integration
  import_path      = "s3://${var.s3_bucket}/lancedb/"
  export_path      = "s3://${var.s3_bucket}/lancedb/"
  imported_file_chunk_size = 1024
  
  # Auto-import on file changes
  auto_import_policy = "NEW_CHANGED"
}

resource "aws_efs_mount_target_security_group" {  # Reuse for FSx
  security_group_id = aws_security_group.lustre.id
}
```

**Considerations**:
- ⚠️ Minimum 1.2 TiB storage ($145/month)
- ⚠️ Higher cost than EFS for small datasets
- ✅ Significantly faster than EFS for parallel access
- ✅ S3 integration is killer feature

**Recommendation**: 🔧 **LOW-MEDIUM PRIORITY** - Add as optional flag

---

### 4.5 Storage Performance Comparison

| Storage Type | Latency | Throughput | Cost/Month | HA | Use Case |
|--------------|---------|------------|------------|----|----|
| **S3** | High (100-200ms) | 5,500 GET/s | $23/TB | ✅ Multi-AZ | Large datasets, cost-sensitive |
| **EFS (Bursting)** | Medium (1-10ms) | Burst to 100 MB/s | $300/TB | ✅ Multi-AZ | Shared access, general purpose |
| **EFS (Provisioned)** | Medium (1-10ms) | Up to 1024 MB/s | $300/TB + $6/MB/s | ✅ Multi-AZ | High throughput needs |
| **FSx Lustre** | Low (<1ms) | 200+ MB/s | $145/TB | ⚠️ Single-AZ | ML training, parallel I/O |
| **EBS gp3** | Very Low (<1ms) | 1000 MB/s | $80/TB | ❌ Single-AZ | Single-node, lowest latency |

**Recommendation Matrix**:
```
Cost-Optimized:        S3 > EFS (bursting) > EBS > FSx > EFS (provisioned)
Performance-Optimized: EBS > FSx > EFS (provisioned) > EFS (bursting) > S3
HA-Required:           EFS > FSx (with backup) > S3 >> EBS
Shared Access:         EFS > FSx > S3 >> EBS (impossible)
```

---

## 5. Gap Analysis by Backend

### Summary Matrix

| Backend Configuration | Module Exists | ECS Ready | Storage OK | Networking | Outputs | Priority | Effort |
|----------------------|---------------|-----------|------------|------------|---------|----------|---------|
| 1. S3Vector (Direct) | ✅ Yes | N/A | ✅ | N/A | ✅ | ✅ DONE | 0 days |
| 2. OpenSearch + S3Vector | ✅ Yes | N/A | ✅ | ⚠️ Default VPC | ❌ None | 🔧 HIGH | 1 day |
| 3. LanceDB + S3 | ✅ Yes | ⚠️ Partial | ✅ | ⚠️ No ALB/SD | ❌ None | 🔧 HIGH | 2 days |
| 4. LanceDB + EFS | ✅ Yes | ⚠️ Partial | ⚠️ Single AZ | ⚠️ No ALB/SD | ❌ None | 🔧 MEDIUM | 2 days |
| 5. LanceDB + EBS | ❌ Broken | ❌ No | ❌ | ❌ | ❌ None | 🔧 HIGH | 4 days |
| 6. Qdrant + EFS | ✅ Yes | ⚠️ Partial | ⚠️ Single AZ | ⚠️ No ALB/SD | ❌ None | 🔧 MEDIUM | 2 days |
| 7. Qdrant + EBS | ❌ Broken | ❌ No | ❌ | ❌ | ❌ None | 🔧 MEDIUM | 4 days |
| **FSx Lustre Option** | ❌ Missing | ❌ No | ❌ | N/A | N/A | 🔧 LOW | 3 days |

---

### Detailed Gap Analysis

#### Backend #1: AWS S3Vector (Direct) ✅
**Status**: COMPLETE - No gaps

**Gaps**: None

**Effort**: 0 days

---

#### Backend #2: OpenSearch + S3Vector ⚠️

**Missing Components**:
1. ❌ **outputs.tf** (CRITICAL)
   - Domain endpoint
   - Domain ARN
   - Dashboard URL
   - Master user ARN

2. ⚠️ **VPC Configuration** (MEDIUM)
   - Uses default VPC
   - Should use dedicated VPC for isolation

3. ⚠️ **Access Policies** (MEDIUM)
   - No resource-based access policy
   - Applications can't connect without manual setup

**Required Implementation**:
```terraform
# outputs.tf
output "domain_endpoint" {
  value = aws_opensearch_domain.s3vector_backend.endpoint
}

output "domain_arn" {
  value = aws_opensearch_domain.s3vector_backend.arn
}

output "kibana_endpoint" {
  value = "${aws_opensearch_domain.s3vector_backend.endpoint}/_dashboards"
}

# main.tf - Add access policy
resource "aws_opensearch_domain_policy" "access" {
  domain_name = aws_opensearch_domain.s3vector_backend.domain_name
  
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        AWS = var.allowed_principal_arns
      }
      Action = "es:*"
      Resource = "${aws_opensearch_domain.s3vector_backend.arn}/*"
    }]
  })
}
```

**Effort**: 1 day
**Priority**: HIGH

---

#### Backend #3: LanceDB + S3 ⚠️

**Missing Components**:
1. ❌ **outputs.tf** (CRITICAL)
   - Service endpoint/DNS
   - Cluster ARN
   - Security group ID

2. ❌ **Application Load Balancer** (CRITICAL)
   - Stable endpoint
   - Health checks
   - SSL termination

3. ❌ **Service Discovery** (HIGH)
   - DNS-based service registry
   - Cloud Map integration

4. ⚠️ **Docker Image** (CRITICAL)
   - Custom image not documented
   - No Dockerfile provided
   - Build/push pipeline missing

**Required Files**:
```
terraform/modules/lancedb_ecs/
├── main.tf
├── variables.tf
├── outputs.tf          # NEW
└── alb.tf              # NEW

docker/lancedb-api/
├── Dockerfile          # NEW
├── requirements.txt    # NEW
├── app.py              # NEW
└── README.md           # NEW
```

**Effort**: 2 days
**Priority**: HIGH

---

#### Backends #4 & #6: LanceDB/Qdrant + EFS ⚠️

**Missing Components**:
1. ❌ **Multi-AZ EFS** (HIGH)
   - Single mount target
   - Not HA

2. **Performance Configuration** (MEDIUM)
   - No provisioned throughput option
   - No performance mode choice

3. ❌ **FSx Lustre Option** (MEDIUM)
   - High-performance alternative
   - S3 integration

4. **Same networking gaps as Backend #3**

**Required Changes**:
```terraform
# Add to variables.tf
variable "efs_mount_targets_count" {
  default = 2  # Multi-AZ
}

variable "performance_mode" {
  default = "generalPurpose"
  validation {
    condition = contains(["generalPurpose", "maxIO"], var.performance_mode)
  }
}

variable "throughput_mode" {
  default = "bursting"
  validation {
    condition = contains(["bursting", "provisioned"], var.throughput_mode)
  }
}

# Update main.tf
resource "aws_efs_mount_target" "storage" {
  count = var.efs_mount_targets_count
  
  file_system_id  = aws_efs_file_system.storage.id
  subnet_id       = var.subnet_ids[count.index]
  security_groups = [aws_security_group.efs.id]
}
```

**Effort**: 2 days each
**Priority**: MEDIUM

---

#### Backends #5 & #7: LanceDB/Qdrant + EBS ❌

**Current State**: BROKEN - Cannot work with Fargate

**Required Solution**: New EC2-based modules

**Missing Components**:
1. ❌ **New Module**: `lancedb_ecs_ec2/` (4 days)
2. ❌ **New Module**: `qdrant_ecs_ec2/` (4 days)

**Alternative**: Un-deprecate existing `qdrant/` module (EC2-based, 1 day)

**Module Structure**:
```
terraform/modules/
├── lancedb_ecs_ec2/
│   ├── main.tf              # EC2 launch template, ASG
│   ├── variables.tf
│   ├── outputs.tf
│   ├── user_data.sh         # ECS agent + Docker volume setup
│   └── README.md
└── qdrant_ecs_ec2/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── user_data.sh
    └── README.md
```

**Key Resources Needed**:
- `aws_launch_template` with EBS block device
- `aws_autoscaling_group` (desired_capacity = 1)
- `aws_ecs_capacity_provider` (EC2-based)
- `aws_ecs_service` with `launch_type = "EC2"`
- Docker volume configuration in task definition
- User data script for ECS agent + volume mounting

**Effort**: 4 days each (8 days total)
**Priority**: HIGH (architectural blocker)

---

## 6. Terraform Best Practices Assessment

### 6.1 Module Design ⚠️

**Current State**: Monolithic modules with mixed concerns

**Issues**:
- ⚠️ Each module creates its own ECS cluster (should be shared)
- ⚠️ Storage and compute tightly coupled
- ⚠️ No separation of networking concerns

**Best Practice**: Composable modules

```terraform
# RECOMMENDED STRUCTURE:
modules/
├── vpc/                    # Networking foundation
├── ecs_cluster/            # Shared cluster
├── ecs_service/            # Generic service template
├── alb/                    # Load balancer
├── storage/
│   ├── s3/
│   ├── efs/
│   ├── fsx/
│   └── ebs/
└── backends/
    ├── s3vector/
    ├── opensearch/
    ├── lancedb/
    └── qdrant/
```

**Score**: ⚠️ 5/10 - Functional but not optimal

---

### 6.2 Variable Naming & Documentation ⚠️

**Issues**:
- ⚠️ Confusing: `backend_type = "ebs"` creates EFS!
- ⚠️ Inconsistent naming (e.g., `deployment_name` vs `domain_name`)
- ✅ Good: Most variables have descriptions
- ✅ Good: Validation blocks where needed

**Recommendations**:
```terraform
# CLEAR variable naming
variable "storage_type" {  # NOT "backend_type"
  description = "Storage backend: s3, efs, or fsx_lustre"
  validation {
    condition = contains(["s3", "efs", "fsx_lustre"], var.storage_type)
    error_message = "Must be s3, efs, or fsx_lustre. For EBS, use the _ec2 module variant."
  }
}
```

**Score**: ⚠️ 6/10 - Needs clarification

---

### 6.3 Output Definitions ❌

**Critical Issue**: Most modules missing outputs

**Current State**:
- ✅ `s3vector` - 8 outputs (excellent)
- ✅ `s3_data_buckets` - 3 outputs (good)
- ✅ `qdrant` (deprecated) - 3 outputs
- ❌ `opensearch` - 0 outputs
- ❌ `lancedb_ecs` - 0 outputs
- ❌ `qdrant_ecs` - 0 outputs

**Impact**: Cannot integrate modules with application layer!

**Required outputs** (minimum):
```terraform
output "endpoint" {
  description = "Service endpoint (ALB DNS or ECS task ENI)"
  value       = aws_lb.service.dns_name
}

output "port" {
  description = "Service port"
  value       = 8000
}

output "security_group_id" {
  description = "Security group ID for ingress rules"
  value       = aws_security_group.service.id
}

output "cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.cluster.arn
}
```

**Score**: ❌ 3/10 - Critical gap

---

### 6.4 State Management

**Current Approach**: Local state (default)

```terraform
# terraform.tfstate stored locally
# NO REMOTE BACKEND CONFIGURED
```

**Issues**:
- ⚠️ No state locking (concurrent apply risk)
- ⚠️ No state backup
- ⚠️ Team collaboration difficult

**Recommendation**:
```terraform
terraform {
  backend "s3" {
    bucket         = "videolake-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "videolake-terraform-locks"
  }
}
```

**Score**: ⚠️ 4/10 - Works for solo, not for teams

---

### 6.5 Module Versioning

**Current State**: No versioning

```terraform
module "lancedb" {
  source = "./modules/lancedb_ecs"  # Local path, no version
}
```

**Best Practice**:
```terraform
module "lancedb" {
  source  = "github.com/videolake/terraform-modules//lancedb_ecs?ref=v1.2.0"
  version = "~> 1.2"
}
```

**Score**: ⚠️ 4/10 - OK for monorepo, not for distribution

---

### 6.6 Resource Tagging ✅

**Current State**: EXCELLENT

```terraform
default_tags {
  tags = {
    Project     = "Videolake"
    ManagedBy   = "Terraform"
    Environment = var.environment
  }
}

# Module-level tags
tags = merge(var.tags, {
  Name      = "${var.deployment_name}"
  Service   = "LanceDB"
  Backend   = var.backend_type
  ManagedBy = "Terraform"
})
```

**Score**: ✅ 9/10 - Best practice

---

### 6.7 Security Defaults ⚠️

**Current State**: Some good, some bad

**Good** ✅:
- Encryption at rest (S3, EFS, EBS)
- Transit encryption (EFS, OpenSearch)
- IAM roles following least privilege

**Bad** ❌:
- Security groups allow 0.0.0.0/0 by default
- Public IP assignment on ECS tasks
- No Secrets Manager for credentials
- Hardcoded passwords in variables

**Recommendations**:
```terraform
# Use Secrets Manager
data "aws_secretsmanager_secret_version" "opensearch_password" {
  secret_id = var.master_password_secret_arn
}

# Restrict security group defaults
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access service"
  type        = list(string)
  default     = []  # Force explicit configuration
  
  validation {
    condition     = length(var.allowed_cidr_blocks) > 0
    error_message = "You must specify allowed CIDR blocks. Do not use 0.0.0.0/0 in production."
  }
}
```

**Score**: ⚠️ 6/10 - Security conscious but too permissive

---

### 6.8 Documentation ⚠️

**Current State**: Inline comments, no READMEs

**Missing**:
- ❌ README.md per module
- ❌ Usage examples
- ❌ Architecture diagrams
- ⚠️ terraform.tfvars.example exists (good!)

**Required Documentation**:
```
modules/lancedb_ecs/
├── README.md          # Module documentation
├── examples/
│   ├── s3/           # S3 backend example
│   ├── efs/          # EFS backend example
│   └── complete/     # Full example with ALB
└── diagrams/
    └── architecture.png
```

**Score**: ⚠️ 4/10 - Needs improvement

---

### Best Practices Summary

| Practice | Score | Status | Priority |
|----------|-------|--------|----------|
| Module Design | 5/10 | ⚠️ Monolithic | MEDIUM |
| Variable Naming | 6/10 | ⚠️ Confusing | HIGH |
| Output Definitions | 3/10 | ❌ Missing | CRITICAL |
| State Management | 4/10 | ⚠️ Local only | LOW |
| Module Versioning | 4/10 | ⚠️ None | LOW |
| Resource Tagging | 9/10 | ✅ Excellent | DONE |
| Security Defaults | 6/10 | ⚠️ Too permissive | HIGH |
| Documentation | 4/10 | ⚠️ Minimal | MEDIUM |
| **Overall** | **5.1/10** | ⚠️ **Needs Work** | **HIGH** |

---

## 7. Implementation Roadmap

### Phase 1: Critical Fixes (1-2 weeks)

**Goal**: Make existing backends production-usable

**Priority 1 - Add Outputs** (2 days)
```
✅ Task: Create outputs.tf for all modules
- opensearch: endpoint, ARN, dashboard URL
- lancedb_ecs: ALB DNS, cluster ARN, service ARN
- qdrant_ecs: ALB DNS, cluster ARN, service ARN

Deliverable: All modules have at least 5 outputs
```

**Priority 2 - Fix Variable Naming** (1 day)
```
✅ Task: Clarify confusing variables
- Rename backend_type to storage_type
- Add clear validation messages
- Update documentation

Deliverable: No more confusion about "ebs" creating EFS
```

**Priority 3 - Docker Images** (2 days)
```
✅ Task: Create and document LanceDB API wrapper
- docker/lancedb-api/Dockerfile
- FastAPI wrapper around LanceDB
- Health check endpoint
- ECR push automation

Deliverable: Public ECR image or build instructions
```

**Priority 4 - Load Balancers** (3 days)
```
✅ Task: Add ALB to LanceDB and Qdrant ECS services
- Create alb.tf in each module
- Target group with health checks
- HTTPS listener (optional)
- Update service to use ALB

Deliverable: Stable endpoints for all ECS services
```

---

### Phase 2: EBS Backend Support (2-3 weeks)

**Goal**: Enable EBS-based backends properly

**Task 1 - Create EC2-based Modules** (8 days)
```
✅ New Module: lancedb_ecs_ec2/
- EC2 launch template with EBS
- Auto Scaling Group (size 1)
- ECS capacity provider
- Task definition with Docker volume
- User data for EBS mounting

✅ New Module: qdrant_ecs_ec2/
- Same architecture as LanceDB
- Qdrant-specific configuration

Deliverable: Both backends working with EBS
```

**Task 2 - Un-deprecate or Replace** (2 days)
```
Decision: Keep or remove deprecated modules?

Option A: Un-deprecate qdrant/ module
- Already implements EC2 + EBS correctly
- Just needs outputs and testing

Option B: Use new qdrant_ecs_ec2/ module
- More consistent with other modules
- Follows ECS patterns

Recommendation: Option B (consistency)
```

---

### Phase 3: Networking & HA (2-3 weeks)

**Goal**: Production-grade networking

**Task 1 - VPC Module** (3 days)
```
✅ New Module: vpc/
- Multi-AZ VPC with public/private subnets
- NAT Gateways for private subnet internet access
- VPC endpoints for AWS services
- Flow logs for security analysis

Deliverable: Reusable VPC module
```

**Task 2 - Service Discovery** (2 days)
```
✅ Add to ECS modules:
- Cloud Map namespace
- Service Discovery service
- DNS-based routing

Deliverable: Services discoverable via DNS
```

**Task 3 - Multi-AZ EFS** (1 day)
```
✅ Update lancedb_ecs and qdrant_ecs:
- Mount targets in multiple subnets
- Cross-AZ access

Deliverable: HA-ready EFS deployments
```

---

### Phase 4: FSx Lustre Support (1 week)

**Goal**: High-performance storage option

**Task 1 - FSx Module** (3 days)
```
✅ Add FSx Lustre to lancedb_ecs and qdrant_ecs:
- New storage_type = "fsx_lustre"
- FSx file system creation
- S3 data repository integration
- Security group configuration

Deliverable: FSx option for both backends
```

**Task 2 - Performance Testing** (2 days)
```
✅ Validate FSx vs EFS performance:
- Write/read benchmarks
- Latency measurements
- Cost analysis

Deliverable: Performance comparison documentation
```

---

### Phase 5: Optimization & Polish (1-2 weeks)

**Goal**: Cost optimization and usability

**Task 1 - Shared ECS Cluster** (2 days)
```
✅ Refactor to use shared cluster:
- Create ecs_cluster module
- All services use same cluster
- Capacity providers for Fargate + EC2

Deliverable: 50% reduction in cluster costs
```

**Task 2 - Autoscaling** (2 days)
```
✅ Add to ECS services:
- Target tracking scaling policies
- CloudWatch alarms
- Scale on CPU/memory

Deliverable: Auto-scaling ECS services
```

**Task 3 - Documentation** (3 days)
```
✅ Module READMEs:
- Architecture diagrams
- Usage examples
- Cost estimates
- Troubleshooting guides

Deliverable: Complete module documentation
```

---

### Implementation Priority Matrix

```
┌────────────────────────────────────────────────────────┐
│  PRIORITY MATRIX                                       │
│                                                        │
│  Critical   ┃ Phase 1: Outputs, ALB, Docker images    │
│  High       ┃ Phase 2: EBS backend support            │
│  Medium     ┃ Phase 3: Networking, Multi-AZ           │
│  Low        ┃ Phase 4: FSx Lustre                     │
│  Polish     ┃ Phase 5: Shared cluster, autoscaling    │
└────────────────────────────────────────────────────────┘
```

---

## 8. Effort Estimates

### By Component

| Component | Effort | Priority | Dependencies |
|-----------|--------|----------|--------------|
| **Add Outputs** | 2 days | CRITICAL | None |
| **Fix Variable Names** | 1 day | HIGH | None |
| **Docker Images** | 2 days | CRITICAL | None |
| **Application Load Balancers** | 3 days | CRITICAL | Outputs |
| **LanceDB ECS EC2 Module** | 4 days | HIGH | VPC (optional) |
| **Qdrant ECS EC2 Module** | 4 days | HIGH | VPC (optional) |
| **VPC Module** | 3 days | MEDIUM | None |
| **Service Discovery** | 2 days | MEDIUM | VPC |
| **Multi-AZ EFS** | 1 day | MEDIUM | None |
| **FSx Lustre Support** | 3 days | LOW | None |
| **Shared ECS Cluster** | 2 days | LOW | None |
| **Autoscaling** | 2 days | LOW | ALB |
| **Documentation** | 3 days | MEDIUM | All above |

**Total Effort**: ~32 developer days (~6-7 weeks for 1 developer)

---

### By Phase

| Phase | Duration | Effort | Parallel Work Possible? |
|-------|----------|--------|-------------------------|
| Phase 1: Critical Fixes | 1-2 weeks | 8 days | ✅ Yes (outputs, ALB, Docker) |
| Phase 2: EBS Support | 2-3 weeks | 10 days | ⚠️ Partial (2 modules simultaneously) |
| Phase 3: Networking | 2-3 weeks | 6 days | ✅ Yes (VPC, SD, EFS independent) |
| Phase 4: FSx Lustre | 1 week | 5 days | ✅ Yes (both backends) |
| Phase 5: Polish | 1-2 weeks | 7 days | ⚠️ Partial (autoscaling after ALB) |
| **Total** | **7-11 weeks** | **36 days** | **4-5 weeks with 2 developers** |

---

## 9. Risk Assessment

### High-Risk Items

**1. EBS Backend Architecture ⚠️**
- **Risk**: Current Fargate implementation fundamentally incompatible with EBS
- **Impact**: Backends #5 and #7 cannot work as documented
- **Mitigation**: Create EC2-based modules (4 days each)
- **Probability**: 100% (confirmed architectural issue)

**2. Missing Outputs ⚠️**
- **Risk**: Cannot integrate backends with application layer
- **Impact**: Modules are not usable until fixed
- **Mitigation**: Add outputs.tf to all modules (2 days)
- **Probability**: 100% (confirmed gap)

**3. Custom Docker Images ⚠️**
- **Risk**: LanceDB requires custom API wrapper that doesn't exist
- **Impact**: Backend #3, #4, #5 cannot deploy
- **Mitigation**: Build and publish Docker image (2 days)
- **Probability**: 100% (current references non-existent image)

### Medium-Risk Items

**4. Default VPC Dependency ⚠️**
- **Risk**: Deployment fails if default VPC doesn't exist or is modified
- **Impact**: All ECS backends fail to deploy
- **Mitigation**: Create dedicated VPC module (3 days)
- **Probability**: 30% (varies by AWS account)

**5. Single-AZ EFS ⚠️**
- **Risk**: No high availability for EFS-based backends
- **Impact**: AZ failure causes data unavailability
- **Mitigation**: Multi-AZ mount targets (1 day)
- **Probability**: 100% (current implementation)

### Low-Risk Items

**6. Performance Gaps**
- **Risk**: EFS bursting mode insufficient for workload
- **Impact**: Poor query performance
- **Mitigation**: Add provisioned throughput option (1 day)
- **Probability**: 40% (workload-dependent)

---

## 10. Cost Optimization Opportunities

### Current Cost Structure (Per Backend)

**Fargate-based (LanceDB/Qdrant + S3/EFS)**:
```
ECS Cluster:            $0/month (pay per task)
Fargate Task (2 vCPU):  $35/month (always-on)
EFS Storage (100GB):    $30/month
NAT Gateway:            $33/month (if using private subnets)
ALB:                    $22/month
─────────────────────────────────────────────
TOTAL:                  ~$120/month per backend
```

**EC2-based (with EBS)**:
```
ECS Cluster:            $0/month
t3.xlarge EC2:          $122/month
EBS gp3 (100GB):        $8/month
ALB:                    $22/month
─────────────────────────────────────────────
TOTAL:                  ~$152/month per backend
```

**Serverless (S3Vector)**:
```
S3Vector storage:       $0.15/1M vectors
Query costs:            $0.10/1M queries
─────────────────────────────────────────────
TOTAL:                  ~$5-50/month (usage-based)
```

### Optimization Opportunities

**1. Shared ECS Cluster** 💰 **Save $50-100/month**
```
Current:  3 clusters × $0 = $0 (but multiple Container Insights)
Proposed: 1 cluster = $0 + single Container Insights subscription

Savings: ~$50-100/month in monitoring and overhead
```

**2. Fargate Spot** 💰 **Save 70% on compute**
```
Current:  On-demand Fargate
Proposed: Fargate Spot for non-production

Savings: $35/month → $10/month per task (70% reduction)
Risk:    Task interruption (acceptable for dev/test)
```

**3. Single NAT Gateway** 💰 **Save $33/month per region**
```
Current:  Multi-AZ NAT (if implemented)
Proposed: Single NAT for non-production

Savings: $33/month per NAT Gateway removed
Risk:    No HA for outbound traffic
```

**4. EFS Lifecycle Policies** 💰 **Save 80% on storage**
```
Current:  All data on Standard storage class
Proposed: Transition to Infrequent Access after 30 days

Savings: $30/100GB → $6/100GB (80% reduction)
Note:    Only affects infrequently accessed data
```

**5. Reserved Capacity** 💰 **Save 30-50% long-term**
```
For production workloads:
- Savings Plans for Fargate (30% savings)
- Reserved Instances for EC2 (40-50% savings)
- Committed throughput for EFS (20% savings)

Requires: 1-3 year commitment
```

### Cost Comparison: Full Deployment

**Current Architecture** (7 backends, always-on):
```
S3Vector (serverless):         $20/month
OpenSearch (2 × or1.medium):   $200/month
LanceDB S3 (Fargate):          $90/month
LanceDB EFS (Fargate):         $120/month
LanceDB EBS (if fixed, EC2):   $152/month
Qdrant EFS (Fargate):          $120/month
Qdrant EBS (if fixed, EC2):    $152/month
────────────────────────────────────────────
TOTAL:                          ~$854/month
```

**Optimized Architecture**:
```
S3Vector (serverless):         $20/month
OpenSearch (1 × or1.medium):   $100/month (downsize)
Shared ECS Cluster:            $0/month
LanceDB S3 (Spot):             $45/month (50% reduction)
LanceDB EFS (Spot):            $60/month (IA storage)
LanceDB EBS (EC2 Spot):        $50/month (Spot + small instance)
Qdrant EFS (Spot):             $60/month
Qdrant EBS (EC2 Spot):         $50/month
Single NAT Gateway:            $33/month
────────────────────────────────────────────
TOTAL:                          ~$418/month

SAVINGS:                        $436/month (51% reduction)
```

---

## 11. Security & Compliance Considerations

### Current Security Posture

**Strengths** ✅:
- Encryption at rest (all storage)
- Encryption in transit (EFS, OpenSearch)
- IAM roles with least privilege
- VPC security groups
- CloudWatch logging enabled

**Weaknesses** ❌:
- Public IP on ECS tasks (no NAT Gateway)
- Security groups allow 0.0.0.0/0 by default
- Hardcoded credentials in variables
- No Secrets Manager integration
- No VPC endpoint for AWS services

### CIS Benchmark Alignment

| Control | Current | Required | Gap |
|---------|---------|----------|-----|
| **Encryption at Rest** | ✅ All storage | ✅ | None |
| **Encryption in Transit** | ⚠️ Partial (EFS, OS) | ✅ All traffic | Add TLS on ALB |
| **IAM Least Privilege** | ✅ Good | ✅ | None |
| **Network Isolation** | ❌ Public IPs | ✅ Private subnets | Need VPC + NAT |
| **Secrets Management** | ❌ Hardcoded | ✅ Secrets Manager | Migrate passwords |
| **Logging & Monitoring** | ✅ CloudWatch | ✅ | None |
| **Security Groups** | ⚠️ Too permissive | ✅ Restricted | Update defaults |
| **VPC Endpoints** | ❌ None | ✅ ECR, S3, logs | Add endpoints |

**Compliance Score**: ⚠️ 60% - Needs work for production

### Security Improvements Roadmap

**Phase 1: Network Isolation** (3 days)
```
1. Create VPC with private subnets
2. Deploy NAT Gateway for outbound
3. Move ECS tasks to private subnets
4. Remove public IPs
```

**Phase 2: Secrets Management** (2 days)
```
1. Store credentials in Secrets Manager
2. Update task definitions with secret ARNs
3. Grant task roles secretsmanager:GetSecretValue
4. Remove hardcoded passwords
```

**Phase 3: TLS Everywhere** (2 days)
```
1. ACM certificates for ALBs
2. HTTPS listeners (443)
3. Enforce TLS 1.2+
4. Update security groups
```

**Phase 4: VPC Endpoints** (2 days)
```
1. ecr.api endpoint (ECR API)
2. ecr.dkr endpoint (Docker registry)
3. s3 endpoint (S3 access)
4. logs endpoint (CloudWatch)
5. Remove NAT Gateway dependency
```

---

## 12. Testing Strategy

### Current State: No Automated Tests ❌

**Gaps**:
- No Terraform validation in CI/CD
- No integration tests
- No state file testing
- Manual verification only

### Recommended Testing Framework

**Layer 1: Terraform Validation** (Automated)
```bash
# In CI/CD pipeline:
terraform fmt -check -recursive
terraform validate
terraform plan -out=plan.tfplan

# Use checkov for security scanning
checkov -d terraform/
```

**Layer 2: Module Tests** (Terratest)
```go
// tests/lancedb_ecs_test.go
func TestLanceDBECS(t *testing.T) {
  terraformOptions := &terraform.Options{
    TerraformDir: "../modules/lancedb_ecs",
    Vars: map[string]interface{}{
      "deployment_name": "test-lancedb",
      "backend_type": "s3",
    },
  }
  
  defer terraform.Destroy(t, terraformOptions)
  terraform.InitAndApply(t, terraformOptions)
  
  // Validate outputs
  endpoint := terraform.Output(t, terraformOptions, "endpoint")
  assert.NotEmpty(t, endpoint)
}
```

**Layer 3: Integration Tests** (Python)
```python
# tests/test_backends.py
def test_lancedb_s3_deployment():
    """Test LanceDB with S3 backend deploys successfully"""
    subprocess.run(["terraform", "apply", "-auto-approve"])
    
    # Validate service is running
    endpoint = get_terraform_output("lancedb_s3.endpoint")
    response = requests.get(f"http://{endpoint}/health")
    assert response.status_code == 200
```

**Layer 4: E2E Tests** (Real Workload)
```python
def test_vector_search_workflow():
    """Test full vector search workflow across all backends"""
    backends = ["s3vector", "lancedb_s3", "qdrant_efs"]
    
    for backend in backends:
        # Insert vectors
        insert_vectors(backend, test_dataset)
        
        # Query vectors
        results = query_vectors(backend, test_query)
        
        # Validate results
        assert len(results) > 0
        assert results[0].distance < 0.5
```

---

## 13. Migration & Upgrade Path

### For Existing Deployments

**Scenario 1: Using `qdrant/` (deprecated) module**
```terraform
# OLD (EC2-based, works with EBS)
module "qdrant" {
  source = "./modules/qdrant"
  ...
}

# OPTION A: Keep it (if it works)
# - Un-deprecate the module
# - Add outputs
# - Update documentation

# OPTION B: Migrate to ECS EC2
# - Use new qdrant_ecs_ec2 module
# - Same EBS backend
# - Better consistency with other modules
```

**Migration Steps**:
1. Export data from existing Qdrant
2. Create new qdrant_ecs_ec2 deployment
3. Import data to new deployment
4. Update application endpoints
5. Destroy old deployment

**Downtime**: ~30 minutes

---

**Scenario 2: Using `lancedb_ecs` with "ebs" type**
```terraform
# OLD (broken - creates EFS, not EBS)
module "lancedb" {
  backend_type = "ebs"  # This creates EFS!
}

# NEW (correct)
module "lancedb" {
  source       = "./modules/lancedb_ecs_ec2"
  storage_type = "ebs"  # Actually creates EBS
}
```

**Migration Steps**:
1. Backup data from EFS
2. Deploy new lancedb_ecs_ec2 with EBS
3. Restore data to EBS volume
4. Update app config
5. Remove old module

**Downtime**: ~1 hour

---

## 14. Summary & Recommendations

### Executive Summary

Videolake's Terraform infrastructure demonstrates **solid foundations** with **critical gaps** preventing production readiness:

**Strengths** ✅:
- S3Vector backend is production-ready
- Good tagging and encryption practices
- Modular design philosophy
- IAM least privilege

**Critical Gaps** ❌:
- Missing outputs (cannot integrate with apps)
- EBS backends broken (architectural issue)
- No load balancers (no stable endpoints)
- No service discovery
- Custom Docker images missing

**Recommendation**: **3-phase approach**

1. **Phase 1 (2 weeks): Critical Fixes**
   - Add outputs to all modules
   - Create Docker images
   - Deploy Application Load Balancers
   - **Result**: Usable backends

2. **Phase 2 (3 weeks): EBS Support**
   - Create EC2-based modules
   - Fix architectural issues
   - **Result**: All 7 backends functional

3. **Phase 3 (3 weeks): Production-Ready**
   - VPC + networking
   - Service Discovery
   - FSx Lustre support
   - **Result**: Production-grade infrastructure

**Total Effort**: 6-8 weeks with 1-2 developers

---

### Prioritized Action Items

**Week 1-2: CRITICAL** 🔴
```
1. ✅ Add outputs.tf to opensearch, lancedb_ecs, qdrant_ecs
2. ✅ Create lancedb-api Docker image and publish
3. ✅ Deploy ALBs for stable endpoints
4. ✅ Fix confusing variable naming (backend_type → storage_type)
```

**Week 3-5: HIGH** 🟠
```
5. ✅ Create lancedb_ecs_ec2 module for EBS support
6. ✅ Create qdrant_ecs_ec2 module for EBS support
7. ✅ Deploy VPC with private/public subnets
8. ✅ Implement Service Discovery (Cloud Map)
```

**Week 6-8: MEDIUM** 🟡
```
9. ✅ Add FSx Lustre support to both backends
10. ✅ Implement multi-AZ EFS configurations
11. ✅ Create shared ECS cluster module
12. ✅ Add autoscaling policies
```

**Week 9+: POLISH** 🟢
```
13. ✅ Write comprehensive module documentation
14. ✅ Create architecture diagrams
15. ✅ Set up automated testing (Terratest)
16. ✅ Implement cost optimization features
```

---

### Decision Points

**Decision 1: Deprecated Modules**
```
Question: Keep or remove qdrant/ (EC2-based) module?

Option A: Un-deprecate and use for EBS backend
Pros:  Already works, just needs outputs
Cons:  Inconsistent with other modules

Option B: Create new qdrant_ecs_ec2 module
Pros:  Consistent with module patterns
Cons:  Extra work (4 days)

Recommendation: Option B (consistency)
```

**Decision 2: Shared vs Per-Backend Clusters**
```
Question: Single shared cluster or keep isolated?

Option A: Shared cluster (recommended)
Pros:  Cost savings, easier management
Cons:  Noisy neighbor potential

Option B: Keep isolated clusters
Pros:  Complete isolation
Cons:  Higher costs, more overhead

Recommendation: Option A (shared with namespaces)
```

**Decision 3: VPC Strategy**
```
Question: When to migrate off default VPC?

Option A: Immediate (block on Phase 1)
Pros:  Better security from start
Cons:  Delays Phase 1 deliverables

Option B: Phase 3 (after critical fixes)
Pros:  Faster time to usable backends
Cons:  Two migrations needed

Recommendation: Option B (pragmatic)
```

---

### Success Criteria

**Phase 1 Success** (2 weeks):
- [ ] All modules have outputs
- [ ] LanceDB Docker image published
- [ ] ALBs deployed and tested
- [ ] At least 3 backends fully functional
- [ ] Applications can connect to backends

**Phase 2 Success** (5 weeks):
- [ ] All 7 backends deployable
- [ ] EBS backends working (EC2-based)
- [ ] Service Discovery operational
- [ ] Private subnets with NAT Gateway

**Phase 3 Success** (8 weeks):
- [ ] FSx Lustre option available
- [ ] Multi-AZ EFS for HA
- [ ] Autoscaling configured
- [ ] Complete documentation
- [ ] Automated tests passing

---

## 15. Appendix

### A. Backend Requirements Matrix

| Backend | Compute | Storage | Networking | IAM | Monitoring |
|---------|---------|---------|------------|-----|------------|
| S3Vector | None (API) | S3 Vectors | None | Policy | CloudWatch |
| OpenSearch | Managed | EBS + S3 | VPC | Service role | CloudWatch |
| LanceDB S3 | ECS Fargate | S3 | VPC, SG, ALB | Task + Exec | CW Logs |
| LanceDB EFS | ECS Fargate | EFS | VPC, SG, ALB | Task + Exec | CW Logs |
| LanceDB EBS | ECS EC2 | EBS | VPC, SG, ALB | Instance + Task | CW Logs |
| Qdrant EFS | ECS Fargate | EFS | VPC, SG, ALB | Task + Exec | CW Logs |
| Qdrant EBS | ECS EC2 | EBS | VPC, SG, ALB | Instance + Task | CW Logs |

---

### B. Resource Naming Conventions

**Current**: Inconsistent
**Recommended**:

```
Format: {project}-{env}-{backend}-{component}-{unique}

Examples:
- videolake-prod-lancedb-s3-cluster
- videolake-dev-qdrant-efs-alb
- videolake-staging-s3vector-bucket

Benefits:
- Clear ownership
- Easy filtering in AWS Console
- Cost allocation tags
```

---

### C. Useful Terraform Commands

```bash
# Validate syntax
terraform fmt -check -recursive
terraform validate

# Plan with specific backend
terraform plan -target=module.lancedb_s3

# Apply only one backend
terraform apply -target=module.lancedb_s3

# Destroy specific backend
terraform destroy -target=module.lancedb_s3

# Show current state
terraform show

# List resources
terraform state list

# Import existing resource
terraform import module.lancedb_s3.aws_ecs_cluster.cluster cluster-name
```

---

### D. References

- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [ECS + EBS Volumes Guide](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ebs-volumes.html)
- [LanceDB Documentation](https://lancedb.github.io/lancedb/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [FSx Lustre User Guide](https://docs.aws.amazon.com/fsx/latest/LustreGuide/)

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-13  
**Author**: Infrastructure Architect Analysis  
**Status**: Complete - Ready for Implementation