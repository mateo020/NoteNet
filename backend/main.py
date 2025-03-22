from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # allow Vite frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "FastAPI is working with CORS!"}
# Include routers
app.include_router(api_router, prefix="/api")

# Print all registered routes
print("\nRegistered routes:")
for route in app.routes:
    print(f"{route.path} [{route.methods}]") 