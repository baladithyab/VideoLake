# CORS Troubleshooting Guide

## Overview

This guide helps resolve Cross-Origin Resource Sharing (CORS) issues between the React frontend (http://localhost:5174) and FastAPI backend (http://localhost:8000).

## CORS Configuration

The FastAPI backend is configured with CORS middleware in `src/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server (alternative port)
        "http://localhost:5174",  # Vite dev server (default)
        "http://127.0.0.1:5174",  # Alternative localhost
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)
```

## Common CORS Errors

### Error 1: "CORS header 'Access-Control-Allow-Origin' missing"

**Symptom**: Browser console shows:
```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource at http://localhost:8000/api/resources/registry. (Reason: CORS header 'Access-Control-Allow-Origin' missing).
```

**Causes**:
1. Backend server is not running
2. CORS middleware not properly configured
3. Request is being blocked before reaching CORS middleware

**Solutions**:

1. **Verify backend is running**:
   ```bash
   curl http://localhost:8000/api/health
   ```
   Should return: `{"status":"healthy",...}`

2. **Restart the backend server**:
   ```bash
   # Stop any running instances
   pkill -f uvicorn
   
   # Start fresh
   python run_api.py
   ```

3. **Test CORS headers**:
   ```bash
   ./test_cors.sh
   ```
   Should show `access-control-allow-origin: http://localhost:5174`

### Error 2: "Preflight request didn't succeed"

**Symptom**: Browser console shows:
```
Cross-Origin Request Blocked: The Same Origin Policy disallows reading the remote resource. (Reason: CORS preflight channel did not succeed).
```

**Causes**:
1. OPTIONS request is failing
2. Backend is not responding to preflight requests

**Solutions**:

1. **Test OPTIONS request manually**:
   ```bash
   curl -X OPTIONS http://localhost:8000/api/resources/registry \
     -H "Origin: http://localhost:5174" \
     -H "Access-Control-Request-Method: GET" \
     -v
   ```

2. **Check backend logs** for errors during OPTIONS handling

3. **Verify CORS middleware is registered** before route handlers in `src/api/main.py`

### Error 3: "Credentials flag is 'true', but 'Access-Control-Allow-Credentials' header is ''"

**Symptom**: Browser console shows credential-related CORS error

**Causes**:
1. `allow_credentials=True` not set in CORS middleware
2. Frontend is sending credentials but backend doesn't allow them

**Solutions**:

1. **Verify CORS configuration** has `allow_credentials=True`

2. **Check frontend API client** (`frontend/src/api/client.ts`):
   ```typescript
   const apiClient = axios.create({
     baseURL: 'http://localhost:8000',
     withCredentials: true,  // Should match backend allow_credentials
   });
   ```

## Testing CORS

### Manual Testing

1. **Test with curl**:
   ```bash
   # Test GET request
   curl -X GET http://localhost:8000/api/resources/registry \
     -H "Origin: http://localhost:5174" \
     -v 2>&1 | grep -i "access-control"
   
   # Test OPTIONS preflight
   curl -X OPTIONS http://localhost:8000/api/resources/registry \
     -H "Origin: http://localhost:5174" \
     -H "Access-Control-Request-Method: GET" \
     -v 2>&1 | grep -i "access-control"
   ```

2. **Use the test script**:
   ```bash
   ./test_cors.sh
   ```

3. **Check browser DevTools**:
   - Open browser DevTools (F12)
   - Go to Network tab
   - Make a request from the frontend
   - Click on the request
   - Check "Response Headers" for CORS headers

### Expected Headers

A successful CORS response should include:

```
access-control-allow-origin: http://localhost:5174
access-control-allow-credentials: true
access-control-allow-methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
access-control-allow-headers: *
access-control-expose-headers: *
access-control-max-age: 3600
```

## Debugging Steps

### Step 1: Verify Backend is Running

```bash
# Check if backend is running
curl http://localhost:8000/

# Should return:
# {"message":"S3Vector API","version":"1.0.0","status":"running"}
```

### Step 2: Check Backend Logs

The backend logs all requests with origin information:

```bash
# Start backend and watch logs
python run_api.py

# Look for lines like:
# INFO: Request: GET /api/resources/registry
# INFO: Origin: http://localhost:5174
# INFO: Response: 200 (took 0.05s)
```

### Step 3: Verify Frontend Configuration

Check `frontend/src/api/client.ts`:

```typescript
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',  // Should match backend URL
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Step 4: Clear Browser Cache

Sometimes browsers cache CORS preflight responses:

1. Open DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

Or use incognito/private mode to test without cache.

### Step 5: Check for Proxy Issues

If using a proxy or reverse proxy, ensure it's not stripping CORS headers.

## Advanced Troubleshooting

### Enable Verbose Logging

Add more detailed logging to `src/api/main.py`:

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging."""
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"Headers: {dict(request.headers)}")
    
    response = await call_next(request)
    
    logger.info(f"Response: {response.status_code}")
    logger.info(f"Response Headers: {dict(response.headers)}")
    
    return response
```

### Test with Different Origins

If `http://localhost:5174` doesn't work, try:

1. `http://127.0.0.1:5174`
2. `http://localhost:3000`
3. Add your specific origin to `allow_origins` in `src/api/main.py`

### Disable CORS Temporarily (Development Only)

For testing purposes only, you can allow all origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # WARNING: Only for development!
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**⚠️ WARNING**: Never use `allow_origins=["*"]` in production!

## Production Considerations

For production deployment:

1. **Restrict origins** to your actual domain:
   ```python
   allow_origins=["https://yourdomain.com"]
   ```

2. **Enable HTTPS**:
   - Use HTTPS for both frontend and backend
   - Update origins to use `https://`

3. **Set specific methods**:
   ```python
   allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"]
   ```

4. **Limit headers**:
   ```python
   allow_headers=["Content-Type", "Authorization"]
   ```

5. **Consider security headers**:
   - Add `Strict-Transport-Security`
   - Add `X-Content-Type-Options`
   - Add `X-Frame-Options`

## Quick Fix Checklist

- [ ] Backend server is running on http://localhost:8000
- [ ] Frontend is running on http://localhost:5174
- [ ] CORS middleware is configured in `src/api/main.py`
- [ ] `allow_origins` includes `http://localhost:5174`
- [ ] `allow_credentials=True` is set
- [ ] `allow_methods` includes the HTTP method you're using
- [ ] Backend has been restarted after CORS configuration changes
- [ ] Browser cache has been cleared
- [ ] No proxy is interfering with requests
- [ ] Backend logs show the request is being received

## Getting Help

If you're still experiencing CORS issues:

1. Run `./test_cors.sh` and share the output
2. Check backend logs for errors
3. Share browser console errors (F12 → Console)
4. Share network request details (F12 → Network → Click request → Headers)

## References

- [FastAPI CORS Documentation](https://fastapi.tiangolo.com/tutorial/cors/)
- [MDN CORS Guide](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [CORS Preflight Requests](https://developer.mozilla.org/en-US/docs/Glossary/Preflight_request)

