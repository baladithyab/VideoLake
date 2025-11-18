import subprocess
import json
import sys
import os
import time

INSTANCE_ID = "i-023372b93ac8bdf0e"
REMOTE_DIR = "/home/ec2-user/S3Vector/logs"
LOCAL_DIR = "benchmark-results/ec2-embedded"

files_to_retrieve = [
    "quick_benchmark_lancedb-efs_20251118_205708.json",
    "quick_benchmark_lancedb-embedded_20251118_205708.json",
    "quick_benchmark_lancedb-s3_20251118_205708.json",
    "quick_benchmark_qdrant-efs_20251118_205708.json",
    "quick_benchmark_s3vector_20251118_205708.json",
    "quick_health_20251118_205708.json",
    "quick_health_index_benchmark_20251118_205708.log"
]

def get_file_content(filename):
    cmd = [
        "aws", "ssm", "send-command",
        "--instance-ids", INSTANCE_ID,
        "--document-name", "AWS-RunShellScript",
        "--parameters", f'commands=["cat {REMOTE_DIR}/{filename}"]'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        command_id = output["Command"]["CommandId"]
        
        # Wait for command to complete
        time.sleep(2)
        
        cmd_status = [
            "aws", "ssm", "list-command-invocations",
            "--command-id", command_id,
            "--details"
        ]
        
        for _ in range(10):
            result_status = subprocess.run(cmd_status, capture_output=True, text=True, check=True)
            output_status = json.loads(result_status.stdout)
            invocations = output_status.get("CommandInvocations", [])
            if invocations:
                status = invocations[0]["Status"]
                if status in ["Success", "Failed"]:
                    if status == "Success":
                        return invocations[0]["CommandPlugins"][0]["Output"]
                    else:
                        print(f"Failed to retrieve {filename}: {invocations[0]['CommandPlugins'][0]['Output']}")
                        return None
            time.sleep(2)
            
        print(f"Timeout waiting for {filename}")
        return None
        
    except Exception as e:
        print(f"Error retrieving {filename}: {e}")
        return None

if not os.path.exists(LOCAL_DIR):
    os.makedirs(LOCAL_DIR)

for filename in files_to_retrieve:
    print(f"Retrieving {filename}...")
    content = get_file_content(filename)
    if content:
        local_path = os.path.join(LOCAL_DIR, filename)
        with open(local_path, "w") as f:
            f.write(content)
        print(f"Saved to {local_path}")