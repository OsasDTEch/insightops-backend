from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import Base, engine
from database.models import *
from routes import intercom_routes, slack_routes, zendesk_routes,auth_routes

app= FastAPI(title='INSIGHTOPS API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],

)
try:
    Base.metadata.create_all(engine)
    print("✅ Tables created")
except Exception as e:
    print("❌ Error creating tables:", e)


app.include_router(intercom_routes.router)
app.include_router(slack_routes.router)
app.include_router(zendesk_routes.router)
app.include_router(auth_routes.router)

@app.get("/")
def root():
    return {"message": "Welcome to InsightOps"}