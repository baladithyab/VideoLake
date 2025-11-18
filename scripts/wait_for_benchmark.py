import subprocess
import json
import sys
import time

COMMAND_ID = "08a0cb65-201a-417d-973b-e25f2c79eab5"

def check_status():
    cmd = [
        "aws", "ssm", "list-command-invocations",
        "--command-id", COMMAND_ID,
        "--details"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = json.loads(result.stdout)
        invocations = output.get("CommandInvocations", [])
        if invocations:
            status = invocations[0]["Status"]
            print(f"Status: {status}")
            if status in ["Success", "Failed", "Cancelled", "TimedOut"]:
                return status, invocations[0]["CommandPlugins"][0]["Output"]
            return status, None
        return "Unknown", None
    except Exception as e:
        print(f"Error checking status: {e}")
        return "Error", None

print(f"Waiting for command {COMMAND_ID} to complete...")
while True:
    status, output = check_status()
    if status in ["Success", "Failed", "Cancelled", "TimedOut"]:
        print(f"Command finished with status: {status}")
        if output:
            print("Output:")
            print(output[-5000:]) # Print last 5000 chars
        break
    time.sleep(10)