from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from src.components.controller import router as api_router1
from src.components.yahoofinance import router as api_router2
from src.database.database import Base, engine
from src.pipeline.exception import CustomException
from src.pipeline.logger import logger
import uvicorn
import os

try:
    from src.components import custom_patch
except ImportError:
    logger.warning("Custom patch module not found, proceeding without it.")    


app = FastAPI()

# CORS middleware configuration
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3002",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3002",
    "http://127.0.0.1:8080",
    "https://rtpa-ui-dfg9aua3gcf8fmhx.eastus2-01.azurewebsites.net",
    "https://rtpa-be.azurewebsites.net",
    "https://rtpa.azurewebsites.net",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
# Base.metadata.create_all(bind=engine)

# Define static file directory
# static_dir = os.path.join(os.path.dirname(__file__), "src\static")
# print(static_dir)

# # Mount static files
# app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include the router from controller.py
app.include_router(api_router1)  
app.include_router(api_router2)

@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    logger.error(f"An error occurred: {exc.error_message}")
    return JSONResponse(
        status_code=500,
        content={"message": "An error occurred", "details": exc.error_message},
    )

if __name__ == "__main__":
    logger.info("Starting the application")
    uvicorn.run(app, host="127.0.0.1", port=8000)