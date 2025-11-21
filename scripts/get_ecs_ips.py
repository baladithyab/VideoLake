import boto3
import json

def get_task_ip(cluster_name):
    ecs = boto3.client('ecs', region_name='us-east-1')
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    try:
        tasks = ecs.list_tasks(cluster=cluster_name)
        if not tasks['taskArns']:
            return None
            
        task_desc = ecs.describe_tasks(cluster=cluster_name, tasks=tasks['taskArns'])
        if not task_desc['tasks']:
            return None
            
        task = task_desc['tasks'][0]
        eni_id = None
        for attachment in task['attachments']:
            if attachment['type'] == 'ElasticNetworkInterface':
                for detail in attachment['details']:
                    if detail['name'] == 'networkInterfaceId':
                        eni_id = detail['value']
                        break
        
        if eni_id:
            eni_desc = ec2.describe_network_interfaces(NetworkInterfaceIds=[eni_id])
            if eni_desc['NetworkInterfaces']:
                public_ip = eni_desc['NetworkInterfaces'][0].get('Association', {}).get('PublicIp')
                private_ip = eni_desc['NetworkInterfaces'][0].get('PrivateIpAddress')
                return {'public': public_ip, 'private': private_ip}
                
    except Exception as e:
        print(f"Error getting IP for {cluster_name}: {e}")
        return None

clusters = [
    "videolake-lancedb-s3-cluster",
    "videolake-lancedb-efs-cluster",
    "videolake-qdrant-cluster"
]

results = {}
for cluster in clusters:
    ip_info = get_task_ip(cluster)
    if ip_info:
        print(f"{cluster}: {ip_info}")
        results[cluster] = ip_info
    else:
        print(f"{cluster}: No running tasks found")
