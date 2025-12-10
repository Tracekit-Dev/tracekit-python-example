#!/bin/bash

# TraceKit Python Test - Request Generator
# This script sends various requests to test all endpoints

BASE_URL="http://localhost:5000"

echo "======================================"
echo "TraceKit Python Test - Request Generator"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to make a request
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4

    echo -e "${BLUE}Testing:${NC} $description"
    echo -e "  ${method} ${endpoint}"

    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" "${BASE_URL}${endpoint}")
    else
        response=$(curl -s -w "\n%{http_code}" -X ${method} "${BASE_URL}${endpoint}" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "  ${GREEN}✓${NC} Status: $http_code"
    else
        echo -e "  ${RED}✗${NC} Status: $http_code"
    fi

    echo ""
    sleep 0.5
}

# Test 1: Homepage
make_request "GET" "/" "" "Homepage"

# Test 2: Health check
make_request "GET" "/health" "" "Health Check"

# Test 3: List all users
make_request "GET" "/api/users" "" "List All Users"

# Test 4: Get specific users
make_request "GET" "/api/users/1" "" "Get User 1 (Alice)"
make_request "GET" "/api/users/2" "" "Get User 2 (Bob)"

# Test 5: Get non-existent user (should return 404)
make_request "GET" "/api/users/999" "" "Get Non-Existent User (404)"

# Test 6: List all orders
make_request "GET" "/api/orders" "" "List All Orders"

# Test 7: Get specific order
make_request "GET" "/api/orders/1" "" "Get Order 1"

# Test 8: Create new order
make_request "POST" "/api/orders" \
    '{"user_id": 1, "product": "Monitor", "amount": 399.99}' \
    "Create New Order"

# Test 9: Test slow endpoint
echo -e "${BLUE}Testing:${NC} Slow Endpoint (will take 1.5-3 seconds)"
echo "  GET /api/slow"
make_request "GET" "/api/slow" "" "Slow Endpoint"

# Test 10: Test error endpoint (expected to fail)
echo -e "${BLUE}Testing:${NC} Error Endpoint (expected error)"
echo "  GET /api/error"
make_request "GET" "/api/error" "" "Error Endpoint"

# Test 11: Test random endpoint (multiple times)
echo -e "${BLUE}Testing:${NC} Random Endpoint (5 requests)"
for i in {1..5}; do
    echo "  Request $i/5"
    make_request "GET" "/api/random" "" "Random Endpoint #$i"
done

# Test 12: Test checkout flow
make_request "POST" "/api/checkout" \
    '{
        "user_id": 1,
        "items": [
            {"product": "Laptop", "price": 1299.99},
            {"product": "Mouse", "price": 29.99}
        ],
        "total": 1329.98
    }' \
    "Checkout Flow (with snapshots)"

# Test 13: Load test - multiple rapid requests
echo -e "${BLUE}Load Test:${NC} Sending 10 rapid requests"
for i in {1..10}; do
    curl -s "${BASE_URL}/api/users" > /dev/null &
    curl -s "${BASE_URL}/api/orders" > /dev/null &
    curl -s "${BASE_URL}/health" > /dev/null &
done
wait
echo -e "  ${GREEN}✓${NC} Load test complete (30 requests sent)"
echo ""

echo "======================================"
echo "Testing Complete!"
echo "======================================"
echo ""
echo "Check your TraceKit dashboard to view traces:"
echo "  - Service: naturalwrite"
echo "  - Total requests: ~25+"
echo "  - Includes errors, slow requests, and code snapshots"
echo ""
