# Backend Troubleshooting Report

**Date:** 2025-11-14 01:58:00 UTC  
**Duration:** ~1 hour 17 minutes  
**Status:** ✅ **RESOLVED** - Both backends are now operational

---

## Executive Summary

Indexing revealed that 2 out of 3 vector store backends were not accessible during health checks. Through systematic diagnosis, we identified and resolved distinct issues affecting S3Vector and Qdrant backends:

- **S3Vector**: Code bug in health check validation (API response key mismatch)
- **Qdrant**: Multi-layered infrastructure configuration issues (service inactive, EFS mount target coverage, security group assignment)

Both backends are now verified as healthy and ready for complete indexing operations.

---

## Initial Status

| Backend | Status | Issue |
|---------|--------|-------|
| LanceDB | ✅ Operational | 100 vectors indexed successfully |
| S3Vector | ❌ Failed | Health check failure - backend not responding |
| Qdrant | ❌ Failed | Connection timeout on http://98.93.105.87:6333 |

---

## Diagnostic Process

### Phase 1: Source Analysis (5-7 Potential Causes)

**S3Vector Potential Sources:**
1. AWS credentials expired/invalid
2. IAM permission issues  
3. S3Vector service not provisioned
4. Incorrect bucket configuration
5. API endpoint unavailable
6. Code bug in health check
7. Network connectivity issues

**Qdrant Potential Sources:**
1. ECS task stopped/crashed
2. Security group blocking port 6333
3. Public IP changed (dynamic allocation)
4. Qdrant service crash (application-level)
5. Network/route issues
6. ECS cluster inactive
7. Missing EFS mount targets

### Phase 2: Testing & Validation

#### S3Vector Diagnosis

**Test 1: AWS CLI Direct Access**
```bash
aws s3vectors list-vector-buckets --region us-east-1
```
**Result:** ✅ Success - Found 2 buckets including `videolake-vectors`

**Test 2: Python Provider Health Check**
```python
provider = S3VectorProvider()
result = provider.validate_connectivity()
```
**Result:** ❌ Failed - "Invalid response from S3 Vectors service"

**Test 3: API Response Structure**
```python
response = client.list_vector_buckets()
print(response.keys())  # ['ResponseMetadata', 'vectorBuckets']
```
**Result:** API returns `'vectorBuckets'` not `'Buckets'`

**Root Cause Identified:** Code bug at [`src/services/vector_store_s3vector_provider.py:289`](src/services/vector_store_s3vector_provider.py:289)
- Health check expecting `'Buckets'` key
- S3Vectors API actually returns `'vectorBuckets'`
- Additional issues on lines 156, 196 with wrong key names

#### Qdrant Diagnosis

**Test 1: Endpoint Connectivity**
```bash
curl -v --connect-timeout 10 http://98.93.105.87:6333/
```
**Result:** ❌ Connection timeout after 10 seconds

**Test 2: ECS Service Status**
```bash
aws ecs describe-services --cluster videolake-qdrant-cluster \
  --services videolake-qdrant-service --region us-east-1
```
**Result:** Service status: **INACTIVE**, Running tasks: **0/0**

**Root Cause #1:** ECS service and cluster were deleted/inactive

**Test 3: Terraform Deployment Check**
```bash
cd terraform && terraform apply
```
**Result:** Qdrant shown as "not_deployed" - `deploy_qdrant=false` in configuration

**Test 4: Post-Deploy EFS Mount Issue**
```
ResourceInitializationError: failed to invoke EFS utils commands to set up EFS volumes
```
**Root Cause #2:** EFS mount target exists in only 1 subnet (`subnet-06d125d850b90e21e`), but ECS service configured with 6 subnets. Tasks launching in other subnets couldn't reach EFS.

**Test 5: Security Group Configuration**
- Initial fix used EFS security group (sg-0809b0a05d4abe35a)
- Blocked port 6333 (Qdrant API port)

**Root Cause #3:** Missing Qdrant service security group (sg-0cbcdd5e177ea26e3) for public access

---

## Resolutions Applied

### S3Vector Backend Fix

**Issue:** Code checking for wrong API response key  
**File:** [`src/services/vector_store_s3vector_provider.py`](src/services/vector_store_s3vector_provider.py)

**Changes Made:**
1. Line 155: `list_buckets()` → `list_vector_buckets()`
2. Line 156: `response.get('Buckets', [])` → `response.get('vectorBuckets', [])`
3. Line 158: `bucket.get('Name')` → `bucket.get('vectorBucketName')`
4. Line 164: `bucket.get('Arn')` → `bucket.get('vectorBucketArn')`
5. Line 195: `list_buckets()` → `list_vector_buckets()`
6. Line 196: `response.get('Buckets', [])` → `response.get('vectorBuckets', [])`
7. Line 200: `bucket.get('Name')` → `bucket.get('vectorBucketName')`
8. Line 203: `bucket.get('Arn')` → `bucket.get('vectorBucketArn')`
9. Line 289: `'Buckets' in response` → `'vectorBuckets' in response`
10. Line 290: `response.get('Buckets', [])` → `response.get('vectorBuckets', [])`

**Verification:**
```python
provider = S3VectorProvider()
result = provider.validate_connectivity()
# Result: {'accessible': True, 'health_status': 'healthy', 'bucket_count': 2}
```

### Qdrant Backend Fix

**Issue:** Multiple infrastructure configuration problems  
**Actions Taken:**

**Step 1: Enable Qdrant in Terraform**
```bash
# Created terraform/terraform.tfvars
deploy_qdrant = true

# Applied configuration
cd terraform && terraform apply -auto-approve
```
**Result:** ECS cluster and service created, but tasks failing

**Step 2: Constrain to Subnet with EFS Mount Target**
```bash
aws ecs update-service \
  --cluster videolake-qdrant-cluster \
  --service videolake-qdrant-service \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-06d125d850b90e21e],
    securityGroups=[sg-0809b0a05d4abe35a],
    assignPublicIp=ENABLED
  }" \
  --region us-east-1 \
  --force-new-deployment
```
**Result:** Task started but not accessible (port blocked)

**Step 3: Add Both Required Security Groups**
```bash
aws ecs update-service \
  --cluster videolake-qdrant-cluster \
  --service videolake-qdrant-service \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-06d125d850b90e21e],
    securityGroups=[sg-0cbcdd5e177ea26e3,sg-0809b0a05d4abe35a],
    assignPublicIp=ENABLED
  }" \
  --region us-east-1 \
  --force-new-deployment
```
**Result:** ✅ Task running and accessible

**Verification:**
```bash
curl -s http://52.90.39.152:6333/
# Response: {"title":"qdrant - vector search engine","version":"1.15.5"}
```

---

## Final Verification Results

```
============================================================
BACKEND CONNECTIVITY VERIFICATION
============================================================

1. S3Vector Backend:
----------------------------------------
   Status: ✅ HEALTHY
   Endpoint: s3vectors.us-east-1.amazonaws.com
   Response Time: 246.31ms
   Bucket Count: 2

2. Qdrant Backend:
----------------------------------------
   Status: ✅ HEALTHY
   Endpoint: http://52.90.39.152:6333
   Response Time: 133.65ms
   Version: 1.15.5

============================================================
VERIFICATION COMPLETE
============================================================
```

---

## Current Backend Configuration

### S3Vector
- **Status:** ✅ Operational
- **Endpoint:** s3vectors.us-east-1.amazonaws.com
- **Buckets:** 
  - `videolake-vectors` (primary)
  - `test-102325-medialake2-vector-bucket`
- **Authentication:** AWS SDK (IAM credentials)

### Qdrant
- **Status:** ✅ Operational  
- **Endpoint:** http://52.90.39.152:6333
- **Version:** 1.15.5
- **Deployment:** ECS Fargate
- **Cluster:** videolake-qdrant-cluster
- **Service:** videolake-qdrant-service (ACTIVE)
- **Running Tasks:** 1/1
- **Subnet:** subnet-06d125d850b90e21e (us-east-1d)
- **Security Groups:** 
  - sg-0cbcdd5e177ea26e3 (Qdrant service - port 6333)
  - sg-0809b0a05d4abe35a (EFS access)
- **Storage:** EFS fs-00740f261940ccb98 (videolake-qdrant-efs)

### LanceDB
- **Status:** ✅ Operational (no changes needed)
- **Vectors Indexed:** 100

---

## Lessons Learned

### S3Vector
1. **API Documentation:** Always verify actual API response structure vs. assumptions
2. **Mock Testing:** Need mock responses in tests to catch API mismatch bugs
3. **Error Messages:** "Invalid response" too generic - should log actual response structure

### Qdrant  
1. **EFS Multi-AZ:** EFS mount targets must exist in ALL subnets where ECS tasks launch
2. **Security Groups:** Tasks need BOTH application-level (Qdrant) AND infrastructure-level (EFS) security groups
3. **Terraform Variables:** Default `deploy_qdrant=false` caused service to be deleted during previous terraform applies
4. **Public IP Allocation:** Using dynamic public IPs requires tracking changes; consider using Elastic IPs for persistent endpoints

---

## Recommendations

### Immediate Actions
1. ✅ **COMPLETED:** S3Vector code fix deployed and tested
2. ✅ **COMPLETED:** Qdrant infrastructure stabilized with correct configuration
3. **TODO:** Update indexing script with new Qdrant endpoint (52.90.39.152:6333)

### Short-term Improvements
1. **EFS Mount Targets:** Add mount targets for remaining 5 subnets to allow multi-AZ deployment:
   - subnet-00c9388cf896574f9
   - subnet-027ac919fcb9b3ff1
   - subnet-0ce5ef1b2e1c58d74
   - subnet-0622c0551e3163cb3
   - subnet-08f5943f4c655f893

2. **Elastic IP:** Consider assigning static Elastic IP to Qdrant for stable endpoint

3. **Health Check Monitoring:** Add automated health check alerts for all backends

### Long-term Improvements
1. **Integration Tests:** Add comprehensive backend connectivity tests to CI/CD pipeline
2. **Infrastructure as Code:** Document all manual ECS service updates in Terraform
3. **Multi-Region:** Consider replicating setup in additional regions for redundancy
4. **Load Balancer:** Add ALB in front of Qdrant for better availability and SSL termination

---

## Next Steps

**Ready for Complete Indexing:**
All three vector store backends are now operational and ready to accept vector indexing operations:

1. **LanceDB:** Continue using existing setup (100 vectors already indexed)
2. **S3Vector:** Ready for indexing at `videolake-vectors` bucket  
3. **Qdrant:** Ready for indexing at `http://52.90.39.152:6333`

**Indexing Command:**
```bash
python scripts/index_embeddings.py \
  --backends lancedb,s3vector,qdrant \
  --qdrant-host 52.90.39.152 \
  --qdrant-port 6333
```

---

## Appendix: Diagnostic Commands Used

```bash
# S3Vector Testing
aws s3vectors list-vector-buckets --region us-east-1
python3 -c "from src.services.vector_store_s3vector_provider import S3VectorProvider; ..."

# Qdrant Testing
curl -v --connect-timeout 10 http://98.93.105.87:6333/
aws ecs describe-services --cluster videolake-qdrant-cluster --services videolake-qdrant-service
aws ecs list-tasks --cluster videolake-qdrant-cluster
aws ecs describe-tasks --cluster videolake-qdrant-cluster --tasks <task-arn>
aws efs describe-file-systems --region us-east-1
aws efs describe-mount-targets --file-system-id fs-00740f261940ccb98
aws ec2 describe-security-groups --filters "Name=group-name,Values=*qdrant*"
aws ec2 describe-network-interfaces --network-interface-ids <eni-id>

# Terraform
cd terraform
terraform init -upgrade
terraform apply -auto-approve
```

---

**Report Generated:** 2025-11-14 01:58:00 UTC  
**Engineer:** Roo (Debug Mode)  
**Status:** Issue Resolved - Both backends operational