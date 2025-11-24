# VideoLake Demo and Benchmark Guide

This guide provides instructions on how to set up the VideoLake demo and run benchmarks.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Terraform installed
- Python 3.8+ installed
- Git installed

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/baladithyab/S3Vector.git
    cd S3Vector
    ```

2.  **Initialize Terraform:**

    ```bash
    cd terraform
    terraform init
    ```

3.  **Deploy Infrastructure:**

    ```bash
    terraform apply -auto-approve
    ```

    This will deploy the necessary AWS resources, including EC2 instances, ECS clusters, and S3 buckets.

## Running Benchmarks

### Embedded LanceDB Benchmark

1.  **Get the Benchmark Runner Instance ID:**

    ```bash
    INSTANCE_ID=$(terraform output -raw lancedb_benchmark_runner_id)
    ```

2.  **Run the Benchmark Script:**

    You can run the benchmark script directly on the EC2 instance using AWS SSM.

    ```bash
    aws ssm send-command \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[\"cd /home/ec2-user/S3Vector && python3 scripts/run_embedded_benchmark.py --verify\"]" \
        --output text
    ```

    To run the full benchmark (not just verification), remove the `--verify` flag.

3.  **Retrieve Results:**

    The benchmark results are saved to `benchmark-results/embedded_lancedb_verify.json` on the instance. You can upload them to S3 and then download them locally.

    ```bash
    # Upload to S3
    aws ssm send-command \
        --instance-ids "$INSTANCE_ID" \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[\"aws s3 cp /home/ec2-user/S3Vector/benchmark-results/embedded_lancedb_verify.json s3://videolake-vectors/benchmark-results/embedded_lancedb_verify.json\"]" \
        --output text

    # Download from S3
    aws s3 cp s3://videolake-vectors/benchmark-results/embedded_lancedb_verify.json benchmark-results/embedded_lancedb_verify.json
    ```

## Running the Demo

(Instructions for running the demo will be added here once the demo infrastructure is fully configured.)

## Teardown

To destroy the infrastructure and avoid incurring costs:

```bash
cd terraform
terraform destroy -auto-approve