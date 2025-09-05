#!/usr/bin/env python3
"""
AWS Resource Scanner Service

Scans AWS account for existing resources and integrates with the resource registry.
Discovers S3 buckets, S3Vector buckets, OpenSearch collections, and other resources.
"""

import boto3
import time
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from botocore.exceptions import ClientError, NoCredentialsError
import logging

from src.utils.aws_clients import aws_client_factory
from src.utils.resource_registry import resource_registry
from src.utils.logging_config import get_logger
from src.config.unified_config_manager import get_unified_config_manager

logger = get_logger(__name__)


@dataclass
class ScanResult:
    """Result of a resource scan operation."""
    resource_type: str
    resources_found: List[Dict[str, Any]]
    scan_duration: float
    errors: List[str]
    region: str


@dataclass
class ComprehensiveScanResult:
    """Result of a comprehensive resource scan."""
    scan_results: List[ScanResult]
    total_resources: int
    total_duration: float
    regions_scanned: List[str]
    errors: List[str]


class AWSResourceScanner:
    """Service for scanning AWS resources and updating the registry."""
    
    def __init__(self, region: Optional[str] = None):
        """Initialize AWS resource scanner.
        
        Args:
            region: AWS region to scan (defaults to config region)
        """
        config_manager = get_unified_config_manager()
        self.region = region or config_manager.config.aws.region
        self.resource_registry = resource_registry
        
        # Initialize AWS clients
        try:
            self.s3_client = aws_client_factory.get_s3_client()
            self.opensearch_client = aws_client_factory.get_opensearch_client()
            self.iam_client = aws_client_factory.get_iam_client()
            
            # Try to initialize S3Vector client (may not be available)
            try:
                self.s3vectors_client = aws_client_factory.get_s3vectors_client()
            except Exception:
                self.s3vectors_client = None
                logger.warning("S3Vector client not available")
                
        except Exception as e:
            logger.error(f"Failed to initialize AWS clients: {e}")
            raise
    
    def scan_all_resources(
        self, 
        regions: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None
    ) -> ComprehensiveScanResult:
        """Scan for all supported resource types across regions.
        
        Args:
            regions: List of regions to scan (defaults to current region)
            resource_types: List of resource types to scan (defaults to all)
            
        Returns:
            ComprehensiveScanResult with all scan results
        """
        if regions is None:
            regions = [self.region]
        
        if resource_types is None:
            resource_types = [
                "s3_buckets",
                "s3vector_buckets", 
                "opensearch_collections",
                "opensearch_domains",
                "iam_roles"
            ]
        
        start_time = time.time()
        all_scan_results = []
        all_errors = []
        total_resources = 0
        
        for region in regions:
            logger.info(f"Scanning resources in region: {region}")
            
            for resource_type in resource_types:
                try:
                    scan_result = self._scan_resource_type(resource_type, region)
                    all_scan_results.append(scan_result)
                    total_resources += len(scan_result.resources_found)
                    all_errors.extend(scan_result.errors)
                    
                except Exception as e:
                    error_msg = f"Failed to scan {resource_type} in {region}: {e}"
                    logger.error(error_msg)
                    all_errors.append(error_msg)
        
        total_duration = time.time() - start_time
        
        return ComprehensiveScanResult(
            scan_results=all_scan_results,
            total_resources=total_resources,
            total_duration=total_duration,
            regions_scanned=regions,
            errors=all_errors
        )
    
    def scan_s3_buckets(self, region: str = None) -> ScanResult:
        """Scan for S3 buckets."""
        region = region or self.region
        start_time = time.time()
        resources = []
        errors = []
        
        try:
            response = self.s3_client.list_buckets()
            
            for bucket in response.get('Buckets', []):
                bucket_name = bucket['Name']
                
                try:
                    # Get bucket region
                    bucket_region = self._get_bucket_region(bucket_name)
                    
                    # Only include buckets in the target region
                    if bucket_region == region:
                        # Get additional bucket info
                        bucket_info = {
                            'name': bucket_name,
                            'region': bucket_region,
                            'created_date': bucket['CreationDate'].isoformat(),
                            'type': 'standard'
                        }
                        
                        # Check if bucket has versioning enabled
                        try:
                            versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
                            bucket_info['versioning'] = versioning.get('Status', 'Disabled')
                        except ClientError:
                            bucket_info['versioning'] = 'Unknown'
                        
                        resources.append(bucket_info)
                        
                except ClientError as e:
                    error_msg = f"Failed to get info for bucket {bucket_name}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        except ClientError as e:
            error_msg = f"Failed to list S3 buckets: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        duration = time.time() - start_time
        
        return ScanResult(
            resource_type="s3_buckets",
            resources_found=resources,
            scan_duration=duration,
            errors=errors,
            region=region
        )
    
    def scan_s3vector_buckets(self, region: str = None) -> ScanResult:
        """Scan for S3Vector buckets."""
        region = region or self.region
        start_time = time.time()
        resources = []
        errors = []
        
        if not self.s3vectors_client:
            errors.append("S3Vector client not available")
            return ScanResult(
                resource_type="s3vector_buckets",
                resources_found=resources,
                scan_duration=0,
                errors=errors,
                region=region
            )
        
        try:
            # Use S3Vector API to list buckets
            response = self.s3vectors_client.list_buckets()
            
            for bucket in response.get('Buckets', []):
                bucket_info = {
                    'name': bucket.get('Name'),
                    'region': region,
                    'created_date': bucket.get('CreationDate', '').isoformat() if bucket.get('CreationDate') else None,
                    'type': 's3vector'
                }
                resources.append(bucket_info)
        
        except Exception as e:
            error_msg = f"Failed to list S3Vector buckets: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        duration = time.time() - start_time
        
        return ScanResult(
            resource_type="s3vector_buckets",
            resources_found=resources,
            scan_duration=duration,
            errors=errors,
            region=region
        )
    
    def scan_opensearch_collections(self, region: str = None) -> ScanResult:
        """Scan for OpenSearch Serverless collections."""
        region = region or self.region
        start_time = time.time()
        resources = []
        errors = []
        
        try:
            # Create region-specific OpenSearch Serverless client
            aoss_client = boto3.client('opensearchserverless', region_name=region)
            
            response = aoss_client.list_collections()
            
            for collection in response.get('collectionSummaries', []):
                collection_info = {
                    'name': collection.get('name'),
                    'id': collection.get('id'),
                    'arn': collection.get('arn'),
                    'status': collection.get('status'),
                    'type': collection.get('type'),
                    'region': region,
                    'created_date': collection.get('createdDate', '').isoformat() if collection.get('createdDate') else None
                }
                resources.append(collection_info)
        
        except ClientError as e:
            error_msg = f"Failed to list OpenSearch collections: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        except Exception as e:
            error_msg = f"OpenSearch Serverless not available in region {region}: {e}"
            errors.append(error_msg)
            logger.warning(error_msg)
        
        duration = time.time() - start_time
        
        return ScanResult(
            resource_type="opensearch_collections",
            resources_found=resources,
            scan_duration=duration,
            errors=errors,
            region=region
        )
    
    def scan_opensearch_domains(self, region: str = None) -> ScanResult:
        """Scan for OpenSearch managed domains."""
        region = region or self.region
        start_time = time.time()
        resources = []
        errors = []
        
        try:
            # Create region-specific OpenSearch client
            opensearch_client = boto3.client('opensearch', region_name=region)
            
            response = opensearch_client.list_domain_names()
            
            for domain in response.get('DomainNames', []):
                domain_name = domain.get('DomainName')
                
                try:
                    # Get detailed domain info
                    domain_detail = opensearch_client.describe_domain(DomainName=domain_name)
                    domain_status = domain_detail.get('DomainStatus', {})
                    
                    domain_info = {
                        'name': domain_name,
                        'arn': domain_status.get('ARN'),
                        'endpoint': domain_status.get('Endpoint'),
                        'version': domain_status.get('EngineVersion'),
                        'status': 'active' if domain_status.get('Created') else 'unknown',
                        'region': region,
                        'created': domain_status.get('Created', False)
                    }
                    resources.append(domain_info)
                    
                except ClientError as e:
                    error_msg = f"Failed to get details for domain {domain_name}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
        
        except ClientError as e:
            error_msg = f"Failed to list OpenSearch domains: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        duration = time.time() - start_time
        
        return ScanResult(
            resource_type="opensearch_domains",
            resources_found=resources,
            scan_duration=duration,
            errors=errors,
            region=region
        )
    
    def scan_iam_roles(self, region: str = None) -> ScanResult:
        """Scan for IAM roles (global resource)."""
        region = region or self.region
        start_time = time.time()
        resources = []
        errors = []
        
        try:
            # IAM is global, but we'll attribute to the specified region
            paginator = self.iam_client.get_paginator('list_roles')
            
            for page in paginator.paginate():
                for role in page.get('Roles', []):
                    # Filter for roles that might be related to our services
                    role_name = role.get('RoleName', '')
                    if any(keyword in role_name.lower() for keyword in 
                          ['opensearch', 's3vector', 'bedrock', 'lambda']):
                        
                        role_info = {
                            'name': role_name,
                            'arn': role.get('Arn'),
                            'path': role.get('Path'),
                            'created_date': role.get('CreateDate', '').isoformat() if role.get('CreateDate') else None,
                            'description': role.get('Description', ''),
                            'region': region  # Attributed region
                        }
                        resources.append(role_info)
        
        except ClientError as e:
            error_msg = f"Failed to list IAM roles: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        duration = time.time() - start_time
        
        return ScanResult(
            resource_type="iam_roles",
            resources_found=resources,
            scan_duration=duration,
            errors=errors,
            region=region
        )
    
    def add_discovered_resources_to_registry(
        self, 
        scan_results: List[ScanResult],
        source: str = "scanner"
    ) -> Dict[str, int]:
        """Add discovered resources to the registry.
        
        Args:
            scan_results: List of scan results to process
            source: Source identifier for registry entries
            
        Returns:
            Dictionary with count of resources added by type
        """
        added_counts = {}
        
        for scan_result in scan_results:
            resource_type = scan_result.resource_type
            added_count = 0
            
            for resource in scan_result.resources_found:
                try:
                    if resource_type == "s3_buckets":
                        self.resource_registry.log_s3_bucket_created(
                            bucket_name=resource['name'],
                            region=resource['region'],
                            source=source
                        )
                    elif resource_type == "s3vector_buckets":
                        self.resource_registry.log_vector_bucket_created(
                            bucket_name=resource['name'],
                            region=resource['region'],
                            source=source
                        )
                    elif resource_type == "opensearch_collections":
                        self.resource_registry.log_opensearch_collection_created(
                            collection_name=resource['name'],
                            collection_arn=resource['arn'],
                            region=resource['region'],
                            source=source
                        )
                    elif resource_type == "opensearch_domains":
                        self.resource_registry.log_opensearch_domain_created(
                            domain_name=resource['name'],
                            domain_arn=resource['arn'],
                            endpoint=resource.get('endpoint'),
                            region=resource['region'],
                            source=source
                        )
                    elif resource_type == "iam_roles":
                        self.resource_registry.log_iam_role_created(
                            role_name=resource['name'],
                            role_arn=resource['arn'],
                            region=resource['region'],
                            source=source
                        )
                    
                    added_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to add {resource_type} {resource.get('name')} to registry: {e}")
            
            added_counts[resource_type] = added_count
            logger.info(f"Added {added_count} {resource_type} to registry")
        
        return added_counts
    
    def _scan_resource_type(self, resource_type: str, region: str) -> ScanResult:
        """Scan for a specific resource type."""
        if resource_type == "s3_buckets":
            return self.scan_s3_buckets(region)
        elif resource_type == "s3vector_buckets":
            return self.scan_s3vector_buckets(region)
        elif resource_type == "opensearch_collections":
            return self.scan_opensearch_collections(region)
        elif resource_type == "opensearch_domains":
            return self.scan_opensearch_domains(region)
        elif resource_type == "iam_roles":
            return self.scan_iam_roles(region)
        else:
            raise ValueError(f"Unsupported resource type: {resource_type}")
    
    def _get_bucket_region(self, bucket_name: str) -> str:
        """Get the region of an S3 bucket."""
        try:
            response = self.s3_client.get_bucket_location(Bucket=bucket_name)
            region = response.get('LocationConstraint')
            # us-east-1 returns None for LocationConstraint
            return region if region else 'us-east-1'
        except ClientError:
            # If we can't determine region, assume current region
            return self.region


# Example usage
if __name__ == "__main__":
    scanner = AWSResourceScanner()
    
    # Scan all resources
    result = scanner.scan_all_resources()
    
    print(f"Scanned {result.total_resources} resources in {result.total_duration:.2f}s")
    print(f"Regions: {result.regions_scanned}")
    
    if result.errors:
        print(f"Errors: {result.errors}")
    
    # Add to registry
    added = scanner.add_discovered_resources_to_registry(result.scan_results)
    print(f"Added to registry: {added}")
