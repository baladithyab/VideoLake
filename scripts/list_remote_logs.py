import subprocess
import json
import sys
import time

INSTANCE_ID = "i-023372b93ac8bdf0e"
REMOTE_DIR = "/home/ec2-user/S3Vector/logs"

def list_files():
    cmd = [
        "aws", "ssm", "send-command",
        "--instance-ids", INSTANCE_ID,
        "--document-name", "AWS-RunShellScript",
        "--parameters", f'commands=["ls -1 {REMOTE_DIR}"]'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        command_id = output["Command"]["CommandId"]
        
        print(f"Command sent. ID: {command_id}")
        
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
                        print(f"Failed to list files: {invocations[0]['CommandPlugins'][0]['Output']}")
                        return None
            time.sleep(2)
            
        print("Timeout waiting for file list")
        return None
        
    except Exception as e:
        print(f"Error listing files: {e}")
        return None

if __name__ == "__main__":
    files = list_files()
    if files:
        print("\nFiles in remote log directory:")
        print(files)