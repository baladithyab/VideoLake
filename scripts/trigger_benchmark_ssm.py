import subprocess
import base64
import json
import sys

# TODO: Fetch this dynamically from Terraform output
# For now, this script needs to be updated to look up the instance by tag or use the new platform instance ID
INSTANCE_ID = "i-023372b93ac8bdf0e"

BUCKET = "videolake-vectors"
S3_PREFIX = "benchmark-scripts"

def upload_to_s3(local_path, s3_key):
    cmd = ["aws", "s3", "cp", local_path, f"s3://{BUCKET}/{s3_key}"]
    print(f"Uploading {local_path} to s3://{BUCKET}/{s3_key}...")
    subprocess.run(cmd, check=True)

print("Uploading scripts to S3...")
upload_to_s3("requirements-benchmark.txt", f"{S3_PREFIX}/requirements-benchmark.txt")
upload_to_s3("scripts/run_quick_health_index_and_benchmark.sh", f"{S3_PREFIX}/run_quick_health_index_and_benchmark.sh")
upload_to_s3("scripts/backend_adapters.py", f"{S3_PREFIX}/backend_adapters.py")
upload_to_s3("scripts/index_embeddings.py", f"{S3_PREFIX}/index_embeddings.py")
upload_to_s3("scripts/benchmark_backend.py", f"{S3_PREFIX}/benchmark_backend.py")

commands = [
    "sudo yum install -y git python3-pip",
    "export AWS_DEFAULT_REGION=us-east-1",
    "export AWS_REGION=us-east-1",
    "cd /home/ec2-user",
    "rm -rf S3Vector S3Vector-react-frontend-refactor",
    "wget https://github.com/baladithyab/S3Vector/archive/refs/heads/react-frontend-refactor.zip -O repo.zip",
    "unzip -o repo.zip",
    "mv VideoLake-react-frontend-refactor S3Vector",
    "cd S3Vector",
    # Download from S3
    f"aws s3 cp s3://{BUCKET}/{S3_PREFIX}/requirements-benchmark.txt requirements-benchmark.txt",
    f"aws s3 cp s3://{BUCKET}/{S3_PREFIX}/run_quick_health_index_and_benchmark.sh scripts/run_quick_health_index_and_benchmark.sh",
    f"aws s3 cp s3://{BUCKET}/{S3_PREFIX}/backend_adapters.py scripts/backend_adapters.py",
    f"aws s3 cp s3://{BUCKET}/{S3_PREFIX}/index_embeddings.py scripts/index_embeddings.py",
    f"aws s3 cp s3://{BUCKET}/{S3_PREFIX}/benchmark_backend.py scripts/benchmark_backend.py",
    
    "touch scripts/__init__.py",
    "chmod +x scripts/run_quick_health_index_and_benchmark.sh",
    "python3 -m venv venv",
    "source venv/bin/activate",
    "pip3 install -r requirements-benchmark.txt qdrant-client opensearch-py PyYAML",
    "export PYTHONPATH=$PYTHONPATH:.",
    "./scripts/run_quick_health_index_and_benchmark.sh"
]

# Join commands into a single string for the SSM parameter
command_str = ' && '.join(commands)

# Construct the AWS CLI command
aws_cmd = [
    "aws", "ssm", "send-command",
    "--instance-ids", INSTANCE_ID,
    "--document-name", "AWS-RunShellScript",
    "--parameters", f'commands=["{command_str}"]'
]

print("Sending SSM command...")
result = None
try:
    result = subprocess.run(aws_cmd, capture_output=True, text=True, check=True)
    output = json.loads(result.stdout)
    command_id = output["Command"]["CommandId"]
    print(f"Command sent successfully. Command ID: {command_id}")
except subprocess.CalledProcessError as e:
    print(f"Error sending command: {e.stderr}")
    sys.exit(1)
except json.JSONDecodeError:
    # result is bound if we reached json.loads
    stdout = result.stdout if result else "No output captured"
    print(f"Error decoding JSON output: {stdout}")
    sys.exit(1)
except Exception as e:
    print(f"An unexpected error occurred: {e}")
    sys.exit(1)