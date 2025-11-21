import time
import requests
import sys
import json

ALB_URL = "http://videolake-alb-1462909988.us-east-1.elb.amazonaws.com"
JOB_ID = "f248a71b-2828-4d17-9244-0efdabb46083"

def check_status():
    url = f"{ALB_URL}/api/benchmark/status/{JOB_ID}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def main():
    print(f"Waiting for benchmark job {JOB_ID} to complete...")
    while True:
        status_data = check_status()
        if status_data:
            status = status_data.get("status")
            print(f"Status: {status}")
            
            if status == "completed":
                print("Benchmark completed!")
                print(json.dumps(status_data, indent=2))
                break
            elif status == "failed":
                print("Benchmark failed!")
                print(json.dumps(status_data, indent=2))
                break
        
        time.sleep(5)

if __name__ == "__main__":
    main()