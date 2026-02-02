# TraceKit Python Test Application

This is a Flask-based test application for demonstrating TraceKit APM 
functionality with Python.

## Features

- ✅ HTTP request tracing
- ✅ Database query simulation with spans
- ✅ Error tracking and exception handling
- ✅ Code monitoring with breakpoints
- ✅ Custom span creation
- ✅ Slow endpoint simulation
- ✅ Random behavior testing
- ✅ Checkout flow with snapshots
- ✅ Metrics tracking (Counter, Gauge, Histogram)

## Metrics

The application demonstrates TraceKit's metrics API by tracking key performance indicators:

### Metrics Tracked

#### HTTP Request Metrics
- **`http.requests.total`** (Counter) - Total number of HTTP requests
- **`http.requests.active`** (Gauge) - Number of currently active requests
- **`http.request.duration`** (Histogram) - Request duration in milliseconds
- **`http.errors.total`** (Counter) - Total number of HTTP errors

#### Database Metrics
- **`db.queries.total`** (Counter) - Total number of database queries
- **`db.query.duration`** (Histogram) - Database query duration in milliseconds

### How Metrics Work

Metrics are initialized at application startup:

```python
# Initialize metrics
request_counter = client.counter("http.requests.total", {"service": "python-test-app"})
active_requests_gauge = client.gauge("http.requests.active", {"service": "python-test-app"})
request_duration_histogram = client.histogram("http.request.duration", {"unit": "ms"})
```

And used in endpoint handlers:

```python
@app.route('/api/orders', methods=['POST'])
def create_order():
    start_time = time.time()

    # Track active requests
    active_requests_gauge.inc()

    try:
        # Process order...
        request_counter.inc()
        return jsonify(new_order), 201
    finally:
        # Always record metrics even if there's an error
        active_requests_gauge.dec()
        duration_ms = (time.time() - start_time) * 1000
        request_duration_histogram.record(duration_ms)
```

### Viewing Metrics

Metrics are automatically exported to TraceKit and can be viewed in your dashboard:

1. Navigate to the Metrics section in TraceKit dashboard
2. Filter by service name: `python-test-app`
3. View metric trends, distributions, and aggregations

### Testing Metrics

Create some orders to generate metrics:

```bash
# Create multiple orders to generate metrics
for i in {1..10}; do
  curl -X POST http://localhost:5001/api/orders \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": 1, \"product\": \"Item $i\", \"amount\": 99.99}"
done
```

You'll see:
- `http.requests.total` increase by 10
- `http.requests.active` spike during processing
- `http.request.duration` histogram showing distribution of request times

## Configuration

The application is configured to send traces to TraceKit:

- **Endpoint:** `https://app.tracekit.dev/v1/traces`
- **Service Name:** `python-test-app`
- **Sample Rate:** 100% (all requests traced)
- **Code Monitoring:** Enabled

Configuration is stored in `.env` file.

## Installation

### 1. Install Dependencies

```bash
cd python-test
pip install -r requirements.txt
```

This will install all required packages including the TraceKit Python APM SDK.

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your TraceKit API key
# TRACEKIT_API_KEY=your-api-key-here
```

Get your API key from: https://app.tracekit.dev

## Running

```bash
python app.py
```

The application will start on `http://localhost:5000`

## Available Endpoints

### Information

- **GET /** - Homepage with API information
- **GET /health** - Health check endpoint

### Users

- **GET /api/users** - List all users
  - Returns array of users
  - Includes database query simulation

- **GET /api/users/<id>** - Get user by ID
  - Returns user object
  - Includes code monitoring snapshot
  - Returns 404 if user not found

### Orders

- **GET /api/orders** - List all orders
  - Returns array of orders
  - Includes database query simulation

- **GET /api/orders/<id>** - Get order by ID
  - Returns order object
  - Returns 404 if order not found

- **POST /api/orders** - Create new order
  - Request body: `{"user_id": 1, "product": "Item", "amount": 99.99}`
  - Returns created order with 201 status

### Testing

- **GET /api/slow** - Slow endpoint (1.5-3 seconds)
  - Tests performance monitoring
  - Returns duration information

- **GET /api/error** - Error endpoint
  - Randomly throws different error types
  - Tests error tracking

- **GET /api/random** - Random behavior
  - Randomly returns success, slow response, or error
  - Tests unpredictable scenarios

### Checkout (Code Monitoring Demo)

- **POST /api/checkout** - Checkout process
  - Request body:
    ```json
    {
      "user_id": 1,
      "items": [{"product": "Laptop", "price": 1299.99}],
      "total": 1299.99
    }
    ```
  - Demonstrates code monitoring with multiple snapshots
  - Includes validation, payment processing, and order creation
  - Returns order and payment information

## Testing the Application

### 1. Basic Request

```bash
curl http://localhost:5000/
```

### 2. List Users

```bash
curl http://localhost:5000/api/users
```

### 3. Get Specific User

```bash
curl http://localhost:5000/api/users/1
```

### 4. Create Order

```bash
curl -X POST http://localhost:5000/api/orders \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "product": "Laptop", "amount": 1299.99}'
```

### 5. Test Slow Endpoint

```bash
curl http://localhost:5000/api/slow
```

### 6. Test Error Tracking

```bash
curl http://localhost:5000/api/error
```

### 7. Test Checkout Flow (Code Monitoring)

```bash
curl -X POST http://localhost:5000/api/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "items": [{"product": "Laptop", "price": 1299.99}],
    "total": 1299.99
  }'
```

### 8. Generate Load

```bash
# Run multiple requests
for i in {1..10}; do
  curl http://localhost:5000/api/users
  curl http://localhost:5000/api/orders
  curl http://localhost:5000/api/random
done
```

## What Gets Traced

### Automatic Tracing

- All HTTP requests (method, URL, status code, duration)
- Request headers (user agent, client IP)
- Response attributes
- Errors and exceptions with stack traces

### Custom Spans

- Database queries with operation details
- Payment processing
- Order creation
- Slow operations
- User validation

### Code Monitoring Snapshots

- User retrieval operations (`get-user` label)
- Checkout start (`checkout-start` label)
- Payment processing (`payment-processing` label)
- Checkout completion (`checkout-complete` label)

## Viewing Traces

1. Ensure you have a valid TraceKit API key configured in `.env`
2. Run this test application
3. Make requests to the endpoints
4. View traces in your TraceKit dashboard at https://app.tracekit.dev

The traces will show:
- HTTP request details
- Custom spans with attributes
- Nested span hierarchy
- Error stack traces
- Code monitoring snapshots with variables

## Simulated Data

### Users

```json
[
  {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": 
"admin"},
  {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": 
"user"},
  {"id": 3, "name": "Charlie Brown", "email": "charlie@example.com", 
"role": "user"},
  {"id": 4, "name": "Diana Prince", "email": "diana@example.com", "role": 
"moderator"}
]
```

### Orders

```json
[
  {"id": 1, "user_id": 1, "product": "Laptop", "amount": 1299.99, 
"status": "completed"},
  {"id": 2, "user_id": 2, "product": "Mouse", "amount": 29.99, "status": 
"pending"},
  {"id": 3, "user_id": 1, "product": "Keyboard", "amount": 89.99, 
"status": "completed"}
]
```

## Troubleshooting

### Traces not appearing?

1. Verify API key in `.env` file
2. Check endpoint URL in `.env` file (should be 
`https://app.tracekit.dev/v1/traces`)
3. Look for errors in Flask console output
4. Ensure your API key is valid at https://app.tracekit.dev

### Import errors?

Make sure you've installed all dependencies including the TraceKit Python 
APM SDK:

```bash
pip install -r requirements.txt
```

### Module not found?

Ensure all dependencies are installed. If you encounter issues with the 
TraceKit SDK, you can install it manually:

#### Installation
pip install tracekit-apm

#### Framework-Specific Installation

#### Flask
pip install tracekit-apm[flask]

#### FastAPI
pip install tracekit-apm[fastapi]

#### Django
pip install tracekit-apm[django]

#### All frameworks
pip install tracekit-apm[all]

## Architecture

```
Flask App (app.py)
    ↓
TraceKit Middleware
    ↓
TracekitClient (tracekit/client.py)
    ↓
OpenTelemetry SDK
    ↓
OTLP HTTP Exporter
    ↓
TraceKit Backend (api.tracekit.dev)
```

## Notes

- All requests are traced (100% sample rate)
- Code monitoring is enabled for snapshot capture
- The app uses simulated in-memory data (no real database)
- Delays are added to simulate realistic operations
- Errors are intentional for testing error tracking

## Next Steps

1. Start the application
2. Make some test requests
3. View traces in TraceKit dashboard
4. Test code monitoring by setting breakpoints
5. Generate load to see performance metrics
