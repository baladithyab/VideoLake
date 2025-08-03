---
inclusion: always
---

# MCP Documentation-First Development Approach

## Always Use Live Documentation

### Priority Order for Information Sources
1. **MCP AWS Documentation Tools** - Always check first for the most current information
2. **MCP Web Search Tools** - For latest updates, blog posts, and community insights
3. **MCP GitHub Tools** - For code examples and implementation patterns
4. **Static knowledge** - Only as a fallback when MCP tools are unavailable

## Required MCP Tool Usage Patterns

### AWS Service Documentation
Before implementing any AWS service integration, ALWAYS:

```python
# 1. Search for current documentation
mcp_aws_knowledge_mcp_server_aws___search_documentation(
    search_phrase="S3 Vectors API operations boto3"
)

# 2. Read specific documentation pages
mcp_aws_knowledge_mcp_server_aws___read_documentation(
    url="https://docs.aws.amazon.com/AmazonS3/latest/API/API_Operations_Amazon_S3_Vectors.html"
)

# 3. Get recommendations for related content
mcp_aws_knowledge_mcp_server_aws___recommend(
    url="https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters.html"
)
```

### Bedrock and TwelveLabs Updates
Stay current with model changes and new features:

```python
# Check for latest Bedrock model information
mcp_tavily_mcp_tavily_search(
    query="Amazon Bedrock new embedding models 2025",
    time_range="month"
)

# Search for TwelveLabs updates
mcp_tavily_mcp_tavily_search(
    query="TwelveLabs Marengo model updates Amazon Bedrock",
    time_range="week"
)
```

### Code Examples and Best Practices
Always verify implementation patterns with current examples:

```python
# Search GitHub for latest implementation patterns
mcp_github_search_code(
    q="s3vectors boto3 python",
    sort="indexed",
    order="desc"
)

# Look for official AWS code examples
mcp_github_search_repositories(
    query="org:awsdocs s3 vectors python"
)
```

## Implementation Workflow with MCP

### Before Starting Any Task
1. **Research Current State**: Use MCP tools to verify latest API changes
2. **Check for Updates**: Search for recent blog posts or announcements
3. **Validate Examples**: Find current code examples and patterns
4. **Verify Pricing**: Check for latest cost information

### During Implementation
1. **Real-time Validation**: Use MCP tools to verify API parameters
2. **Error Resolution**: Search for current solutions to encountered issues
3. **Best Practice Updates**: Check for latest recommendations
4. **Performance Insights**: Look for current optimization strategies

### After Implementation
1. **Validation**: Verify implementation against latest documentation
2. **Optimization**: Search for newest performance recommendations
3. **Security Updates**: Check for latest security best practices
4. **Cost Analysis**: Verify current pricing and optimization strategies

## Specific MCP Usage for This Project

### S3 Vectors (Preview Service)
Since S3 Vectors is in preview, documentation changes frequently:

```python
# Always check for latest S3 Vectors documentation
mcp_aws_knowledge_mcp_server_aws___search_documentation(
    search_phrase="S3 Vectors preview updates limitations"
)

# Look for latest API changes
mcp_tavily_mcp_tavily_search(
    query="AWS S3 Vectors API changes preview",
    time_range="week"
)
```

### Bedrock Model Updates
Models and pricing change regularly:

```python
# Check for new embedding models
mcp_aws_knowledge_mcp_server_aws___search_documentation(
    search_phrase="Bedrock embedding models 2025"
)

# Verify current model IDs and availability
mcp_tavily_mcp_tavily_search(
    query="Amazon Bedrock model IDs embedding 2025"
)
```

### TwelveLabs Integration
Monitor for service updates and new features:

```python
# Check TwelveLabs documentation for updates
mcp_tavily_mcp_tavily_search(
    query="TwelveLabs Marengo Bedrock integration updates"
)

# Look for implementation examples
mcp_github_search_code(
    q="twelvelabs marengo bedrock python"
)
```

## Documentation Validation Checklist

### Before Each Implementation Session
- [ ] Search for latest AWS service documentation
- [ ] Check for recent blog posts or announcements
- [ ] Verify current API parameters and model IDs
- [ ] Look for updated code examples
- [ ] Confirm current pricing and limits

### During Problem Solving
- [ ] Search for current solutions to specific errors
- [ ] Check GitHub issues for similar problems
- [ ] Look for recent Stack Overflow discussions
- [ ] Verify against latest official documentation

### Code Review Process
- [ ] Validate all API calls against current documentation
- [ ] Verify model IDs and parameters are current
- [ ] Check that error handling covers latest error types
- [ ] Confirm security practices are up-to-date

## MCP Tool Selection Guide

### For AWS Documentation
- **Primary**: `mcp_aws_knowledge_mcp_server_aws___search_documentation`
- **Detailed**: `mcp_aws_knowledge_mcp_server_aws___read_documentation`
- **Discovery**: `mcp_aws_knowledge_mcp_server_aws___recommend`

### For Current Updates and News
- **Primary**: `mcp_tavily_mcp_tavily_search`
- **Specific Sites**: `mcp_tavily_mcp_tavily_extract`
- **Comprehensive**: `mcp_tavily_mcp_tavily_crawl`

### For Code Examples
- **Primary**: `mcp_github_search_code`
- **Repositories**: `mcp_github_search_repositories`
- **Specific Files**: `mcp_github_get_file_contents`

### For General Web Information
- **Backup**: `mcp_duckduckgo_mcp_server_search`
- **Content**: `mcp_duckduckgo_mcp_server_fetch_content`

## Error Handling for MCP Tools

### When MCP Tools Fail
```python
def get_current_documentation(topic: str, fallback_info: str = None):
    """Get current documentation with fallback to static knowledge"""
    try:
        # Try MCP AWS documentation first
        result = mcp_aws_knowledge_search(topic)
        return result
    except Exception as e:
        logger.warning(f"MCP tool failed: {e}")
        
        try:
            # Try web search as backup
            result = mcp_tavily_search(topic)
            return result
        except Exception as e2:
            logger.warning(f"Backup MCP tool failed: {e2}")
            
            # Use fallback information with warning
            if fallback_info:
                logger.info("Using fallback information - may be outdated")
                return fallback_info
            else:
                raise Exception("No current documentation available")
```

## Documentation Freshness Indicators

### Always Note When Information Was Retrieved
```python
from datetime import datetime

def log_documentation_source(source: str, url: str = None):
    """Log when and where documentation was retrieved"""
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"Documentation retrieved: {timestamp} from {source}")
    if url:
        logger.info(f"Source URL: {url}")
```

### Flag Potentially Outdated Information
- Mark any information not verified within the last 30 days
- Always prefer MCP-retrieved information over static knowledge
- Document the source and timestamp of all technical decisions
- Update implementation when newer information becomes available

## Success Metrics

### Documentation Currency
- 100% of AWS API calls verified against current documentation
- All model IDs and parameters validated within last 7 days
- Error handling updated based on current service behavior
- Cost calculations based on latest pricing information

### Implementation Quality
- All code examples sourced from current repositories
- Security practices aligned with latest AWS recommendations
- Performance optimizations based on recent best practices
- Integration patterns verified against current service capabilities