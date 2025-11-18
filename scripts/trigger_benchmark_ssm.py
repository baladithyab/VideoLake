import subprocess
import base64
import json
import sys

INSTANCE_ID = "i-023372b93ac8bdf0e"

def read_and_encode(filepath):
    try:
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: File {filepath} not found.")
        sys.exit(1)

print("Reading and encoding files...")
requirements_b64 = read_and_encode("requirements-benchmark.txt")
script_b64 = read_and_encode("scripts/run_quick_health_index_and_benchmark.sh")

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
    f"echo '{requirements_b64}' | base64 -d > requirements-benchmark.txt",
    f"echo '{script_b64}' | base64 -d > scripts/run_quick_health_index_and_benchmark.sh",
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