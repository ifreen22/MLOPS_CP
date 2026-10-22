import os

base_dir = r"c:\Users\Ifreen\Downloads\MLOPS_CP"
be_dir = os.path.join(base_dir, "backend")

folders = [
    "app",
    "app/api",
    "app/api/v1",
    "app/api/v1/controllers",
    "app/core",
    "app/models",
    "app/schemas",
    "app/schemas/dto",
    "app/services",
    "app/repositories",
    "app/validation",
    "app/db",
    "app/ml_services"
]

for folder in folders:
    os.makedirs(os.path.join(be_dir, folder), exist_ok=True)

main_py = """
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router

app = FastAPI(title="AIOps Sentinel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}
"""

with open(os.path.join(be_dir, "app", "main.py"), "w") as f:
    f.write(main_py)

with open(os.path.join(be_dir, "app", "api", "v1", "router.py"), "w") as f:
    f.write('from fastapi import APIRouter\n\napi_router = APIRouter()\n')

print("Backend setup complete!")
