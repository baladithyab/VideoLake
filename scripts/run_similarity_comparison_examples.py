#!/usr/bin/env python3
"""
Example usage script for the similarity search comparison tool.

This script demonstrates how to use the similarity search comparison functionality
with various test queries and provides examples of the expected output.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.similarity_search_comparison import SimilaritySearchComparison


def run_example_comparisons():
    """Run several example similarity search comparisons."""
    
    # Initialize the comparison service
    print("🚀 Initializing Similarity Search Comparison Service...")
    comparison_service = SimilaritySearchComparison()
    
    # Define test queries
    test_queries = [
        "machine learning algorithms",
        "artificial intelligence and neural networks", 
        "computer vision and image processing",
        "natural language processing techniques",
        "deep learning models and training"
    ]
    
    print(f"\n📋 Running {len(test_queries)} example comparisons...\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"EXAMPLE {i}/{len(test_queries)}")
        print(f"{'='*60}")
        
        try:
            # Perform the comparison
            results = comparison_service.compare_search_results(
                query_text=query,
                top_k=5  # Get top 5 results for examples
            )
            
            # Print the results
            comparison_service.print_comparison_results(results)
            
            # Brief summary
            if 'error' not in results:
                s3v_latency = results['s3vector'].get('total_latency_ms', 0)
                os_latency = results['opensearch'].get('total_latency_ms', 0)
                s3v_count = results['s3vector'].get('results_count', 0)
                os_count = results['opensearch'].get('results_count', 0)
                
                print(f"\n📊 Quick Summary:")
                print(f"   S3Vector: {s3v_latency:.1f}ms, {s3v_count} results")
                print(f"   OpenSearch: {os_latency:.1f}ms, {os_count} results")
                
                if s3v_latency > 0 and os_latency > 0:
                    faster = "S3Vector" if s3v_latency < os_latency else "OpenSearch"
                    print(f"   Winner: {faster} 🏆")
            
        except Exception as e:
            print(f"❌ Error in example {i}: {e}")
            continue
        
        # Add a pause between examples
        if i < len(test_queries):
            input("\nPress Enter to continue to the next example...")
    
    print(f"\n✅ Completed all {len(test_queries)} example comparisons!")


def run_single_comparison_demo():
    """Run a single detailed comparison demo."""
    
    print("🎯 Single Comparison Demo")
    print("="*50)
    
    # Initialize the comparison service
    comparison_service = SimilaritySearchComparison()
    
    # Demo query
    demo_query = "machine learning algorithms for data analysis"
    
    print(f"Query: '{demo_query}'")
    print("Performing comparison...")
    
    try:
        results = comparison_service.compare_search_results(
            query_text=demo_query,
            top_k=10
        )
        
        comparison_service.print_comparison_results(results)
        
        # Additional analysis
        if 'error' not in results:
            print("\n🔍 Detailed Analysis:")
            
            # Embedding info
            print(f"• Embedding Model: Marengo 2.7 (twelvelabs.marengo-embed-2-7-v1:0)")
            print(f"• Vector Dimensions: {results['query_vector_dimensions']}")
            print(f"• Embedding Generation: {results['embedding_generation_ms']:.2f}ms")
            
            # Index comparison
            s3v_results = results['s3vector']
            os_results = results['opensearch']
            
            if 'error' not in s3v_results and 'error' not in os_results:
                print(f"\n• S3Vector Index:")
                print(f"  - Query Time: {s3v_results.get('query_latency_ms', 0):.2f}ms")
                print(f"  - Total Time: {s3v_results.get('total_latency_ms', 0):.2f}ms")
                print(f"  - Results: {s3v_results.get('results_count', 0)}")
                
                print(f"\n• OpenSearch Index:")
                print(f"  - Query Time: {os_results.get('query_latency_ms', 0):.2f}ms")
                print(f"  - Total Time: {os_results.get('total_latency_ms', 0):.2f}ms")
                print(f"  - Results: {os_results.get('results_count', 0)}")
                
                # Performance comparison
                comparison = results.get('comparison', {})
                print(f"\n• Performance:")
                print(f"  - Faster Index: {comparison.get('faster_index', 'N/A')}")
                print(f"  - Latency Difference: {comparison.get('latency_difference_ms', 0):.2f}ms")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")


def show_usage_examples():
    """Show command-line usage examples."""
    
    print("📚 Command-Line Usage Examples")
    print("="*50)
    
    script_path = "scripts/similarity_search_comparison.py"
    
    examples = [
        {
            "description": "Basic search comparison",
            "command": f'python {script_path} "machine learning algorithms"'
        },
        {
            "description": "Search with custom top-k results",
            "command": f'python {script_path} "neural networks" --top-k 20'
        },
        {
            "description": "Search with output file and verbose logging",
            "command": f'python {script_path} "computer vision" --output-file results.json --verbose'
        },
        {
            "description": "Complex query example",
            "command": f'python {script_path} "deep learning models for natural language processing" --top-k 15'
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}:")
        print(f"   {example['command']}")
    
    print(f"\n💡 Tips:")
    print(f"   • Use quotes around multi-word queries")
    print(f"   • The --output-file option saves detailed JSON results")
    print(f"   • Use --verbose for detailed logging information")
    print(f"   • Results show both S3Vector and OpenSearch performance")


def main():
    """Main function with interactive menu."""
    
    print("🔍 Similarity Search Comparison Examples")
    print("="*60)
    
    while True:
        print("\nChoose an option:")
        print("1. Run single comparison demo")
        print("2. Run multiple example comparisons")
        print("3. Show command-line usage examples")
        print("4. Exit")
        
        try:
            choice = input("\nEnter your choice (1-4): ").strip()
            
            if choice == "1":
                run_single_comparison_demo()
            elif choice == "2":
                run_example_comparisons()
            elif choice == "3":
                show_usage_examples()
            elif choice == "4":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
