import os
import time
import json
import uuid
import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="CloudCart Order & Catalog API", version="1.0.0")

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus automatic HTTP metrics (/metrics endpoint)
Instrumentator().instrument(app).expose(app)

# Redis connection via Environment Variables (Kubernetes ConfigMap/Secret friendly)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
APP_ENV = os.getenv("APP_ENV", "development")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    socket_connect_timeout=2
)

# Sample Catalog Data
PRODUCTS = [
    {"id": 1, "name": "DevOps Pro Mechanical Keyboard", "price": 120, "stock": 15},
    {"id": 2, "name": "Kubernetes Cluster Mug", "price": 18, "stock": 40},
    {"id": 3, "name": "Terraform IaC Hoodie", "price": 45, "stock": 25},
    {"id": 4, "name": "Linux Penguin Desk Mat", "price": 25, "stock": 30},
]

class OrderRequest(BaseModel):
    product_id: int
    quantity: int = 1

@app.get("/api/info")
def get_info():
    return {
        "service": "cloudcart-backend",
        "environment": APP_ENV,
        "hostname": os.uname().nodename
    }

# Kubernetes Liveness Probe
@app.get("/healthz")
def healthz():
    return {"status": "alive"}

# Kubernetes Readiness Probe (checks Redis dependency)
@app.get("/ready")
def ready():
    try:
        redis_client.ping()
        return {"status": "ready", "redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {str(e)}")

@app.get("/api/products")
def list_products():
    return {"products": PRODUCTS}

@app.post("/api/orders")
def create_order(order: OrderRequest):
    product = next((p for p in PRODUCTS if p["id"] == order.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    order_id = str(uuid.uuid4())[:8]
    order_data = {
        "order_id": order_id,
        "product": product["name"],
        "quantity": order.quantity,
        "total_price": product["price"] * order.quantity,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        redis_client.lpush("orders", json.dumps(order_data))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store order in Redis: {str(e)}")

    return {"message": "Order placed successfully", "order": order_data}

@app.get("/api/orders")
def get_orders():
    try:
        raw_orders = redis_client.lrange("orders", 0, 19)
        orders = [json.loads(o) for o in raw_orders]
        return {"orders": orders}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

# Endpoint to test Grafana Alerts & K8s Resilience
@app.get("/api/simulate-error")
def simulate_error():
    raise HTTPException(status_code=500, detail="Simulated 500 Internal Server Error for Observability Testing")