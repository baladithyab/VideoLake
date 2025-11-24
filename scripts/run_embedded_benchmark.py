import os
import json
import time
import lancedb
import numpy as np
import argparse
from datetime import datetime

def run_benchmark(verify=False):
    print("Starting embedded LanceDB benchmark...")
    
    # Configuration
    db_path = "/tmp/lancedb_benchmark_data"
    table_name = "vectors"
    dim = 1536
    num_vectors = 1000 if verify else 10000
    num_queries = 50
    
    # Ensure directory exists
    os.makedirs(db_path, exist_ok=True)
    
    # Connect to LanceDB
    db = lancedb.connect(db_path)
    
    # Create data
    print(f"Generating {num_vectors} vectors of dimension {dim}...")
    data = []
    for i in range(num_vectors):
        vector = np.random.rand(dim).astype(np.float32).tolist()
        data.append({"id": i, "vector": vector, "text": f"sample text {i}"})
    
    # Create table
    print(f"Creating table '{table_name}'...")
    if table_name in db.table_names():
        db.drop_table(table_name)
    
    tbl = db.create_table(table_name, data)
    
    # Run queries
    print(f"Running {num_queries} queries...")
    start_time = time.time()
    successful_queries = 0
    
    for i in range(num_queries):
        query_vector = np.random.rand(dim).astype(np.float32).tolist()
        try:
            tbl.search(query_vector).limit(10).to_list()
            successful_queries += 1
        except Exception as e:
            print(f"Query failed: {e}")
            
    end_time = time.time()
    duration = end_time - start_time
    qps = successful_queries / duration if duration > 0 else 0
    
    # Prepare results
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "successful_queries": successful_queries,
        "throughput_qps": qps,
        "endpoint_info": {
            "type": "embedded",
            "path": db_path
        },
        "config": {
            "num_vectors": num_vectors,
            "num_queries": num_queries,
            "dimension": dim
        }
    }
    
    # Save results
    output_dir = "benchmark-results"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "embedded_lancedb_verify.json")
    
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
        
    print(f"Benchmark complete. Results saved to {output_file}")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run embedded LanceDB benchmark")
    parser.add_argument("--verify", action="store_true", help="Run a quick verification test")
    args = parser.parse_args()
    
    run_benchmark(verify=args.verify)