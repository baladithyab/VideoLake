"""
Setup script for real AWS integration tests.

This script helps configure the environment and validate prerequisites
for running real AWS integration tests.

Credential precedence implemented:
  1) If AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are explicitly set, accept and validate via STS.
  2) Else, attempt current/default boto3 session/profile/IMDS/assumed-role; if STS works, accept.
  3) Else, fail with actionable guidance.

Secrets are never printed; only sources are logged.
"""
from dotenv import load_dotenv
# Load .env before any reads, but do not override explicitly provided environment
load_dotenv(override=False)

import os
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _detect_credential_source(session: boto3.Session) -> str:
    """
    Best-effort human-readable source of credentials for logging only.
    Does not print sensitive values.
    """
    akid = os.getenv("AWS_ACCESS_KEY_ID")
    sk = os.getenv("AWS_SECRET_ACCESS_KEY")
    profile = os.getenv("AWS_PROFILE") or session.profile_name
    if akid and sk:
        return "Environment variables (explicit key/secret)"
    if profile:
        return f"Profile '{profile}' (shared config/credentials)"
    return "Default credential chain (IMDS/SSO/AssumeRole/process)"


def check_aws_credentials() -> bool:
    """
    Validate AWS credentials according to fallback logic:
      1) If explicit key/secret are set in env, require STS to pass.
      2) Else, try default/profile chain and require STS to pass.
    """
    logger.info("Checking AWS credentials with fallback logic...")
    try:
        region = os.getenv("AWS_REGION", "us-west-2")
        session = boto3.Session(region_name=region)

        akid = os.getenv("AWS_ACCESS_KEY_ID")
        sk = os.getenv("AWS_SECRET_ACCESS_KEY")

        if akid and sk:
            logger.info("Credential path: Environment variables (explicit key/secret) [secrets redacted]")
        else:
            logger.info(f"Credential path: {_detect_credential_source(session)} [no secrets logged]")

        sts = session.client("sts")
        identity = sts.get_caller_identity()
        logger.info(f"AWS credentials validated via STS. Account: {identity.get('Account')} ARN: {identity.get('Arn')}")
        return True

    except NoCredentialsError:
        logger.error(
            "No AWS credentials could be resolved. Provide one of:\n"
            "  - Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (and AWS_SESSION_TOKEN if temp)\n"
            "  - Or set AWS_PROFILE and ensure your shared config/credentials are valid\n"
            "  - Or authenticate your default chain (e.g., AWS SSO login) so STS works"
        )
        return False
    except ClientError as e:
        logger.error(
            f"STS GetCallerIdentity failed: {e}\n"
            "Resolution tips:\n"
            "  - If using env keys, verify they are correct and not expired.\n"
            "  - If using AWS_PROFILE, run `aws sts get-caller-identity` or `aws sso login` as applicable.\n"
            "  - Ensure the region is correct (AWS_REGION)."
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking credentials: {e}")
        return False


def check_required_permissions() -> bool:
    """Basic sanity checks that required AWS services are reachable."""
    logger.info("Checking AWS service client creation and basic calls...")
    ok = True
    try:
        region = os.getenv("AWS_REGION", "us-west-2")
        session = boto3.Session(region_name=region)

        # S3 simple call
        try:
            s3 = session.client("s3")
            s3.list_buckets()
            logger.info("S3 client OK.")
        except ClientError as e:
            logger.error(f"S3 access failed: {e}")
            ok = False

        # Bedrock Runtime creation (not invoking model here)
        try:
            bedrock = session.client("bedrock-runtime")
            logger.info("Bedrock Runtime client created.")
        except Exception as e:
            logger.warning(f"Bedrock Runtime client creation warning: {e}")

        # S3 Vectors client creation (service availability varies by region)
        try:
            s3vectors = session.client("s3vectors")
            logger.info("S3 Vectors client created.")
        except Exception as e:
            logger.warning(f"S3 Vectors client creation warning: {e}")

    except Exception as e:
        logger.error(f"Permission/service check failed: {e}")
        ok = False

    return ok


def check_environment_variables() -> bool:
    """
    Check presence of required environment variables for the tests.

    Safety gates:
      - S3_VECTORS_BUCKET is required and must be valid (validated separately).
      - AWS credentials may come from env OR from profile/assumed-role/IMDS; do not hard fail
        on missing AWS_ACCESS_KEY_ID/SECRET if STS passes.
    """
    logger.info("Checking environment variables and test configuration...")
    required_nonsecret = {
        "S3_VECTORS_BUCKET": "Vector bucket for testing (unique name)",
    }
    optional = {
        "AWS_REGION": "Region (default us-west-2)",
        "BEDROCK_TEXT_MODEL": "Bedrock text model id (default amazon.titan-embed-text-v2:0)",
        "AWS_PROFILE": "AWS profile to use (optional)",
        "AWS_SESSION_TOKEN": "Session token (if temporary creds)",
        "AWS_ACCESS_KEY_ID": "Access key (optional if profile/chain works)",
        "AWS_SECRET_ACCESS_KEY": "Secret key (optional if profile/chain works)",
    }

    ok = True
    for k, desc in required_nonsecret.items():
        v = os.getenv(k)
        if not v:
            logger.error(f"Missing required env var: {k} - {desc}")
            ok = False
        else:
            logger.info(f"{k}: {v}")

    for k, desc in optional.items():
        v = os.getenv(k)
        if v:
            if "SECRET" in k or "TOKEN" in k:
                logger.info(f"{k}: [REDACTED]")
            elif k == "AWS_ACCESS_KEY_ID":
                masked = v[:4] + "****" if len(v) >= 4 else "[REDACTED]"
                logger.info(f"{k}: {masked}")
            else:
                logger.info(f"{k}: {v}")
        else:
            logger.info(f"{k}: Not set ({desc})")

    return ok


def validate_test_bucket() -> bool:
    """Basic validation that S3_VECTORS_BUCKET looks sane."""
    name = os.getenv("S3_VECTORS_BUCKET")
    if not name:
        logger.error("S3_VECTORS_BUCKET not set.")
        return False

    if not (3 <= len(name) <= 63):
        logger.error(f"S3_VECTORS_BUCKET has invalid length: {len(name)}")
        return False

    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789-")
    if any(c not in allowed for c in name):
        logger.error("S3_VECTORS_BUCKET contains invalid characters.")
        return False

    if name.startswith("-") or name.endswith("-") or "--" in name:
        logger.error("S3_VECTORS_BUCKET cannot start/end with '-' or contain '--'.")
        return False

    logger.info(f"S3_VECTORS_BUCKET looks valid: {name}")
    return True


def estimate_test_costs() -> None:
    logger.info("Estimated costs (rough):")
    logger.info("  - Bedrock Titan embeddings: ~$0.0001 per 1K tokens")
    logger.info("  - S3 Vectors storage: ~$0.023 per GB-month")
    logger.info("  - S3 Vectors queries: ~$0.01 per 1K queries")
    logger.info("Expected total for a full test run: < $0.10")


def create_env_file_template() -> None:
    template = """# Real AWS Integration Test Environment Variables
# Copy to .env and fill values

# Required AWS Credentials
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Optional
AWS_REGION=us-west-2
AWS_SESSION_TOKEN=

# S3 Vectors
S3_VECTORS_BUCKET=

# Bedrock
BEDROCK_TEXT_MODEL=amazon.titan-embed-text-v2:0
"""
    path = ".env.template"
    with open(path, "w", encoding="utf-8") as f:
        f.write(template)
    logger.info(f"Environment template created at {path}")


def main() -> int:
    logger.info("Starting setup checks for real AWS integration tests...")
    all_ok = True

    if not check_environment_variables():
        all_ok = False
    if not check_aws_credentials():
        all_ok = False
    if not check_required_permissions():
        all_ok = False
    if not validate_test_bucket():
        all_ok = False

    estimate_test_costs()

    # Create template if neither .env nor .env.template exist
    if not os.path.exists(".env") and not os.path.exists(".env.template"):
        create_env_file_template()

    if all_ok:
        logger.info("All setup checks passed. Ready to run real AWS tests.")
        return 0
    else:
        logger.error("Setup checks failed. Fix issues before running real AWS tests.")
        return 1


if __name__ == "__main__":
    sys.exit(main())