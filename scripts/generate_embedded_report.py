import json
import glob
import os
import pandas as pd

RESULTS_DIR = "benchmark-results/ec2-embedded"
TIMESTAMP = "20251118_223647"

def load_results():
    results = []
    pattern = os.path.join(RESULTS_DIR, f"quick_benchmark_*_{TIMESTAMP}.json")
    for filepath in glob.glob(pattern):
        try:
            with open(filepath) as f:
                data = json.load(f)
                results.append(data)
        except Exception as e:
            print(f"Error loading {filepath}: {e}")
    return results

def generate_report(results):
    df = pd.DataFrame(results)
    
    # Select relevant columns
    cols = [
        "backend", 
        "throughput_qps", 
        "latency_p50_ms", 
        "latency_p95_ms", 
        "latency_p99_ms",
        "successful_queries",
        "query_count"
    ]
    
    # Filter for existing columns
    cols = [c for c in cols if c in df.columns]
    
    df = df[cols].sort_values("throughput_qps", ascending=False)
    
    report = f"# Embedded Benchmark Report ({TIMESTAMP})\n\n"
    report += "## Summary\n\n"
    report += df.to_markdown(index=False, floatfmt=".2f")
    report += "\n\n"
    
    report += "## Detailed Results\n\n"
    for res in results:
        report += f"### {res.get('backend')}\n"
        report += f"- **Throughput:** {res.get('throughput_qps', 0):.2f} QPS\n"
        report += f"- **P50 Latency:** {res.get('latency_p50_ms', 0):.2f} ms\n"
        report += f"- **P95 Latency:** {res.get('latency_p95_ms', 0):.2f} ms\n"
        report += f"- **P99 Latency:** {res.get('latency_p99_ms', 0):.2f} ms\n"
        report += f"- **Success Rate:** {res.get('successful_queries', 0)}/{res.get('query_count', 0)}\n"
        if 'endpoint_info' in res:
            report += f"- **Endpoint Info:**\n"
            report += f"```json\n{json.dumps(res['endpoint_info'], indent=2)}\n```\n"
        report += "\n"
        
    output_path = os.path.join(RESULTS_DIR, f"summary_report_{TIMESTAMP}.md")
    with open(output_path, "w") as f:
        f.write(report)
    
    print(f"Report generated at {output_path}")
    print(report)

if __name__ == "__main__":
    results = load_results()
    if results:
        generate_report(results)
    else:
        print("No results found.")