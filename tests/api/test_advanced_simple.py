# -*- coding: utf-8 -*-
"""
Simple standalone test for advanced routers to verify basic functionality
"""

import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

# Test alerts_advanced_router
print("Testing alerts_advanced_router...")
from api.alerts_advanced_router import router as alerts_router

app1 = FastAPI()
app1.include_router(alerts_router)
app1.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client1 = TestClient(app1)
response = client1.get("/api/v1/alerts/dashboard")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
print("[OK] alerts_advanced_router - GET /dashboard works")

# Test ai_advanced_router
print("Testing ai_advanced_router...")
from api.ai_advanced_router import router as ai_router

app2 = FastAPI()
app2.include_router(ai_router)
app2.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client2 = TestClient(app2)
response = client2.get("/api/ai/model-fine-tuning/jobs")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
print("[OK] ai_advanced_router - GET /model-fine-tuning/jobs works")

# Test integration_providers_router
print("Testing integration_providers_router...")
from api.integration_providers_router import router as integration_router

app3 = FastAPI()
app3.include_router(integration_router)
app3.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client3 = TestClient(app3)
response = client3.get("/api/v1/integration/teams/config")
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
print("[OK] integration_providers_router - GET /teams/config works")

print("\n" + "=" * 80)
print("All basic tests passed! [OK]")
print("=" * 80)
