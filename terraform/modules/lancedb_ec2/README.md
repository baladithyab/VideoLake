# LanceDB EC2+EBS Terraform Module

This Terraform module deploys LanceDB API on AWS EC2 with persistent EBS storage. It provides a production-ready, high-performance vector database backend using Docker containers on EC2 with dedicated EBS volumes.

## Architecture

- **EC2 Instance**: Amazon Linux 2023 with Docker
- **Storage**: Dedicated EBS gp3 volume (default: 100GB, 3000 IOPS, 125 MB/s)
- **Container**: LanceDB API from ECR
- **Networking**: Security group with configurable access control
- **Monitoring**: CloudWatch logging and metrics
- **IAM**: Dedicated role with CloudWatch and ECR permissions

## Usage

```hcl
module "lancedb_ec2" {
  source = "./modules/lancedb_ec2"

  deployment_name   = "my-lancedb-prod"
  aws_region        = "us-east-1"
  availability_zone = "us-east-1a"

  # Instance configuration
  instance_type = "t3.xlarge" # 4 vCPU, 16GB RAM

  # Storage configuration
  ebs_volume_size_gb    = 100
  ebs_volume_type       = "gp3"
  ebs_iops              = 3000
  ebs_throughput_mbps   = 125

  # Network security
  allowed_cidr_blocks = ["10.0.0.0/8"]
  enable_ssh          = false

  # Container image
  lancedb_image = "386931836011.dkr.ecr.us-east-1.amazonaws.com/videolake-lancedb-api:latest"

  # Monitoring
  log_retention_days = 7

  tags = {
    Environment = "production"
    Project     = "S3Vector"
  }
}
```

## Outputs

- `endpoint` - LanceDB API HTTP endpoint
- `instance_id` - EC2 instance ID for management
- `security_group_id` - Security group ID for network configuration
- `ebs_volume_id` - EBS volume ID for backup/snapshot operations

## Key Features

### Persistent Storage
- Dedicated EBS volume mounted at `/mnt/lancedb`
- Data persists across instance restarts
- Supports EBS snapshots for backups
- Automatic volume formatting on first boot

### Container Management
- Automatic ECR authentication
- Docker container with restart policy
- Volume-mounted data directory
- Environment variables for LanceDB configuration:
  - `LANCEDB_BACKEND=ebs`
  - `LANCEDB_URI=/mnt/lancedb`

### Security
- Encrypted EBS volume at rest
- Security group with minimal required ports
- IAM role with least-privilege permissions
- Optional SSH access (disabled by default)

### Monitoring
- CloudWatch log group for container logs
- EC2 instance metrics
- CloudWatch agent for custom metrics

## Comparison with Qdrant EC2

This module follows the same pattern as the Qdrant EC2 module:

| Feature | Qdrant EC2 | LanceDB EC2 |
|---------|-----------|-------------|
| Instance Type | t3.xlarge (default) | t3.xlarge (default) |
| Storage | EBS gp3, 100GB | EBS gp3, 100GB |
| IOPS | 3000 | 3000 |
| Throughput | 125 MB/s | 125 MB/s |
| API Port | 6333 (REST), 6334 (gRPC) | 8000 (REST) |
| Mount Point | `/var/lib/qdrant` | `/mnt/lancedb` |
| Container Source | Docker Hub | AWS ECR |

## Requirements

- Terraform >= 1.0
- AWS Provider ~> 5.0
- Valid AWS credentials with EC2, IAM, and CloudWatch permissions
- Access to the LanceDB API ECR repository

## Cost Estimation

Default configuration monthly costs (us-east-1):
- EC2 t3.xlarge: ~$120/month
- EBS 100GB gp3: ~$8/month
- Data transfer: ~$10/month
- **Total: ~$138/month**

## Notes

- The EBS volume is attached as `/dev/xvdf`
- First boot will format the volume if not already formatted
- Container logs are available via `docker logs lancedb-api` on the instance
- The module uses `lifecycle.ignore_changes` for user_data to prevent unnecessary instance recreation

## Maintenance

### Viewing Container Logs
```bash
ssh ec2-user@<instance-ip>
docker logs lancedb-api
docker logs -f lancedb-api  # Follow logs
```

### Restarting the Container
```bash
ssh ec2-user@<instance-ip>
docker restart lancedb-api
```

### EBS Snapshots
Use AWS Console or CLI to create EBS snapshots of the data volume for backups.

## Troubleshooting

1. **Container not starting**: Check `/var/log/lancedb-setup.log` on the instance
2. **Volume not mounting**: Verify EBS volume is attached and `/dev/xvdf` exists
3. **ECR authentication issues**: Check IAM role has ECR read permissions
4. **API not accessible**: Verify security group allows access from your IP/CIDR