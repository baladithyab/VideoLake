# IMPLEMENTATION GUIDE: Qdrant & LanceDB AWS Best Practices

## KEY FINDINGS

### Storage Backend Decision Matrix

**Use S3 (LanceDB recommended):**
- Multi-tenant RAG applications
- Serverless/Lambda-based architectures
- Cost-conscious deployments (10M vectors = ~$50/month)
- Public API endpoints with variable load
- Data portability requirement

**Use EFS (LanceDB):**
- Stateful microservices on EKS
- Real-time ML feature stores
- Consistent latency requirement (<100ms)
- Multi-pod sharing within VPC
- 24/7 availability required

**Use Qdrant Cloud:**
- Managed operational overhead priority
- Sub-100ms latency requirement
- Enterprise support needed
- Multi-region deployments
- Starting cost: $25/month

**Use Qdrant Self-Hosted:**
- On-premises + cloud hybrid
- Compliance/data sovereignty
- Full control requirement
- High-throughput (10M+ QPS)
- Vertical scaling preferred

---

## QDRANT AWS DEPLOYMENT PATTERNS

### Pattern 1: Production on ECS (Recommended)

**Architecture:**
```
ALB (Application Load Balancer)
  ↓
ECS Service (Qdrant)
  ├─ Primary: m5.xlarge
  ├─ Standby: m5.xlarge
  └─ EBS gp3 (100GB, 5000 IOPS)
     ↓
CloudWatch (Metrics/Logs)
     ↓
S3 (Snapshots)
```

**Deployment Configuration:**
```python
# docker-compose.yml equivalent for ECS
{
    "container_definitions": [{
        "name": "qdrant",
        "image": "qdrant/qdrant:latest",
        "portMappings": [{
            "containerPort": 6333,
            "protocol": "tcp"
        }],
        "environment": [
            {"name": "QDRANT_API_KEY", "value": "your-secure-key"},
            {"name": "QDRANT_SNAPSHOTS_PATH", "value": "/qdrant/snapshots"}
        ],
        "mountPoints": [{
            "sourceVolume": "qdrant-storage",
            "containerPath": "/qdrant/storage",
            "readOnly": False
        }],
        "memory": 16384,
        "cpu": 4096
    }],
    "volumes": [{
        "name": "qdrant-storage",
        "ebs_volume_configuration": {
            "size": 100,
            "volume_type": "gp3",
            "iops": 5000,
            "throughput": 250
        }
    }]
}
```

**Python Client Usage:**
```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# Connection through ALB
client = QdrantClient(
    url="http://my-qdrant-alb.elb.amazonaws.com:6333",
    api_key=os.getenv("QDRANT_API_KEY")
)

# Create collection with HNSW indexing
client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(
        size=1536,  # OpenAI embeddings
        distance=Distance.COSINE
    )
)

# Upsert with metadata for filtering
client.upsert(
    collection_name="documents",
    points=[
        PointStruct(
            id=i,
            vector=embedding,
            payload={
                "document_id": f"doc-{i}",
                "source": "s3://bucket/path",
                "timestamp": datetime.now().isoformat()
            }
        )
        for i, embedding in enumerate(embeddings)
    ]
)

# Search with metadata filtering
from qdrant_client.models import Filter, FieldCondition, MatchValue

results = client.search(
    collection_name="documents",
    query_vector=query_embedding,
    query_filter=Filter(
        must=[
            FieldCondition(
                key="source",
                match=MatchValue(value="s3://bucket/path")
            )
        ]
    ),
    limit=10
)
```

### Pattern 2: Qdrant Cloud (Simplest)

**Setup:**
```python
from qdrant_client import QdrantClient

# 1. Create cluster on https://cloud.qdrant.io
# 2. Copy connection string and API key
# 3. Use in code:

client = QdrantClient(
    url="https://your-cluster-id.qdrant.io",
    api_key="your-api-key"
)

# Everything else is identical
```

**Cost Estimation:**
- Small: $25/month (1M vectors)
- Medium: $50/month (10M vectors)
- Large: Custom pricing (100M+ vectors)

---

## LANCEDB AWS DEPLOYMENT PATTERNS

### Pattern 1: Serverless on S3 (Recommended)

**Architecture:**
```
AWS Lambda Functions
  ↓
LanceDB (in-process)
  ├─ S3 Backend
  │  └─ s3://vector-bucket/lancedb
  ├─ DynamoDB (concurrent write coordination)
  │  └─ lancedb-commits table
  └─ CloudWatch Logs
```

**Implementation:**
```python
import lancedb
import boto3
import os

def initialize_lancedb():
    """Initialize LanceDB with S3 backend and DynamoDB coordination."""
    
    db_uri = os.getenv(
        "LANCEDB_URI",
        "s3+ddb://vector-bucket/lancedb"
    )
    
    storage_options = {
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "aws_region": os.getenv("AWS_REGION", "us-east-1"),
        "ddbTableName": "lancedb-commits",
        "aws_server_side_encryption": "aws:kms",
        "aws_sse_kms_key_id": os.getenv("KMS_KEY_ARN"),
        "timeout": "60s",
        "allow_http": False
    }
    
    db = lancedb.connect(db_uri, storage_options=storage_options)
    return db

def create_dynamodb_commit_store():
    """Create DynamoDB table for concurrent write coordination."""
    dynamodb = boto3.client("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
    
    try:
        dynamodb.create_table(
            TableName="lancedb-commits",
            KeySchema=[
                {"AttributeName": "base_uri", "KeyType": "HASH"},
                {"AttributeName": "version", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "base_uri", "AttributeType": "S"},
                {"AttributeName": "version", "AttributeType": "N"},
            ],
            BillingMode="PAY_PER_REQUEST",  # Auto-scaling
            StreamSpecification={
                "StreamViewType": "NEW_AND_OLD_IMAGES"
            },
            Tags=[
                {"Key": "Application", "Value": "vector-search"},
                {"Key": "Environment", "Value": "production"}
            ]
        )
        print("DynamoDB table created successfully")
    except Exception as e:
        print(f"Table creation: {e}")

def upsert_vectors_lambda(event, context):
    """Lambda handler for concurrent vector writes."""
    db = initialize_lancedb()
    
    table = db.create_table(
        "documents",
        data=[
            {
                "id": doc["id"],
                "vector": doc["embedding"],
                "text": doc["text"],
                "metadata": doc["metadata"]
            }
            for doc in event["documents"]
        ],
        mode="overwrite"
    )
    
    return {
        "statusCode": 200,
        "body": f"Upserted {len(event['documents'])} vectors"
    }

def query_lambda(event, context):
    """Lambda handler for vector search."""
    db = initialize_lancedb()
    table = db.open_table("documents")
    
    results = table.search(
        event["query_vector"]
    ).limit(10).to_list()
    
    return {
        "statusCode": 200,
        "results": results
    }
```

**Terraform Configuration:**
```hcl
# S3 Bucket for LanceDB
resource "aws_s3_bucket" "lancedb" {
  bucket = "vector-bucket-${data.aws_account_id.current.account_id}"
}

resource "aws_s3_bucket_versioning" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.lancedb.arn
    }
  }
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "lancedb" {
  bucket = aws_s3_bucket.lancedb.id
  name   = "archive"
  status = "Enabled"

  tiering {
    days          = 90
    access_tier   = "ARCHIVE_ACCESS"
  }

  tiering {
    days          = 180
    access_tier   = "DEEP_ARCHIVE_ACCESS"
  }
}

# DynamoDB for concurrent writes
resource "aws_dynamodb_table" "lancedb_commits" {
  name           = "lancedb-commits"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "base_uri"
  range_key      = "version"

  attribute {
    name = "base_uri"
    type = "S"
  }

  attribute {
    name = "version"
    type = "N"
  }

  point_in_time_recovery {
    enabled = true
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }
}

# Lambda IAM Role
resource "aws_iam_role" "lancedb_lambda" {
  name = "lancedb-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "lancedb_s3_access" {
  name = "lancedb-s3-access"
  role = aws_iam_role.lancedb_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.lancedb.arn,
          "${aws_s3_bucket.lancedb.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.lancedb_commits.arn
      },
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.lancedb.arn
      }
    ]
  })
}
```

### Pattern 2: Stateful EKS with EFS Backend

**Architecture:**
```
EKS Pod (LanceDB Application)
  ↓
EFS Mount Point
  └─ /mnt/lancedb (Shared across AZs)
     ↓
CloudWatch Logs
```

**Implementation:**
```yaml
# kubernetes.yml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: lancedb-pv
spec:
  capacity:
    storage: 500Gi
  accessModes:
    - ReadWriteMany
  nfs:
    server: fs-12345678.efs.us-east-1.amazonaws.com
    path: "/"

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: lancedb-pvc
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: ""
  resources:
    requests:
      storage: 500Gi
  volumeName: lancedb-pv

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lancedb-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: lancedb
  template:
    metadata:
      labels:
        app: lancedb
    spec:
      containers:
      - name: app
        image: my-registry/lancedb-app:latest
        env:
        - name: LANCEDB_URI
          value: "/mnt/lancedb"
        - name: LANCEDB_CACHE_SIZE
          value: "1000"
        volumeMounts:
        - name: lancedb-storage
          mountPath: /mnt/lancedb
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
      volumes:
      - name: lancedb-storage
        persistentVolumeClaim:
          claimName: lancedb-pvc
```

---

## RESOURCE REGISTRY ENHANCEMENTS

### New Methods for Qdrant/LanceDB Tracking

```python
# Add to ResourceRegistry class

def log_qdrant_deployment_created(
    self,
    deployment_id: str,
    deployment_type: str,  # "cloud" or "self-hosted"
    url: str,
    region: str,
    source: str = "api"
) -> None:
    """Log Qdrant deployment creation."""
    rec = {
        "id": deployment_id,
        "type": deployment_type,
        "url": url,
        "region": region,
        "source": source,
        "status": "created",
        "created_at": _utc_now_iso(),
    }
    with self._lock:
        data = self._read()
        data.setdefault("qdrant_deployments", [])
        data["qdrant_deployments"].append(rec)
        self._write(data)

def log_qdrant_collection_created(
    self,
    deployment_id: str,
    collection_name: str,
    vector_dimension: int,
    distance_metric: str,
    source: str = "api"
) -> None:
    """Log Qdrant collection creation."""
    rec = {
        "deployment_id": deployment_id,
        "name": collection_name,
        "dimension": vector_dimension,
        "distance_metric": distance_metric,
        "source": source,
        "status": "created",
        "created_at": _utc_now_iso(),
    }
    with self._lock:
        data = self._read()
        data.setdefault("qdrant_collections", [])
        data["qdrant_collections"].append(rec)
        self._write(data)

def log_lancedb_instance_created(
    self,
    instance_id: str,
    backend_type: str,  # "s3", "efs", "ebs", "local"
    backend_uri: str,
    region: str,
    source: str = "api"
) -> None:
    """Log LanceDB instance creation."""
    rec = {
        "id": instance_id,
        "backend_type": backend_type,
        "backend_uri": backend_uri,
        "region": region,
        "source": source,
        "status": "created",
        "created_at": _utc_now_iso(),
    }
    with self._lock:
        data = self._read()
        data.setdefault("lancedb_instances", [])
        data["lancedb_instances"].append(rec)
        self._write(data)

def log_lancedb_table_created(
    self,
    instance_id: str,
    table_name: str,
    vector_dimension: int,
    row_count: int = 0,
    source: str = "api"
) -> None:
    """Log LanceDB table creation."""
    rec = {
        "instance_id": instance_id,
        "name": table_name,
        "dimension": vector_dimension,
        "row_count": row_count,
        "source": source,
        "status": "created",
        "created_at": _utc_now_iso(),
    }
    with self._lock:
        data = self._read()
        data.setdefault("lancedb_tables", [])
        data["lancedb_tables"].append(rec)
        self._write(data)
```

---

## COST COMPARISON

### Scenario: 10M Vector Storage with 1K QPS

**Qdrant Cloud:**
- Managed service: $50/month
- API calls: Included
- Support: Email
- Total: $50/month

**Qdrant on ECS:**
- m5.xlarge: $140/month
- EBS gp3 (100GB, 5000 IOPS): $30/month
- Data transfer: $15/month
- CloudWatch: $5/month
- Total: $190/month

**LanceDB on S3:**
- S3 storage (50GB): $1.15/month
- DynamoDB (pay-per-request): $5/month
- Lambda (1M requests/day): $20/month
- Data transfer: $10/month
- Total: $36.15/month

**LanceDB on EFS:**
- EFS storage (50GB): $5/month
- EC2 compute (t3.xlarge): $60/month
- Data transfer: $10/month
- CloudWatch: $5/month
- Total: $80/month

**Winner:** LanceDB on S3 for cost, Qdrant Cloud for simplicity.

---

## MONITORING & ALERTING

```python
import boto3
from datetime import datetime

def setup_cloudwatch_monitoring():
    """Setup monitoring for vector stores."""
    
    cloudwatch = boto3.client("cloudwatch")
    
    # Qdrant monitoring
    cloudwatch.put_metric_alarm(
        AlarmName="qdrant-collection-size-high",
        MetricName="CollectionSize",
        Namespace="Qdrant",
        Statistic="Average",
        Period=300,
        EvaluationPeriods=2,
        Threshold=1000000,  # 1M vectors
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=["arn:aws:sns:region:account:alerts"]
    )
    
    # LanceDB monitoring
    cloudwatch.put_metric_alarm(
        AlarmName="lancedb-s3-cost-high",
        MetricName="EstimatedCharges",
        Namespace="AWS/Billing",
        Statistic="Maximum",
        Period=86400,
        EvaluationPeriods=1,
        Threshold=100,  # $100/month
        ComparisonOperator="GreaterThanThreshold"
    )
```

