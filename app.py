"""
TraceKit Python Test Application

This is a Flask application that demonstrates TraceKit APM functionality.
It sends traces to a local TraceKit instance.

Usage:
    pip install -r requirements.txt
    python app.py
"""

import os
import sys
import time
import random
import requests
from flask import Flask, jsonify, request, abort
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path to import tracekit
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python-apm'))

import tracekit
from tracekit.middleware.flask import init_flask_app

# Create Flask app
app = Flask(__name__)

# Service URLs for cross-service communication
GO_SERVICE_URL = 'http://localhost:8082'
NODE_SERVICE_URL = 'http://localhost:8084'
LARAVEL_SERVICE_URL = 'http://localhost:8083'
PHP_SERVICE_URL = 'http://localhost:8086'

# Initialize TraceKit with local configuration
print("\n" + "="*60)
print("Initializing TraceKit APM...")
print("="*60)

# Validate required environment variables
API_KEY = os.getenv('TRACEKIT_API_KEY')
if not API_KEY:
    print("❌ ERROR: TRACEKIT_API_KEY environment variable is required.")
    print("   Please copy .env.example to .env and add your API key.")
    print("   Get your API key from: https://app.tracekit.dev")
    sys.exit(1)

SERVICE_NAME = os.getenv('SERVICE_NAME', 'python-test-app')

client = tracekit.init(
    api_key=API_KEY,
    service_name=SERVICE_NAME,
    endpoint=os.getenv('TRACEKIT_ENDPOINT', 'http://localhost:8081/v1/traces'),
    enabled=True,
    sample_rate=1.0,  # Trace 100% of requests for testing
    enable_code_monitoring=True,
    # Map localhost URLs to actual service names for service graph
    service_name_mappings={
        'localhost:8082': 'go-test-app',
        'localhost:8084': 'node-test-app',
        'localhost:8083': 'laravel-test-app',
        'localhost:8086': 'php-test-app',
    }
)

print(f"✓ API Key: {API_KEY[:20]}...")
print(f"✓ Service: {SERVICE_NAME}")
print(f"✓ Endpoint: {os.getenv('TRACEKIT_ENDPOINT', 'http://localhost:8081/v1/traces')}")
print(f"✓ Code Monitoring: Enabled")
print(f"✓ Service Mappings: go, node, laravel, php")
print("="*60 + "\n")

# Add TraceKit middleware
init_flask_app(app, client)

# Simulated database
USERS_DB = [
    {"id": 1, "name": "Alice Johnson", "email": "alice@example.com", "role": "admin"},
    {"id": 2, "name": "Bob Smith", "email": "bob@example.com", "role": "user"},
    {"id": 3, "name": "Charlie Brown", "email": "charlie@example.com", "role": "user"},
    {"id": 4, "name": "Diana Prince", "email": "diana@example.com", "role": "moderator"},
]

ORDERS_DB = [
    {"id": 1, "user_id": 1, "product": "Laptop", "amount": 1299.99, "status": "completed"},
    {"id": 2, "user_id": 2, "product": "Mouse", "amount": 29.99, "status": "pending"},
    {"id": 3, "user_id": 1, "product": "Keyboard", "amount": 89.99, "status": "completed"},
]


# Routes

@app.route('/')
def index():
    """Homepage with available endpoints"""
    return jsonify({
        "service": SERVICE_NAME,
        "message": "TraceKit Python Test Application",
        "endpoints": [
            "GET /",
            "GET /health",
            "GET /api/users",
            "GET /api/users/<id>",
            "GET /api/orders",
            "GET /api/orders/<id>",
            "POST /api/orders",
            "GET /api/slow",
            "GET /api/error",
            "GET /api/random",
            "POST /api/checkout",
            "GET /api/data          - Data endpoint (called by other services)",
            "GET /api/call-go       - Call Go service",
            "GET /api/call-node     - Call Node service",
            "GET /api/call-all      - Call all services (chain test)",
        ],
        "tracekit": {
            "service_name": SERVICE_NAME,
            "endpoint": os.getenv('TRACEKIT_ENDPOINT', 'http://localhost:8081/v1/traces'),
            "monitoring_enabled": True
        }
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "python-test-app",
        "timestamp": time.time()
    })


@app.route('/api/users')
def list_users():
    """List all users with simulated database query"""
    from opentelemetry import trace

    # Get current tracer
    tracer = trace.get_tracer(__name__)

    # Create a custom child span using context manager
    with tracer.start_as_current_span('db.query.users') as span:
        span.set_attributes({
            'db.system': 'postgresql',
            'db.operation': 'SELECT',
            'db.table': 'users',
            'db.statement': 'SELECT * FROM users'
        })

        # Simulate database query delay
        time.sleep(random.uniform(0.02, 0.08))

        span.set_attributes({
            'db.rows': len(USERS_DB),
            'db.duration_ms': random.randint(20, 80)
        })

    return jsonify({
        "count": len(USERS_DB),
        "users": USERS_DB
    })


@app.route('/api/users/<int:user_id>')
def get_user(user_id):
    """Get a specific user by ID"""
    from opentelemetry import trace

    # Get current tracer
    tracer = trace.get_tracer(__name__)

    # Capture snapshot for debugging
    if client.get_snapshot_client():
        try:
            client.capture_snapshot('get-user', {
                'user_id': user_id,
                'request_path': request.path,
                'request_method': request.method
            })
        except Exception as e:
            print(f"Snapshot error: {e}")

    # Create child span using context manager
    with tracer.start_as_current_span('db.query.user') as span:
        span.set_attributes({
            'db.system': 'postgresql',
            'db.operation': 'SELECT',
            'db.table': 'users',
            'db.statement': 'SELECT * FROM users WHERE id = ?',
            'user.id': user_id
        })

        time.sleep(random.uniform(0.01, 0.05))

        user = next((u for u in USERS_DB if u['id'] == user_id), None)

        if user is None:
            span.set_attribute('user.found', False)
            abort(404, description=f"User {user_id} not found")

        span.set_attributes({
            'user.found': True,
            'user.role': user['role']
        })

    return jsonify(user)


@app.route('/api/orders')
def list_orders():
    """List all orders"""
    span = client.start_span('db.query.orders', {
        'db.system': 'postgresql',
        'db.operation': 'SELECT',
        'db.table': 'orders'
    })

    time.sleep(random.uniform(0.03, 0.07))

    client.end_span(span, {
        'db.rows': len(ORDERS_DB)
    })

    return jsonify({
        "count": len(ORDERS_DB),
        "orders": ORDERS_DB
    })


@app.route('/api/orders/<int:order_id>')
def get_order(order_id):
    """Get a specific order by ID"""
    span = client.start_span('db.query.order', {
        'db.system': 'postgresql',
        'db.operation': 'SELECT',
        'db.table': 'orders',
        'order.id': order_id
    })

    time.sleep(random.uniform(0.01, 0.04))

    order = next((o for o in ORDERS_DB if o['id'] == order_id), None)

    if order is None:
        client.end_span(span, {'order.found': False})
        abort(404, description=f"Order {order_id} not found")

    client.end_span(span, {
        'order.found': True,
        'order.status': order['status']
    })

    return jsonify(order)


@app.route('/api/orders', methods=['POST'])
def create_order():
    """Create a new order"""
    data = request.get_json()

    # Validate input
    if not data or 'user_id' not in data or 'product' not in data or 'amount' not in data:
        abort(400, description="Missing required fields: user_id, product, amount")

    # Create order span
    span = client.start_span('create-order', {
        'user.id': data['user_id'],
        'product.name': data['product'],
        'order.amount': data['amount']
    })

    # Simulate database insert
    time.sleep(random.uniform(0.05, 0.15))

    new_order = {
        "id": len(ORDERS_DB) + 1,
        "user_id": data['user_id'],
        "product": data['product'],
        "amount": data['amount'],
        "status": "pending"
    }

    ORDERS_DB.append(new_order)

    client.end_span(span, {
        'order.id': new_order['id'],
        'order.created': True
    })

    return jsonify(new_order), 201


@app.route('/api/slow')
def slow_endpoint():
    """Simulate a slow endpoint"""
    span = client.start_span('slow-computation', {
        'operation.type': 'heavy-computation'
    })

    # Simulate slow work
    duration = random.uniform(1.5, 3.0)
    time.sleep(duration)

    client.end_span(span, {
        'operation.duration_ms': int(duration * 1000)
    })

    return jsonify({
        "message": "This was slow",
        "duration_seconds": round(duration, 2)
    })


@app.route('/api/error')
def error_endpoint():
    """Endpoint that throws an error for testing error tracking"""
    # This error will be automatically captured by TraceKit
    error_types = [
        ValueError("Invalid value provided"),
        KeyError("Missing required key"),
        RuntimeError("Something went wrong in processing"),
        Exception("Generic test error")
    ]

    raise random.choice(error_types)


@app.route('/api/random')
def random_endpoint():
    """Endpoint with random behavior"""
    action = random.choice(['success', 'slow', 'error'])

    if action == 'success':
        span = client.start_span('random-success')
        time.sleep(random.uniform(0.01, 0.1))
        client.end_span(span)
        return jsonify({"result": "success", "action": action})

    elif action == 'slow':
        span = client.start_span('random-slow')
        time.sleep(random.uniform(0.5, 1.5))
        client.end_span(span)
        return jsonify({"result": "slow", "action": action})

    else:  # error
        raise Exception("Random error occurred!")


@app.route('/api/checkout', methods=['POST'])
def checkout():
    """Simulate a checkout process with code monitoring"""
    from opentelemetry import trace
    import asyncio

    tracer = trace.get_tracer(__name__)

    data = request.get_json()

    if not data:
        abort(400, description="Request body required")

    user_id = data.get('user_id')
    items = data.get('items', [])
    total = data.get('total', 0)

    # Capture snapshot at checkout start (sync wrapper)
    if client.get_snapshot_client():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.capture_snapshot('checkout-start', {
                'user_id': user_id,
                'items_count': len(items),
                'total_amount': total,
                'timestamp': time.time()
            }))
            loop.close()
        except Exception as e:
            print(f"Snapshot error: {e}")

    # Validate user - nested span
    with tracer.start_as_current_span('validate-user') as validate_span:
        validate_span.set_attribute('user.id', user_id)
        time.sleep(random.uniform(0.02, 0.05))

        user = next((u for u in USERS_DB if u['id'] == user_id), None)
        if not user:
            validate_span.set_attribute('validation.result', 'failed')
            abort(400, description="Invalid user ID")

        validate_span.set_attribute('validation.result', 'success')

    # Process payment - nested span
    with tracer.start_as_current_span('process-payment') as payment_span:
        payment_span.set_attributes({
            'payment.amount': total,
            'user.id': user_id
        })

        # Capture snapshot during payment
        if client.get_snapshot_client():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(client.capture_snapshot('payment-processing', {
                    'user_id': user_id,
                    'amount': total,
                    'user_email': user['email']
                }))
                loop.close()
            except Exception as e:
                print(f"Snapshot error: {e}")

        time.sleep(random.uniform(0.3, 0.7))

        payment_result = {
            'payment_id': f'pay_{int(time.time())}_{random.randint(1000, 9999)}',
            'status': 'success',
            'amount': total
        }

        payment_span.set_attributes({
            'payment.status': payment_result['status'],
            'payment.id': payment_result['payment_id']
        })

    # Create order - nested span
    with tracer.start_as_current_span('create-order-record') as order_span:
        order_span.set_attributes({
            'user.id': user_id,
            'payment.id': payment_result['payment_id']
        })

        time.sleep(random.uniform(0.05, 0.15))

        new_order = {
            'order_id': f'ord_{int(time.time())}',
            'user_id': user_id,
            'items': items,
            'total': total,
            'payment_id': payment_result['payment_id'],
            'status': 'completed'
        }

        order_span.set_attributes({
            'order.id': new_order['order_id'],
            'order.status': new_order['status']
        })

    # Capture snapshot at checkout completion
    if client.get_snapshot_client():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.capture_snapshot('checkout-complete', {
                'user_id': user_id,
                'order_id': new_order['order_id'],
                'payment_id': payment_result['payment_id'],
                'total_amount': total,
                'status': 'success'
            }))
            loop.close()
        except Exception as e:
            print(f"Snapshot error: {e}")

    return jsonify({
        'success': True,
        'order': new_order,
        'payment': payment_result
    })


# Cross-service communication endpoints

@app.route('/api/data')
def data_endpoint():
    """Data endpoint that can be called by other services for distributed tracing"""
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span('process-data') as span:
        span.set_attribute('data.source', 'python-test-app')
        time.sleep(random.uniform(0.01, 0.05))

        data = {
            "service": SERVICE_NAME,
            "timestamp": time.time(),
            "data": {
                "users_count": len(USERS_DB),
                "orders_count": len(ORDERS_DB),
                "random_value": random.randint(1, 100)
            }
        }

        span.set_attribute('data.users_count', len(USERS_DB))
        span.set_attribute('data.orders_count', len(ORDERS_DB))

    return jsonify(data)


@app.route('/api/call-go')
def call_go_service():
    """Call Go service - demonstrates distributed tracing"""
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    tracer = trace.get_tracer(__name__)
    propagator = TraceContextTextMapPropagator()

    with tracer.start_as_current_span('call-go-service') as span:
        span.set_attribute('peer.service', 'go-test-app')

        # Inject trace context into headers
        headers = {}
        propagator.inject(headers)

        try:
            response = requests.get(f'{GO_SERVICE_URL}/api/data', headers=headers, timeout=5)
            span.set_attribute('http.status_code', response.status_code)

            return jsonify({
                "service": SERVICE_NAME,
                "called": "go-test-app",
                "response": response.json() if response.ok else None,
                "status": response.status_code
            })
        except Exception as e:
            span.set_attribute('error', True)
            span.set_attribute('error.message', str(e))
            return jsonify({
                "service": SERVICE_NAME,
                "called": "go-test-app",
                "error": str(e)
            }), 500


@app.route('/api/call-node')
def call_node_service():
    """Call Node service - demonstrates distributed tracing"""
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    tracer = trace.get_tracer(__name__)
    propagator = TraceContextTextMapPropagator()

    with tracer.start_as_current_span('call-node-service') as span:
        span.set_attribute('peer.service', 'node-test-app')

        headers = {}
        propagator.inject(headers)

        try:
            response = requests.get(f'{NODE_SERVICE_URL}/api/data', headers=headers, timeout=5)
            span.set_attribute('http.status_code', response.status_code)

            return jsonify({
                "service": SERVICE_NAME,
                "called": "node-test-app",
                "response": response.json() if response.ok else None,
                "status": response.status_code
            })
        except Exception as e:
            span.set_attribute('error', True)
            span.set_attribute('error.message', str(e))
            return jsonify({
                "service": SERVICE_NAME,
                "called": "node-test-app",
                "error": str(e)
            }), 500


@app.route('/api/call-laravel')
def call_laravel_service():
    """Call Laravel service - demonstrates distributed tracing"""
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    tracer = trace.get_tracer(__name__)
    propagator = TraceContextTextMapPropagator()

    with tracer.start_as_current_span('call-laravel-service') as span:
        span.set_attribute('peer.service', 'laravel-test-app')

        headers = {}
        propagator.inject(headers)

        try:
            response = requests.get(f'{LARAVEL_SERVICE_URL}/api/data', headers=headers, timeout=5)
            span.set_attribute('http.status_code', response.status_code)

            return jsonify({
                "service": SERVICE_NAME,
                "called": "laravel-test-app",
                "response": response.json() if response.ok else None,
                "status": response.status_code
            })
        except Exception as e:
            span.set_attribute('error', True)
            span.set_attribute('error.message', str(e))
            return jsonify({
                "service": SERVICE_NAME,
                "called": "laravel-test-app",
                "error": str(e)
            }), 500


@app.route('/api/call-php')
def call_php_service():
    """Call PHP service - demonstrates distributed tracing"""
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    tracer = trace.get_tracer(__name__)
    propagator = TraceContextTextMapPropagator()

    with tracer.start_as_current_span('call-php-service') as span:
        span.set_attribute('peer.service', 'php-test-app')

        headers = {}
        propagator.inject(headers)

        try:
            response = requests.get(f'{PHP_SERVICE_URL}/api/data', headers=headers, timeout=5)
            span.set_attribute('http.status_code', response.status_code)

            return jsonify({
                "service": SERVICE_NAME,
                "called": "php-test-app",
                "response": response.json() if response.ok else None,
                "status": response.status_code
            })
        except Exception as e:
            span.set_attribute('error', True)
            span.set_attribute('error.message', str(e))
            return jsonify({
                "service": SERVICE_NAME,
                "called": "php-test-app",
                "error": str(e)
            }), 500


@app.route('/api/call-all')
def call_all_services():
    """Call all services - demonstrates distributed tracing across multiple services"""
    from opentelemetry import trace
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    tracer = trace.get_tracer(__name__)
    propagator = TraceContextTextMapPropagator()

    results = {
        "service": SERVICE_NAME,
        "chain": []
    }

    services = [
        ("go-test-app", GO_SERVICE_URL),
        ("node-test-app", NODE_SERVICE_URL),
        ("laravel-test-app", LARAVEL_SERVICE_URL),
        ("php-test-app", PHP_SERVICE_URL),
    ]

    for service_name, service_url in services:
        with tracer.start_as_current_span(f'call-{service_name}') as span:
            span.set_attribute('peer.service', service_name)

            headers = {}
            propagator.inject(headers)

            try:
                response = requests.get(f'{service_url}/api/data', headers=headers, timeout=5)
                span.set_attribute('http.status_code', response.status_code)

                results["chain"].append({
                    "service": service_name,
                    "status": response.status_code,
                    "response": response.json() if response.ok else None
                })
            except Exception as e:
                span.set_attribute('error', True)
                span.set_attribute('error.message', str(e))
                results["chain"].append({
                    "service": service_name,
                    "error": str(e)
                })

    return jsonify(results)


# Error handlers

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": str(error)
    }), 404


@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request",
        "message": str(error)
    }), 400


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal Server Error",
        "message": str(error)
    }), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Flask app starting!")
    print("="*60)
    print("Service: python-test-app")
    print("Port: 5001")
    print("URL: http://localhost:5001")
    print("\nAvailable endpoints:")
    print("  - GET  /")
    print("  - GET  /health")
    print("  - GET  /api/users")
    print("  - GET  /api/users/<id>")
    print("  - GET  /api/orders")
    print("  - GET  /api/orders/<id>")
    print("  - POST /api/orders")
    print("  - GET  /api/slow")
    print("  - GET  /api/error")
    print("  - GET  /api/random")
    print("  - POST /api/checkout")
    print("\nTraceKit Configuration:")
    print(f"  - Endpoint: {os.getenv('TRACEKIT_ENDPOINT')}")
    print(f"  - Service: {os.getenv('TRACEKIT_SERVICE_NAME')}")
    print("  - Monitoring: Enabled")
    print("="*60 + "\n")

    app.run(
        host='0.0.0.0',
        port=5001,
        debug=False  # Set to False to avoid double initialization
    )
