# OpenSearch Domain Wait Feature

## Overview

Added functionality to wait for OpenSearch domain creation to complete before finishing the Complete Setup process.

## Problem

Previously, when creating an OpenSearch domain as part of Complete Setup:
- Domain creation was initiated
- Setup completed immediately
- Domain took 10-15 minutes to become active in the background
- Users had to manually check domain status

## Solution

Added optional wait functionality that:
1. ✅ Monitors domain creation progress
2. ✅ Shows real-time status updates
3. ✅ Waits for domain to become fully active
4. ✅ Provides progress bar and status messages
5. ✅ Has configurable timeout (default: 20 minutes)
6. ✅ Allows users to skip waiting if desired

## Features

### 1. Wait Checkbox

Added checkbox in Complete Setup form:
```
☑ Wait for OpenSearch Domain to Complete
```

**Options**:
- **Checked (default)**: Wait for domain to become active before completing setup
- **Unchecked**: Create domain in background, complete setup immediately

### 2. Progress Monitoring

When waiting is enabled, the UI shows:
- **Progress bar**: Visual indication of elapsed time
- **Status messages**: Real-time updates on domain state
  - "Creating domain..."
  - "Configuring domain..."
  - "Finalizing domain..."
  - "Domain active! Endpoint: ..."

### 3. Status Checks

The wait function checks domain status every 30 seconds:
- **Created**: Domain resource created
- **Processing**: Domain being configured
- **Endpoint**: Domain endpoint available
- **Active**: Domain ready for use

### 4. Timeout Handling

**Default timeout**: 20 minutes

If timeout is reached:
- Warning message displayed
- Setup completes successfully
- Domain continues creating in background
- User can check status manually

## Implementation

### New Method: `_wait_for_opensearch_domain_active()`

```python
def _wait_for_opensearch_domain_active(
    self, 
    domain_name: str, 
    max_wait_minutes: int = 20
) -> bool:
    """
    Wait for OpenSearch domain to become active.
    
    Args:
        domain_name: Name of the domain to wait for
        max_wait_minutes: Maximum time to wait (default: 20)
        
    Returns:
        True if domain became active, False if timeout
    """
```

**Features**:
- Checks domain status every 30 seconds
- Updates progress bar based on elapsed time
- Shows status messages for each state
- Handles errors gracefully
- Returns True when domain is active
- Returns False on timeout or error

### Updated Method: `_create_opensearch_domain_real()`

**New parameter**: `wait_for_active: bool = True`

```python
def _create_opensearch_domain_real(
    self,
    domain_name: str,
    s3_vector_bucket_arn: str,
    wait_for_active: bool = True
) -> Tuple[bool, str]:
```

**Behavior**:
- If `wait_for_active=True`: Waits for domain to become active
- If `wait_for_active=False`: Returns immediately after creation

### Updated Method: `_create_complete_setup_real()`

**New parameter**: `wait_for_opensearch: bool = True`

```python
def _create_complete_setup_real(
    self,
    setup_name: str,
    region: str,
    create_opensearch: bool = False,
    wait_for_opensearch: bool = True
) -> bool:
```

**Passes wait parameter** to OpenSearch domain creation.

## User Experience

### With Wait Enabled (Default)

1. User creates Complete Setup with OpenSearch
2. S3Vector bucket created ✅
3. S3Vector index created ✅
4. S3 bucket created ✅
5. OpenSearch domain creation initiated
6. **Progress bar appears**: "Waiting for domain to become active..."
7. **Status updates every 30 seconds**:
   - "Creating domain... (30s / 1200s)"
   - "Configuring domain... (300s / 1200s)"
   - "Finalizing domain... (600s / 1200s)"
8. **Domain becomes active**: "✅ OpenSearch domain is now active!"
9. **Setup completes**: All resources ready to use

**Total time**: 10-15 minutes (actual domain creation time)

### With Wait Disabled

1. User creates Complete Setup with OpenSearch
2. S3Vector bucket created ✅
3. S3Vector index created ✅
4. S3 bucket created ✅
5. OpenSearch domain creation initiated
6. **Setup completes immediately**: "ℹ️ Domain creation will continue in background"
7. User can check status manually later

**Total time**: ~30 seconds (just resource creation, no waiting)

## Status Checking

### During Wait

Progress bar shows:
```
⏱️ Configuring domain... (300s / 1200s)
[████████░░░░░░░░░░░░] 25%
```

### After Completion

Success message:
```
✅ OpenSearch domain is now active!
Endpoint: search-s3vector-1759187028-domain-xxxxx.us-east-1.es.amazonaws.com
```

### On Timeout

Warning message:
```
⚠️ Domain creation is taking longer than expected. Check status manually.
```

## Manual Status Check

If user skips waiting or timeout occurs, they can check status:

```bash
aws opensearch describe-domain \
  --domain-name s3vector-1759187028-domain \
  --region us-east-1 \
  --query 'DomainStatus.[Processing,Created,Endpoint]'
```

**Expected output when ready**:
```json
[
  false,  // Processing
  true,   // Created
  "search-s3vector-1759187028-domain-xxxxx.us-east-1.es.amazonaws.com"  // Endpoint
]
```

## Configuration

### Timeout Duration

Default: 20 minutes

To change timeout, modify the call:
```python
self._wait_for_opensearch_domain_active(domain_name, max_wait_minutes=30)
```

### Check Interval

Default: 30 seconds

To change interval, modify in `_wait_for_opensearch_domain_active()`:
```python
check_interval = 60  # Check every 60 seconds
```

## Error Handling

### Domain Not Found

If domain doesn't appear immediately:
- Continues waiting
- Shows: "Waiting for domain to appear..."

### API Errors

If AWS API returns error:
- Logs error
- Returns False
- Setup continues (domain may still be creating)

### Timeout

If max wait time exceeded:
- Shows warning
- Returns False
- Setup completes successfully
- Domain continues creating in background

## Benefits

1. ✅ **Better UX**: Users know when domain is ready
2. ✅ **No Manual Checking**: Automatic status monitoring
3. ✅ **Clear Progress**: Visual feedback during wait
4. ✅ **Flexible**: Can skip waiting if desired
5. ✅ **Safe**: Handles errors and timeouts gracefully
6. ✅ **Complete Setup**: All resources ready when setup finishes

## Testing

### Test Wait Functionality

1. Create Complete Setup with OpenSearch
2. Check "Wait for OpenSearch Domain to Complete"
3. Click "Create Complete Setup"
4. Observe progress bar and status messages
5. Wait for completion (10-15 minutes)
6. Verify domain is active

### Test Skip Wait

1. Create Complete Setup with OpenSearch
2. Uncheck "Wait for OpenSearch Domain to Complete"
3. Click "Create Complete Setup"
4. Setup completes immediately
5. Check domain status manually after 10-15 minutes

### Test Timeout

1. Set very short timeout (e.g., 1 minute)
2. Create Complete Setup with OpenSearch
3. Wait for timeout
4. Verify warning message appears
5. Verify setup completes successfully

## Files Modified

- `frontend/components/simplified_resource_manager.py`:
  - Added `_wait_for_opensearch_domain_active()` method
  - Updated `_create_opensearch_domain_real()` with wait parameter
  - Updated `_create_complete_setup_real()` with wait parameter
  - Added wait checkbox in UI

## Summary

The OpenSearch domain wait feature provides:
- ✅ Optional waiting for domain to become active
- ✅ Real-time progress monitoring
- ✅ Clear status messages
- ✅ Configurable timeout
- ✅ Graceful error handling
- ✅ Better user experience

**Default behavior**: Wait for domain to complete (recommended)  
**Alternative**: Skip waiting and check status manually

This ensures users have a complete, ready-to-use setup when the Complete Setup process finishes.

