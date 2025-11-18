# Benchmark SSM Execution Guide

This guide explains how to trigger the benchmark suite on the EC2 instance using AWS Systems Manager (SSM). This method ensures that benchmarks run **in-region (us-east-1)**, avoiding cross-region latency artifacts.

## Prerequisites

1.  **AWS CLI**: Ensure you have the AWS CLI installed and configured with credentials that have permission to `ssm:SendCommand`.
2.  **EC2 Instance ID**: You need the Instance ID of the benchmark EC2 instance (e.g., `i-023372b93ac8bdf0e`). You can find this in the Terraform outputs or AWS Console.

## Triggering the Benchmark

We have a helper script `scripts/trigger_benchmark_ssm.py` that automates the process. It:
1.  Reads the local `requirements-benchmark.txt` and `scripts/run_quick_health_index_and_benchmark.sh`.
2.  Encodes them to Base64.
3.  Constructs a shell command to:
    *   Clone the repo (or update it).
    *   Decode and write the latest script/requirements files to the instance.
    *   Set up a virtual environment.
    *   Install dependencies.
    *   Run the benchmark script.
4.  Sends this command to the EC2 instance via SSM.

### Usage

Run the python script from the project root:

```bash
python3 scripts/trigger_benchmark_ssm.py
```

**Note:** You may need to update the `INSTANCE_ID` variable in `scripts/trigger_benchmark_ssm.py` if the instance ID changes.

### Manual Trigger (AWS CLI)

If you prefer to run the command manually using the AWS CLI, you can use `aws ssm send-command`.

**Simple Command (Run existing script on instance):**

```bash
aws ssm send-command \
    --instance-ids "i-023372b93ac8bdf0e" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["cd /home/ec2-user/S3Vector && git pull && ./scripts/run_quick_health_index_and_benchmark.sh"]' \
    --region us-east-1
```

**Full Command (replicates the Python script logic):**

*Note: This is complex to type manually due to file encoding. Use the Python script for full deployment.*

## Retrieving Results

The benchmark script writes results to `/home/ec2-user/S3Vector/logs/` on the instance.
You can retrieve them using `scripts/retrieve_benchmark_results.py` (if implemented) or by SSH-ing into the instance (if SSH is open) or using SSM Session Manager.

**Using SSM Session Manager to view logs:**

1.  Go to AWS Console > Systems Manager > Session Manager.
2.  Start a session with the benchmark instance.
3.  Navigate to the logs directory:
    ```bash
    cd /home/ec2-user/S3Vector/logs
    ls -l
    cat quick_health_index_benchmark_*.log
    ```

## Verifying In-Region Execution

The scripts now explicitly set `AWS_DEFAULT_REGION=us-east-1` to ensure all SDK calls (S3Vector, etc.) originate from the correct region.