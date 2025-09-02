#!/usr/bin/env python3
"""
List OpenSearch Integration Resources

This script helps users track and manage OpenSearch resources created by the
S3Vector integration system, including collections, domains, pipelines, and IAM roles.

Usage:
    python scripts/list_opensearch_resources.py --summary
    python scripts/list_opensearch_resources.py --detailed
    python scripts/list_opensearch_resources.py --cleanup --confirm
    python scripts/list_opensearch_resources.py --export-pattern --cleanup
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.resource_registry import resource_registry
from src.services.opensearch_integration import OpenSearchIntegrationManager
from src.utils.logging_config import setup_logging, get_structured_logger


class OpenSearchResourceManager:
    """Manages OpenSearch integration resources and provides cleanup utilities."""
    
    def __init__(self):
        setup_logging()
        self.logger = get_structured_logger(__name__)
        self.integration_manager = OpenSearchIntegrationManager()
    
    def print_summary(self) -> None:
        """Print a summary of OpenSearch resources."""
        try:
            summary = self.integration_manager.get_opensearch_resource_summary()
            
            print("="*80)
            print("OPENSEARCH INTEGRATION RESOURCE SUMMARY")
            print("="*80)
            
            # Overall summary
            overall = summary['summary']
            print(f"\nOverall Resource Counts:")
            print(f"  S3 Buckets: {overall['s3_buckets']}")
            print(f"  Vector Buckets: {overall['vector_buckets']}")
            print(f"  Vector Indexes: {overall['vector_indexes']}")
            print(f"  OpenSearch Collections: {overall['opensearch_collections']}")
            print(f"  OpenSearch Domains: {overall['opensearch_domains']}")
            print(f"  OpenSearch Pipelines: {overall['opensearch_pipelines']}")
            print(f"  OpenSearch Indexes: {overall['opensearch_indexes']}")
            print(f"  IAM Roles: {overall['iam_roles']}")
            
            # Active resources
            active = overall.get('active_resources', {})
            print(f"\nActive Selections:")
            print(f"  Vector Index ARN: {active.get('index_arn', 'None')}")
            print(f"  Vector Bucket: {active.get('vector_bucket', 'None')}")
            print(f"  OpenSearch Collection: {active.get('opensearch_collection', 'None')}")
            print(f"  OpenSearch Domain: {active.get('opensearch_domain', 'None')}")
            
            # Integration patterns
            patterns = summary['integration_patterns']
            print(f"\nIntegration Pattern Usage:")
            print(f"  Export Pattern Resources: {patterns['export_resources']}")
            print(f"  Engine Pattern Resources: {patterns['engine_resources']}")
            
            print(f"\nLast Updated: {overall.get('last_updated', 'Unknown')}")
            print("="*80)
            
        except Exception as e:
            print(f"❌ Failed to get resource summary: {e}")
    
    def print_detailed_resources(self) -> None:
        """Print detailed information about all OpenSearch resources."""
        try:
            summary = self.integration_manager.get_opensearch_resource_summary()
            details = summary['opensearch_details']
            
            print("="*80)
            print("DETAILED OPENSEARCH RESOURCE LISTING")
            print("="*80)
            
            # OpenSearch Serverless Collections
            collections = details['collections']
            print(f"\n📦 OpenSearch Serverless Collections ({collections['active']}/{collections['total']} active):")
            if collections['resources']:
                for collection in collections['resources']:
                    print(f"  • {collection['name']}")
                    print(f"    ARN: {collection.get('arn', 'N/A')}")
                    print(f"    Region: {collection.get('region', 'N/A')}")
                    print(f"    Type: {collection.get('type', 'N/A')}")
                    print(f"    Created: {collection.get('created_at', 'N/A')}")
                    print(f"    Source: {collection.get('source', 'N/A')}")
                    print()
            else:
                print("    No active collections found.")
            
            # OpenSearch Domains
            domains = details['domains']
            print(f"\n🏛️ OpenSearch Domains ({domains['active']}/{domains['total']} active):")
            if domains['resources']:
                for domain in domains['resources']:
                    print(f"  • {domain['name']}")
                    print(f"    ARN: {domain.get('arn', 'N/A')}")
                    print(f"    Region: {domain.get('region', 'N/A')}")
                    print(f"    Engine Version: {domain.get('engine_version', 'N/A')}")
                    print(f"    S3 Vectors Enabled: {domain.get('s3_vectors_enabled', False)}")
                    print(f"    Created: {domain.get('created_at', 'N/A')}")
                    print(f"    Source: {domain.get('source', 'N/A')}")
                    print()
            else:
                print("    No active domains found.")
            
            # OpenSearch Ingestion Pipelines
            pipelines = details['pipelines']
            print(f"\n🔄 OpenSearch Ingestion Pipelines ({pipelines['active']}/{pipelines['total']} active):")
            if pipelines['resources']:
                for pipeline in pipelines['resources']:
                    print(f"  • {pipeline['name']}")
                    print(f"    ARN: {pipeline.get('arn', 'N/A')}")
                    print(f"    Source Index: {pipeline.get('source_index_arn', 'N/A')}")
                    print(f"    Target Collection: {pipeline.get('target_collection', 'N/A')}")
                    print(f"    Region: {pipeline.get('region', 'N/A')}")
                    print(f"    Created: {pipeline.get('created_at', 'N/A')}")
                    print(f"    Source: {pipeline.get('source', 'N/A')}")
                    print()
            else:
                print("    No active pipelines found.")
            
            # OpenSearch Indexes
            indexes = details['indexes']
            print(f"\n📊 OpenSearch Indexes with S3 Vector Engine ({indexes['active']}/{indexes['total']} active):")
            if indexes['resources']:
                for index in indexes['resources']:
                    print(f"  • {index['name']}")
                    print(f"    Endpoint: {index.get('endpoint', 'N/A')}")
                    print(f"    Vector Field: {index.get('vector_field', 'N/A')}")
                    print(f"    Dimensions: {index.get('dimensions', 'N/A')}")
                    print(f"    Space Type: {index.get('space_type', 'N/A')}")
                    print(f"    Engine: {index.get('engine_type', 'N/A')}")
                    print(f"    Created: {index.get('created_at', 'N/A')}")
                    print(f"    Source: {index.get('source', 'N/A')}")
                    print()
            else:
                print("    No active indexes found.")
            
            # IAM Roles
            roles = details['iam_roles']
            print(f"\n🔐 IAM Roles ({roles['active']}/{roles['total']} active):")
            if roles['resources']:
                for role in roles['resources']:
                    print(f"  • {role['name']}")
                    print(f"    ARN: {role.get('arn', 'N/A')}")
                    print(f"    Purpose: {role.get('purpose', 'N/A')}")
                    print(f"    Region: {role.get('region', 'N/A')}")
                    print(f"    Created: {role.get('created_at', 'N/A')}")
                    print(f"    Source: {role.get('source', 'N/A')}")
                    print()
            else:
                print("    No active IAM roles found.")
            
            print("="*80)
            
        except Exception as e:
            print(f"❌ Failed to get detailed resources: {e}")
    
    def cleanup_resources(
        self, 
        pattern: str = "all", 
        confirm: bool = False,
        preserve_collections: bool = True,
        preserve_domains: bool = True
    ) -> None:
        """Clean up OpenSearch integration resources."""
        if not confirm:
            print("❌ Cleanup requires --confirm flag")
            print("   This will DELETE OpenSearch resources!")
            print("   Add --confirm to proceed")
            return
        
        print(f"🧹 Starting OpenSearch resource cleanup (pattern: {pattern})...")
        print(f"   Preserve collections: {preserve_collections}")
        print(f"   Preserve domains: {preserve_domains}")
        print()
        
        try:
            if pattern == "all":
                # Clean up all resources
                result = self.integration_manager.cleanup_all_opensearch_resources(
                    confirm_deletion=True,
                    preserve_collections=preserve_collections,
                    preserve_domains=preserve_domains
                )
                
                print("✅ Cleanup completed!")
                print(f"   Pipelines deleted: {result['pipelines_deleted']}")
                print(f"   Collections deleted: {result['collections_deleted']}")
                print(f"   Domains modified: {result['domains_modified']}")
                print(f"   Indexes deleted: {result['indexes_deleted']}")
                print(f"   IAM roles deleted: {result['iam_roles_deleted']}")
                
                if result['errors']:
                    print(f"\n⚠️  Errors encountered ({len(result['errors'])}):")
                    for error in result['errors']:
                        print(f"   • {error}")
            
            elif pattern == "export":
                # Clean up export pattern resources
                pipelines = resource_registry.list_opensearch_pipelines()
                active_pipelines = [p for p in pipelines if p.get('status') == 'created']
                
                if not active_pipelines:
                    print("No export pattern resources found to clean up.")
                    return
                
                cleaned = 0
                for pipeline in active_pipelines:
                    export_id = pipeline.get('name')
                    print(f"Cleaning up export pipeline: {export_id}")
                    
                    result = self.integration_manager.cleanup_export_resources(
                        export_id=export_id,
                        cleanup_collection=not preserve_collections,
                        cleanup_iam_role=True
                    )
                    
                    if result.get('pipeline_deleted'):
                        cleaned += 1
                        print(f"  ✅ Pipeline deleted")
                    if result.get('collection_deleted'):
                        print(f"  ✅ Collection deleted")
                    if result.get('iam_role_deleted'):
                        print(f"  ✅ IAM role deleted")
                    
                    if result['errors']:
                        print(f"  ⚠️  Errors: {', '.join(result['errors'])}")
                
                print(f"\n✅ Export cleanup completed! {cleaned} pipelines processed.")
            
            elif pattern == "engine":
                # Clean up engine pattern resources
                domains = resource_registry.list_opensearch_domains()
                active_domains = [d for d in domains if d.get('status') == 'created']
                
                if not active_domains:
                    print("No engine pattern resources found to clean up.")
                    return
                
                cleaned = 0
                for domain in active_domains:
                    domain_name = domain.get('name')
                    print(f"Cleaning up engine domain: {domain_name}")
                    
                    result = self.integration_manager.cleanup_engine_resources(
                        domain_name=domain_name,
                        disable_s3_vectors=not preserve_domains,
                        cleanup_indexes=True
                    )
                    
                    if result.get('s3_vectors_disabled'):
                        cleaned += 1
                        print(f"  ✅ S3 vectors disabled")
                    
                    indexes_deleted = result.get('indexes_deleted', 0)
                    if indexes_deleted > 0:
                        print(f"  ✅ {indexes_deleted} indexes deleted")
                    
                    if result['errors']:
                        print(f"  ⚠️  Errors: {', '.join(result['errors'])}")
                
                print(f"\n✅ Engine cleanup completed! {cleaned} domains processed.")
            
            else:
                print(f"❌ Unknown cleanup pattern: {pattern}")
                print("   Valid patterns: all, export, engine")
                
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    
    def export_resources_json(self, output_file: str = None) -> None:
        """Export resource information to JSON file."""
        try:
            summary = self.integration_manager.get_opensearch_resource_summary()
            
            output_path = output_file or "opensearch_resources.json"
            with open(output_path, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            print(f"✅ Resource information exported to: {output_path}")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Manage OpenSearch Integration Resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/list_opensearch_resources.py --summary
  python scripts/list_opensearch_resources.py --detailed
  python scripts/list_opensearch_resources.py --cleanup export --confirm
  python scripts/list_opensearch_resources.py --cleanup all --confirm --no-preserve-collections
  python scripts/list_opensearch_resources.py --export resources.json
        """
    )
    
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show resource summary'
    )
    
    parser.add_argument(
        '--detailed',
        action='store_true', 
        help='Show detailed resource information'
    )
    
    parser.add_argument(
        '--cleanup',
        choices=['all', 'export', 'engine'],
        help='Clean up resources by pattern'
    )
    
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirm resource cleanup (required for cleanup operations)'
    )
    
    parser.add_argument(
        '--no-preserve-collections',
        action='store_true',
        help='Allow deletion of OpenSearch Serverless collections'
    )
    
    parser.add_argument(
        '--no-preserve-domains',
        action='store_true',
        help='Allow modification of OpenSearch domains'
    )
    
    parser.add_argument(
        '--export',
        metavar='FILE',
        help='Export resource information to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize resource manager
    manager = OpenSearchResourceManager()
    
    try:
        # Execute requested operations
        if args.summary:
            manager.print_summary()
        
        if args.detailed:
            manager.print_detailed_resources()
        
        if args.cleanup:
            manager.cleanup_resources(
                pattern=args.cleanup,
                confirm=args.confirm,
                preserve_collections=not args.no_preserve_collections,
                preserve_domains=not args.no_preserve_domains
            )
        
        if args.export:
            manager.export_resources_json(args.export)
        
        # Default to summary if no specific action requested
        if not any([args.summary, args.detailed, args.cleanup, args.export]):
            manager.print_summary()
            
    except KeyboardInterrupt:
        print("\n👋 Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Operation failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())