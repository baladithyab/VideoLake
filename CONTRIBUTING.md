# Contributing to S3Vector

Thank you for your interest in contributing to the S3Vector AWS Vector Store Comparison Platform! This document provides guidelines for contributing to the project.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [How to Contribute](#how-to-contribute)
4. [Development Guidelines](#development-guidelines)
5. [Documentation Guidelines](#documentation-guidelines)
6. [Testing Requirements](#testing-requirements)
7. [Pull Request Process](#pull-request-process)
8. [Style Guidelines](#style-guidelines)

---

## 🤝 Code of Conduct

This project follows a code of professional conduct:

- Be respectful and inclusive
- Focus on constructive feedback
- Value diverse perspectives
- Prioritize project goals over personal preferences
- Maintain professional communication

---

## 🚀 Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **Development Environment**:
   - Python 3.11+
   - Node.js 18+
   - Terraform 1.0+
   - AWS CLI configured
   - Git

2. **AWS Access**:
   - Valid AWS account
   - Appropriate IAM permissions
   - Bedrock and S3Vectors access

3. **Knowledge**:
   - Familiarity with vector databases
   - Understanding of AWS services
   - Python and TypeScript experience

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/S3Vector.git
cd S3Vector

# Install Python dependencies with uv (creates and manages virtual environment automatically)
uv sync --all-extras  # Installs all dependencies including dev extras

# Install frontend dependencies
cd frontend
bun install
cd ..

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Deploy infrastructure
cd terraform
terraform init
terraform apply
cd ..

# Run tests to verify setup
uv run pytest tests/test_e2e_vector_store_workflows.py -v
```

---

## 💡 How to Contribute

### Types of Contributions

We welcome various types of contributions:

#### 🐛 Bug Reports

**Before submitting**:
- Check if issue already exists
- Verify it's not already fixed in latest version
- Collect relevant information

**What to include**:
- Clear description of the bug
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, versions)
- Error messages and logs
- Screenshots if applicable

**Template**:
```markdown
**Description**: Brief description of the bug

**Steps to Reproduce**:
1. Deploy with Mode 1
2. Process video X
3. Run query Y
4. Observe error Z

**Expected Behavior**: Should return results

**Actual Behavior**: Returns error "..."

**Environment**:
- OS: Ubuntu 22.04
- Python: 3.11.5
- Terraform: 1.6.0
- AWS Region: us-east-1

**Logs**:
```
[paste relevant logs]
```
```

#### ✨ Feature Requests

**Before submitting**:
- Check if feature already planned
- Consider if it fits project scope
- Think about implementation approach

**What to include**:
- Clear use case
- Proposed solution
- Alternative approaches considered
- Potential impact on existing features

#### 📖 Documentation Improvements

Documentation contributions are highly valued!

**Types**:
- Fixing typos or errors
- Adding examples
- Improving clarity
- Adding missing sections
- Translating documentation

**See**: [Documentation Guidelines](#documentation-guidelines)

#### 🔧 Code Contributions

**Types**:
- Bug fixes
- Feature implementations
- Performance optimizations  
- Test improvements
- Refactoring

**See**: [Development Guidelines](#development-guidelines)

---

## 🛠️ Development Guidelines

### Architecture Principles

Follow these core principles:

1. **Terraform-First Infrastructure**
   - All infrastructure changes via Terraform
   - Never create AWS resources via API for optional backends
   - S3Vector operations OK via API (built-in)

2. **S3Vector as Primary Backend**
   - S3Vector is the default, always-deployed backend
   - Other backends are optional comparisons
   - Design features to work with S3Vector first

3. **Provider Pattern**
   - Use [`VectorStoreProvider`](src/services/vector_store_provider.py) interface
   - Implement for new backends
   - Maintain interface compatibility

4. **Health-First Design**
   - All backends must support health checks
   - 3-second timeout for responsiveness
   - Graceful degradation when backends unavailable

### Code Organization

```
src/
├── api/           # FastAPI routes and middleware
├── services/      # Business logic and providers
├── utils/         # Shared utilities
└── models/        # Data models and schemas

tests/
├── Core tests     # S3Vector functionality (no infra needed)
└── Optional tests # Backend comparisons (requires Terraform)

terraform/
└── modules/       # Infrastructure as Code
```

### Coding Standards

#### Python

```python
# Style: Follow PEP 8
# Type hints: Required for public APIs
# Docstrings: Google style

async def process_video(
    video_s3_uri: str,
    backend: str,
    options: dict
) -> dict:
    """
    Process video and generate embeddings.
    
    Args:
        video_s3_uri: S3 URI of video file
        backend: Target vector store backend
        options: Processing configuration
        
    Returns:
        Processing job details with job_id and status
        
    Raises:
        ValidationError: Invalid input parameters
        ProcessingError: Video processing failed
    """
    # Implementation
```

#### TypeScript/React

```typescript
// Style: Follow Airbnb style guide
// Types: Required for all exports
// Components: Functional with hooks

interface SearchProps {
  backend: string;
  onResults: (results: SearchResult[]) => void;
}

export const SearchComponent: React.FC<SearchProps> = ({ 
  backend, 
  onResults 
}) => {
  // Implementation
};
```

#### Terraform

```hcl
# Style: terraform fmt before commit
# Naming: snake_case for resources
# Comments: Explain non-obvious choices

resource "aws_instance" "qdrant" {
  # Instance configuration
  instance_type = var.qdrant_instance_type
  
  # Security group for port 6333
  vpc_security_group_ids = [aws_security_group.qdrant.id]
  
  tags = merge(
    var.common_tags,
    {
      Name = "${var.project_name}-qdrant"
      Role = "vector-database"
    }
  )
}
```

### Adding New Vector Store Backend

To add a new vector store:

1. **Create Provider Implementation**:
   ```bash
   # Create new provider file
   touch src/services/vector_store_newbackend_provider.py
   ```

2. **Implement VectorStoreProvider Interface**:
   ```python
   from src.services.vector_store_provider import VectorStoreProvider
   
   class NewBackendProvider(VectorStoreProvider):
       async def create_index(self, index_name: str) -> bool:
           # Implementation
           
       async def add_vectors(self, index_name: str, vectors: List) -> bool:
           # Implementation
           
       async def search(self, query_vector: List[float], k: int) -> List:
           # Implementation
           
       async def health_check(self) -> bool:
           # Implementation
   ```

3. **Create Terraform Module**:
   ```bash
   mkdir -p terraform/modules/newbackend
   touch terraform/modules/newbackend/main.tf
   touch terraform/modules/newbackend/variables.tf
   touch terraform/modules/newbackend/outputs.tf
   ```

4. **Add Tests**:
   ```bash
   # Add to test_real_aws_e2e_workflows.py
   class TestRealNewBackendWorkflow:
       def test_newbackend_workflow(self):
           # Implementation
   ```

5. **Update Documentation**:
   - Add to [`ARCHITECTURE.md`](docs/ARCHITECTURE.md)
   - Update [`DEPLOYMENT_GUIDE.md`](docs/DEPLOYMENT_GUIDE.md)
   - Add examples to [`usage-examples.md`](docs/usage-examples.md)

---

## 📖 Documentation Guidelines

### Documentation Standards

1. **Markdown Format**:
   - Use proper heading hierarchy (H1 → H2 → H3)
   - Include table of contents for docs > 200 lines
   - Use code fences with language identifiers
   - Include examples with expected output

2. **Required Sections** (for guides):
   - Overview/Purpose
   - Prerequisites
   - Step-by-step instructions
   - Expected results
   - Troubleshooting
   - Cross-references

3. **Code Examples**:
   - Show complete, runnable code
   - Include expected output
   - Add comments for clarity
   - Test all examples before committing

4. **Terminology**:
   - **S3Vector**: Project name (singular)
   - **S3Vectors**: AWS library name
   - **Backend** or **Vector Store**: Storage systems
   - **Mode 1/2/3**: Deployment configurations

### File Organization

- **Root README**: [`README.md`](README.md) - Project overview
- **Getting Started**: [`QUICKSTART.md`](QUICKSTART.md) - Quick setup
- **Technical Docs**: [`docs/`](docs/) directory
- **Module Docs**: Co-located with code (e.g., [`terraform/README.md`](terraform/README.md))
- **Archive**: [`archive/development/`](archive/development/) - Historical docs

### Documentation Style

```markdown
# Document Title

> **Brief description of what this document covers**

## Table of Contents (if > 200 lines)

## Section 1

Clear, concise writing with:
- Actionable steps
- Code examples
- Expected outcomes

### Examples

```bash
# Commands with comments
terraform init  # Initialize Terraform
```

**Expected Output**:
```
Terraform has been successfully initialized!
```

## Troubleshooting

Common issues with solutions.
```

---

## 🧪 Testing Requirements

### Test Coverage Requirements

- **New Features**: Minimum 80% coverage
- **Bug Fixes**: Test for regression
- **Refactoring**: Maintain or improve coverage

### Running Tests

```bash
# Core S3Vector tests (required for all PRs)
uv run pytest tests/test_e2e_vector_store_workflows.py -v

# Optional backend tests (if infrastructure changes)
# Requires: terraform apply first
uv run pytest tests/test_real_aws_e2e_workflows.py -v --real-aws -m "not expensive"
```

### Test Guidelines

1. **S3Vector Tests (Core)**:
   - Required for all PRs
   - No additional infrastructure needed
   - Fast execution (<1 minute)
   - Use mocks appropriately

2. **Optional Backend Tests**:
   - Required for backend-specific changes
   - Requires Terraform deployment
   - Document cost implications
   - Skip expensive tests in CI

3. **Test Naming**:
   ```python
   def test_s3vector_create_index():  # Feature tested
       """Test S3Vector index creation."""  # Clear docstring
       # Arrange
       # Act
       # Assert
   ```

4. **Cleanup**:
   - All tests must clean up resources
   - Use fixtures with try/finally
   - Verify cleanup succeeded

---

## 🔄 Pull Request Process

### Before Submitting PR

1. **Code Quality**:
   ```bash
   # Format Python code
   black src/ tests/
   
   # Format TypeScript code
   cd frontend && bun run format

   # Lint code
   pylint src/
   cd frontend && bun run lint
   
   # Format Terraform
   cd terraform && terraform fmt -recursive
   ```

2. **Run Tests**:
   ```bash
   # Core tests (required)
   uv run pytest tests/test_e2e_vector_store_workflows.py -v --cov=src

   # Terraform validation
   cd terraform && terraform validate
   ```

3. **Update Documentation**:
   - Update relevant docs for changes
   - Add examples if adding features
   - Update CHANGELOG if exists

### PR Title Format

```
<type>(<scope>): <description>

Examples:
feat(s3vector): add batch indexing support
fix(opensearch): resolve connection timeout
docs(deployment): update Mode 2 instructions
test(qdrant): add performance benchmarks
refactor(api): simplify route handlers
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `chore`: Maintenance tasks

### PR Description Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Testing

- [ ] Core S3Vector tests pass
- [ ] Optional backend tests pass (if applicable)
- [ ] New tests added for new functionality
- [ ] All tests pass locally

## Documentation

- [ ] Updated relevant documentation
- [ ] Added code examples if needed
- [ ] Updated API documentation if API changed

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex logic
- [ ] No new warnings generated
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests passing
```

### Review Process

1. **Automated Checks** (CI):
   - Code formatting (black, prettier)
   - Linting (pylint, eslint)
   - Core test suite
   - Type checking

2. **Manual Review**:
   - Code quality and design
   - Test coverage  
   - Documentation completeness
   - Breaking change assessment

3. **Approval Requirements**:
   - At least 1 approval from maintainer
   - All CI checks passing
   - No unresolved review comments

---

## 🎨 Style Guidelines

### Python Style

Follow **PEP 8** with these specifics:

```python
# Line length: 88 characters (Black default)
# Imports: Organized by stdlib, third-party, local
# Quotes: Double quotes for strings
# Formatting: Use Black

import os
from typing import List, Dict

import boto3
import requests

from src.utils.aws_clients import get_s3_client
from src.services.vector_store_provider import VectorStoreProvider


class S3VectorProvider(VectorStoreProvider):
    """S3Vector backend implementation."""
    
    def __init__(self, bucket_name: str) -> None:
        """Initialize S3Vector provider."""
        self.bucket_name = bucket_name
        self.client = get_s3_client()
```

### TypeScript/React Style

Follow **Airbnb style guide** with these specifics:

```typescript
// Use functional components with hooks
// Props: Define interfaces
// Exports: Named exports for components

import React, { useState, useEffect } from 'react';

interface SearchComponentProps {
  backend: string;
  onSearch: (query: string) => void;
}

export const SearchComponent: React.FC<SearchComponentProps> = ({
  backend,
  onSearch,
}) => {
  const [query, setQuery] = useState('');
  
  // Component logic
  
  return (
    <div className="search-container">
      {/* JSX */}
    </div>
  );
};
```

### Terraform Style

Follow **HashiCorp conventions**:

```hcl
# File organization: resources, data, variables, outputs
# Naming: snake_case for all identifiers
# Comments: Explain why, not what
# Formatting: terraform fmt

resource "aws_instance" "qdrant" {
  # Use descriptive names
  instance_type = var.qdrant_instance_type
  ami           = data.aws_ami.amazon_linux_2.id
  
  # Tag all resources
  tags = {
    Name        = "${var.project_name}-qdrant"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  
  # Lifecycle rules when appropriate
  lifecycle {
    create_before_destroy = true
  }
}
```

### Documentation Style

```markdown
# Use American English spelling
# Use present tense ("returns" not "will return")
# Use active voice ("configure the backend" not "the backend should be configured")
# Use second person ("you can" not "one can")

## Structure

Each guide should have:
1. Overview with purpose
2. Prerequisites
3. Step-by-step instructions
4. Expected results
5. Troubleshooting
6. Cross-references

## Code Examples

Always include:
- Complete, runnable code
- Comments for clarity
- Expected output
- Error handling

## Cost Information

Always mention:
- Estimated costs (e.g., ~$0.50/month)
- Time estimates (e.g., < 5 minutes)
- Warnings for expensive operations
```

---

## ✅ Testing Requirements

### Test Coverage Rules

1. **Core S3Vector Changes**: Must include tests
2. **API Changes**: Must include integration tests
3. **Infrastructure Changes**: Must include Terraform validation
4. **Bug Fixes**: Must include regression test

### Test Types

#### Unit Tests
```python
def test_s3vector_provider_initialization():
    """Test provider initializes correctly."""
    provider = S3VectorProvider(bucket_name="test-bucket")
    assert provider.bucket_name == "test-bucket"
    assert provider.client is not None
```

#### Integration Tests
```python
@pytest.mark.integration
def test_video_processing_integration():
    """Test complete video processing workflow."""
    # End-to-end integration test
```

#### Real AWS Tests
```python
@pytest.mark.real_aws
@pytest.mark.skipif(not os.getenv("REAL_AWS_TESTS"), reason="Skipping real AWS tests")
def test_real_s3vector_workflow():
    """Test with real AWS resources (costs money!)."""
    # Real AWS integration test
```

### Running Tests Before PR

```bash
# Format code
black src/ tests/
cd frontend && bun run format

# Lint
pylint src/ tests/
cd frontend && bun run lint

# Type check
mypy src/

# Run all core tests
uv run pytest tests/test_e2e_vector_store_workflows.py -v --cov=src

# Run specific tests if needed
uv run pytest tests/ -v -k "s3vector"

# All tests should pass before submitting PR
```

---

## 📝 Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Example**:
```
feat(api): add batch embedding generation endpoint

Add new /api/embeddings/batch endpoint for generating
multiple embeddings in a single request. Improves
performance by 3x for bulk operations.

Closes #123
```

### Commit Types

- `feat`: New feature
- `fix`: Bug fix  
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Test additions/changes
- `chore`: Build process, dependencies

### Commit Best Practices

- One logical change per commit
- Write clear commit messages
- Reference issues in commit body
- Keep commits focused and atomic

---

## 🎯 Feature Development Workflow

### 1. Planning Phase

- Open GitHub issue describing feature
- Discuss approach with maintainers
- Get approval before major work

### 2. Development Phase

```bash
# Create feature branch
git checkout -b feat/your-feature-name

# Make changes following guidelines
# Commit regularly with clear messages

# Keep branch updated
git fetch origin
git rebase origin/main
```

### 3. Testing Phase

```bash
# Run all relevant tests
uv run pytest tests/ -v

# Add new tests for feature
# Ensure >80% coverage

# Test documentation examples
# Verify all code snippets work
```

### 4. Documentation Phase

- Update affected documentation
- Add usage examples
- Update API docs if needed
- Add to CHANGELOG

### 5. Review Phase

```bash
# Push feature branch
git push origin feat/your-feature-name

# Create pull request
# Address review comments
# Make requested changes
```

---

## 🔍 Review Checklist

### For Reviewers

When reviewing PRs, check:

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Adequate test coverage
- [ ] Documentation updated
- [ ] No breaking changes (or properly documented)
- [ ] Performance impact considered
- [ ] Security implications reviewed
- [ ] Error handling appropriate
- [ ] Logging added for debugging
- [ ] Cost impact documented (if infrastructure change)

### For Contributors

Before requesting review:

- [ ] All tests passing locally
- [ ] Code formatted (black, prettier)
- [ ] No linting errors
- [ ] Documentation updated
- [ ] Examples tested
- [ ] Commit messages clear
- [ ] PR description complete
- [ ] Breaking changes noted

---

## 💬 Communication

### Asking Questions

- Use GitHub Discussions for general questions
- Use GitHub Issues for bug reports and feature requests
- Reference relevant documentation when asking
- Provide context and examples

### Reporting Security Issues

**Do not open public issues for security vulnerabilities!**

Instead:
- Email maintainers directly
- Provide detailed description
- Wait for confirmation before disclosure

---

## 🙏 Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes
- Project documentation
- Community highlights

---

## 📚 Additional Resources

### Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Deployment patterns
- **[testing_guide.md](docs/testing_guide.md)** - Testing approach
- **[DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)** - Complete doc catalog

### External Resources

- [AWS S3Vectors Documentation](https://docs.aws.amazon.com/s3/)
- [Terraform Best Practices](https://www.terraform.io/docs/cloud/guides/recommended-practices/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

---

## ❓ Questions?

If you have questions:

1. Check the **[FAQ](docs/FAQ.md)**
2. Search **GitHub Issues** for similar questions
3. Ask in **GitHub Discussions**
4. Reference relevant documentation

---

**Thank you for contributing to S3Vector!** 🎉

Your contributions help make AWS vector store evaluation more accessible and effective for everyone.

---

**Last Updated**: 2025-11-13  
**Version**: 1.0  
**Maintainer**: S3Vector Team