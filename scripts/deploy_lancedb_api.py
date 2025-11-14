#!/usr/bin/env python3
"""Build and deploy the LanceDB API Docker image to ECS via ECR.

This script is a thin wrapper around `docker build` and AWS CLI calls to
push the image to ECR and trigger a new ECS deployment for the
LanceDB API service created by the `terraform/modules/lancedb_ecs` module.

It intentionally reuses the existing Terraform/ECS layout instead of
introducing new infrastructure.

Prerequisites:
- Terraform has been applied with one of the LanceDB modules enabled
  (deploy_lancedb_s3 / deploy_lancedb_efs / deploy_lancedb_ebs).
- An ECR repository exists and the ECS task definition references
  that repository (configured in Terraform module variables).

By default this script targets the S3-backed deployment
("${var.lancedb_deployment_name}-s3"). You can override the deployment
name and AWS region via CLI arguments.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def run(cmd, cwd: Path | None = None) -> None:
    """Run a shell command, raising on non-zero exit.

    This is intentionally simple; orchestration and retries live in
    scripts/deploy_and_benchmark.py.
    """
    cwd = cwd or Path.cwd()
    logger.info("Running command", extra={"cmd": " ".join(cmd), "cwd": str(cwd)})
    result = subprocess.run(cmd, cwd=str(cwd))
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and deploy LanceDB API Docker image")
    parser.add_argument("--aws-region", default="us-east-1", help="AWS region (default: us-east-1)")
    parser.add_argument(
        "--deployment-name",
        default="videolake-lancedb-s3",
        help="Base deployment name used by terraform/modules/lancedb_ecs",
    )
    parser.add_argument(
        "--ecr-repo",
        default=None,
        help=(
            "Optional explicit ECR repo URI (e.g. 123.dkr.ecr.us-east-1.amazonaws.com/videolake-lancedb-api). "
            "If omitted, will assume '<account>.dkr.ecr.<region>.amazonaws.com/<deployment-name>-api'."
        ),
    )
    parser.add_argument("--image-tag", default="latest", help="Docker image tag (default: latest)")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    project_root = Path(__file__).parent.parent
    docker_dir = project_root / "docker/lancedb-api"
    if not docker_dir.is_dir():
        print(f"Docker directory not found: {docker_dir}")
        return 1

    # Resolve account ID and ECR repo URL
    try:
        import boto3

        sts = boto3.client("sts", region_name=args.aws_region)
        account_id = sts.get_caller_identity()["Account"]
    except Exception as e:  # pragma: no cover - environment specific
        logger.error("Failed to resolve AWS account ID via STS: %s", e)
        print(f"Failed to resolve AWS account ID: {e}")
        return 1

    repo_url = args.ecr_repo or f"{account_id}.dkr.ecr.{args.aws_region}.amazonaws.com/{args.deployment_name}-api"

    # Docker build
    image_name = f"lancedb-api:{args.image_tag}"
    print(f"Building Docker image {image_name} in {docker_dir}...")
    run(["docker", "build", "-t", image_name, "."], cwd=docker_dir)

    # Docker tag
    full_image = f"{repo_url}:{args.image_tag}"
    print(f"Tagging image {image_name} as {full_image}...")
    run(["docker", "tag", image_name, full_image])

    # ECR login
    print(f"Logging in to ECR {repo_url}...")
    login_cmd = [
        "aws",
        "ecr",
        "get-login-password",
        "--region",
        args.aws_region,
    ]
    login_proc = subprocess.run(login_cmd, capture_output=True, text=True)
    if login_proc.returncode != 0:
        print("Failed to get ECR login password:", login_proc.stderr)
        return login_proc.returncode

    docker_login_cmd = [
        "docker",
        "login",
        "--username",
        "AWS",
        "--password-stdin",
        repo_url,
    ]
    docker_login = subprocess.run(docker_login_cmd, input=login_proc.stdout, text=True)
    if docker_login.returncode != 0:
        print("Docker login to ECR failed")
        return docker_login.returncode

    # Docker push
    print(f"Pushing image {full_image} to ECR...")
    run(["docker", "push", full_image])

    # Optional: update ECS service to pick up new image via force-new-deployment.
    # The ECS cluster and service names are derived from the deployment_name
    # as defined in terraform/modules/lancedb_ecs.
    cluster_name = f"{args.deployment_name}-cluster"
    service_name = f"{args.deployment_name}-service"

    print(f"Forcing new ECS deployment on cluster={cluster_name}, service={service_name}...")
    run(
        [
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            cluster_name,
            "--service",
            service_name,
            "--force-new-deployment",
            "--region",
            args.aws_region,
        ]
    )

    print("LanceDB API image built, pushed, and ECS service updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

