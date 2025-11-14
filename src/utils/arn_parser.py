"""
AWS ARN Parser Utilities.

Centralized ARN parsing for S3 Vector and other AWS resources.
Eliminates duplicate ARN parsing logic across service files.
"""

import re
from typing import Dict, Optional
from src.exceptions import ValidationError


class ARNParser:
    """Parser for AWS ARN (Amazon Resource Name) formats."""

    # ARN format: arn:partition:service:region:account-id:resource-type/resource-id
    ARN_PATTERN = re.compile(
        r'^arn:(?P<partition>[^:]+):(?P<service>[^:]+):(?P<region>[^:]*):(?P<account>[^:]*):(?P<resource>.+)$'
    )

    # S3 Vector ARN format: arn:aws:s3vectors:region:account:bucket/bucket-name/index/index-name
    S3VECTOR_ARN_PATTERN = re.compile(
        r'^arn:aws:s3vectors:[^:]*:[^:]*:bucket/([^/]+)/index/([^/]+)$'
    )

    @classmethod
    def parse_arn(cls, arn: str) -> Dict[str, str]:
        """
        Parse generic AWS ARN into components.

        Args:
            arn: AWS ARN string

        Returns:
            Dictionary with components: partition, service, region, account, resource

        Raises:
            ValidationError: If ARN format is invalid

        Example:
            >>> ARNParser.parse_arn("arn:aws:s3:::my-bucket")
            {'partition': 'aws', 'service': 's3', 'region': '', 'account': '', 'resource': 'my-bucket'}
        """
        if not arn:
            raise ValidationError("ARN cannot be empty")

        if not arn.startswith('arn:'):
            raise ValidationError(f"Invalid ARN format: must start with 'arn:' - got: {arn}")

        match = cls.ARN_PATTERN.match(arn)
        if not match:
            raise ValidationError(f"Invalid ARN format: {arn}")

        return match.groupdict()

    @classmethod
    def parse_s3vector_arn(cls, arn: str) -> Dict[str, str]:
        """
        Parse S3 Vector ARN into components.

        Args:
            arn: S3 Vector ARN string

        Returns:
            Dictionary with: partition, service, region, account, bucket, index

        Raises:
            ValidationError: If ARN format is invalid

        Example:
            >>> ARNParser.parse_s3vector_arn(
            ...     "arn:aws:s3vectors:us-east-1:123456789:bucket/my-bucket/index/my-index"
            ... )
            {
                'partition': 'aws',
                'service': 's3vectors',
                'region': 'us-east-1',
                'account': '123456789',
                'bucket': 'my-bucket',
                'index': 'my-index'
            }
        """
        # First parse as generic ARN
        base_parts = cls.parse_arn(arn)

        # Validate service
        if base_parts['service'] != 's3vectors':
            raise ValidationError(
                f"Not an S3 Vector ARN: service is '{base_parts['service']}', expected 's3vectors'"
            )

        # Parse resource part: bucket/bucket-name/index/index-name
        match = cls.S3VECTOR_ARN_PATTERN.match(arn)
        if not match:
            raise ValidationError(
                f"Invalid S3 Vector ARN resource format: {arn}. "
                f"Expected: arn:aws:s3vectors:region:account:bucket/BUCKET/index/INDEX"
            )

        bucket_name, index_name = match.groups()

        return {
            **base_parts,
            'bucket': bucket_name,
            'index': index_name
        }

    @classmethod
    def extract_bucket_name(cls, arn: str) -> Optional[str]:
        """
        Extract bucket name from S3 Vector ARN.

        Args:
            arn: S3 Vector ARN string

        Returns:
            Bucket name or None if parsing fails

        Example:
            >>> ARNParser.extract_bucket_name("arn:aws:s3vectors:us-east-1:123:bucket/my-bucket/index/idx")
            'my-bucket'
        """
        try:
            parsed = cls.parse_s3vector_arn(arn)
            return parsed.get('bucket')
        except (ValidationError, Exception):
            return None

    @classmethod
    def extract_index_name(cls, arn: str) -> Optional[str]:
        """
        Extract index name from S3 Vector ARN.

        Args:
            arn: S3 Vector ARN string

        Returns:
            Index name or None if parsing fails

        Example:
            >>> ARNParser.extract_index_name("arn:aws:s3vectors:us-east-1:123:bucket/my-bucket/index/idx")
            'idx'
        """
        try:
            parsed = cls.parse_s3vector_arn(arn)
            return parsed.get('index')
        except (ValidationError, Exception):
            return None

    @classmethod
    def build_s3vector_arn(
        cls,
        bucket: str,
        index: str,
        region: str = "us-east-1",
        account: str = "",
        partition: str = "aws"
    ) -> str:
        """
        Build S3 Vector ARN from components.

        Args:
            bucket: S3 bucket name
            index: Index name
            region: AWS region (default: us-east-1)
            account: AWS account ID (default: empty string)
            partition: AWS partition (default: aws)

        Returns:
            Formatted S3 Vector ARN

        Example:
            >>> ARNParser.build_s3vector_arn("my-bucket", "my-index", "us-west-2", "123456789")
            'arn:aws:s3vectors:us-west-2:123456789:bucket/my-bucket/index/my-index'
        """
        return f"arn:{partition}:s3vectors:{region}:{account}:bucket/{bucket}/index/{index}"

    @classmethod
    def to_resource_id(cls, bucket: str, index: str) -> str:
        """
        Generate normalized resource ID for an index.

        This format is used by some S3 Vector API parameters.

        Args:
            bucket: S3 bucket name
            index: Index name

        Returns:
            Resource ID string

        Example:
            >>> ARNParser.to_resource_id("my-bucket", "my-index")
            'bucket/my-bucket/index/my-index'
        """
        return f"bucket/{bucket}/index/{index}"

    @classmethod
    def is_valid_s3vector_arn(cls, arn: str) -> bool:
        """
        Check if string is a valid S3 Vector ARN.

        Args:
            arn: String to validate

        Returns:
            True if valid S3 Vector ARN, False otherwise

        Example:
            >>> ARNParser.is_valid_s3vector_arn("arn:aws:s3vectors:us-east-1:123:bucket/b/index/i")
            True
            >>> ARNParser.is_valid_s3vector_arn("invalid-arn")
            False
        """
        try:
            cls.parse_s3vector_arn(arn)
            return True
        except (ValidationError, Exception):
            return False

    @classmethod
    def parse_s3_bucket_arn(cls, arn: str) -> Optional[str]:
        """
        Extract bucket name from S3 bucket ARN.

        Args:
            arn: S3 bucket ARN (e.g., "arn:aws:s3:::my-bucket")

        Returns:
            Bucket name or None if parsing fails

        Example:
            >>> ARNParser.parse_s3_bucket_arn("arn:aws:s3:::my-bucket")
            'my-bucket'
        """
        try:
            parsed = cls.parse_arn(arn)
            if parsed['service'] == 's3':
                # S3 bucket ARN format: arn:aws:s3:::bucket-name or arn:aws:s3:::bucket-name/*
                resource = parsed['resource']
                if resource.endswith('/*'):
                    return resource[:-2]
                return resource
            return None
        except (ValidationError, Exception):
            return None
