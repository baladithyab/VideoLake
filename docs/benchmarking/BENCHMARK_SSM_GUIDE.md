# Remote Benchmarking with AWS Systems Manager (SSM)

This guide documents the workflow for running benchmarks remotely on an EC2 instance in `us-east-1`. This approach eliminates cross-region latency issues by running the benchmark client in the same region as the vector database infrastructure.

## Architecture Overview

The workflow consists of three main stages:
1.  **Infrastructure**: A dedicated EC2 instance (`lancedb-benchmark-runner`) deployed via Terraform.
2.  **Trigger**: A local Python script uploads benchmark scripts to S3 and triggers execution on the EC2 instance via AWS SSM.
3.  **Retrieval**: A local Python script (or manual process) retrieves the JSON result files from the EC2 instance.

## Prerequisites

### 1. Infrastructure Deployment
Ensure the `lancedb_benchmark_ec2` module is deployed. This module provisions:
-   **EC2 Instance**: Amazon Linux 2023, `t3.xlarge` (default).
-   **IAM Role**: Grants `AmazonSSMManagedInstanceCore` (for SSM access) and S3 access (for downloading scripts/uploading artifacts).
-   **Security Group**: Allows outbound traffic and SSH (optional).

**To deploy:**
```bash
cd terraform
terraform apply -target=module.lancedb_benchmark_ec2
```

**Note the Instance ID**: After deployment, note the `instance_id` from the Terraform outputs. You will need this for the scripts.

### 2. Local Environment
Ensure you have the following installed locally:
-   AWS CLI configured with appropriate credentials.
-   Python 3.x with `boto3` installed.

## Execution Workflow

### Step 1: Trigger Benchmarks

Use the `scripts/trigger_benchmark_ssm.py` script to start the benchmark process.

**What this script does:**
1.  Uploads necessary scripts (`run_all_benchmarks_custom.sh`, `benchmark_backend.py`, etc.) and `requirements-benchmark.txt` to the `videolake-vectors` S3 bucket.
2.  Sends an SSM `AWS-RunShellScript` command to the target instance.
3.  The remote instance downloads the scripts, sets up a virtual environment, installs dependencies, and runs the benchmarks.

**Configuration:**
Open `scripts/trigger_benchmark_ssm.py` and ensure the `INSTANCE_ID` variable matches your deployed benchmark runner instance.

```python
# scripts/trigger_benchmark_ssm.py
INSTANCE_ID = "i-0xxxx..." # Update this
```

**Run the trigger:**
```bash
python3 scripts/trigger_benchmark_ssm.py
```

**Output:**
The script will output a **Command ID**. Save this ID if you want to track status via AWS CLI, though the script usually returns immediately after sending the command.

### Step 2: Monitor Progress (Optional)

Since the benchmark runs asynchronously on the remote instance, you can check the status in the AWS Console under **Systems Manager > Run Command**, or use the AWS CLI:

```bash
aws ssm list-command-invocations --command-id <COMMAND_ID> --details
```

### Step 3: Retrieve Results

Once the benchmarks are complete (usually takes 5-10 minutes depending on the number of queries), retrieve the results.

#### Option A: Automated Retrieval
Use the `scripts/retrieve_benchmark_results.py` script.

**Configuration:**
Open `scripts/retrieve_benchmark_results.py` and update:
-   `INSTANCE_ID`: Your benchmark runner instance ID.
-   `REMOTE_DIR`: Default is `/home/ec2-user/S3Vector/logs` or wherever the script outputs results (check `run_all_benchmarks_custom.sh` output path). *Note: The current setup outputs to a timestamped directory, so you may need to update the script to point to the specific directory or modify the runner to use a fixed path.*

```bash
python3 scripts/retrieve_benchmark_results.py
```

#### Option B: Manual Retrieval (SSM Session Manager)
If you need to explore the results or if the automatic retrieval misses files:

1.  **Connect to the instance**:
    ```bash
    aws ssm start-session --target <INSTANCE_ID>
    ```
2.  **Navigate to results**:
    ```bash
    cd /home/ec2-user/S3Vector/benchmark-results
    ls -R
    ```
3.  **View or Copy content**:
    You can `cat` the files to copy the JSON content, or upload them to S3 for easy download:
    ```bash
    # On the remote instance
    aws s3 cp --recursive benchmark-results/ s3://videolake-vectors/results/my-run/
    ```
    Then download locally:
    ```bash
    # On your local machine
    aws s3 cp --recursive s3://videolake-vectors/results/my-run/ ./local-results/
    ```

## Troubleshooting

### Instance Not Appearing in SSM
-   **Wait**: It can take up to 5-10 minutes for a new instance to register with SSM.
-   **Check IAM Role**: Ensure the instance has the `AmazonSSMManagedInstanceCore` policy attached.
-   **Check Agent**: The SSM Agent is installed by default on Amazon Linux 2023. If using a different AMI, ensure the agent is installed.

### "Access Denied" for S3
-   Ensure the IAM role attached to the EC2 instance has `s3:GetObject` and `s3:ListBucket` permissions for the `videolake-vectors` bucket.

### Benchmark Script Fails
-   **Check Logs**: Connect via SSM Session Manager and check `/var/log/amazon/ssm/amazon-ssm-agent.log` or the standard output logs if redirected.
-   **Manual Run**: Connect via SSM, navigate to `/home/ec2-user/S3Vector`, activate the venv, and run the script manually to see errors:
    ```bash
    source venv/bin/activate
    ./scripts/run_all_benchmarks_custom.sh
    ```

## Key Files

-   `scripts/trigger_benchmark_ssm.py`: Local orchestrator.
-   `scripts/retrieve_benchmark_results.py`: Local result fetcher.
-   `scripts/run_all_benchmarks_custom.sh`: Remote execution script (runs on EC2).
-   `terraform/modules/lancedb_benchmark_ec2/`: Infrastructure definition.