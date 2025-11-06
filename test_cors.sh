#!/bin/bash
# Test CORS configuration by making a request with Origin header

echo "Testing CORS configuration..."
echo ""

# Test 1: OPTIONS preflight request
echo "1. Testing OPTIONS preflight request:"
curl -X OPTIONS http://localhost:8000/api/resources/registry \
  -H "Origin: http://localhost:5174" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -i "access-control"

echo ""
echo ""

# Test 2: GET request with Origin header
echo "2. Testing GET request with Origin header:"
curl -X GET http://localhost:8000/api/resources/registry \
  -H "Origin: http://localhost:5174" \
  -v 2>&1 | grep -i "access-control"

echo ""
echo ""

# Test 3: Health check
echo "3. Testing health check endpoint:"
curl -X GET http://localhost:8000/api/health \
  -H "Origin: http://localhost:5174" \
  -v 2>&1 | grep -i "access-control"

echo ""
echo ""
echo "CORS test complete!"
echo ""
echo "Expected headers:"
echo "  - access-control-allow-origin: http://localhost:5174"
echo "  - access-control-allow-credentials: true"
echo "  - access-control-allow-methods: GET, POST, PUT, DELETE, PATCH, OPTIONS"
echo "  - access-control-allow-headers: *"

