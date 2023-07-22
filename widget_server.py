import os
import json
from dotenv import main
from fastapi import FastAPI, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, parse_obj_as
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import httpx

main.load_dotenv()

#########Initialize backend API keys ######

server_api_key=os.environ['BACKEND_API_KEY'] #New
API_KEY_NAME=os.environ['API_KEY_NAME'] #New
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Depends(api_key_header)):
    if api_key_header.split(' ')[1] != server_api_key:
    #if api_key_header!= server_api_key:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    return api_key_header

class Query(BaseModel):
    user_input: str
    user_id: str

# #####################################################

def get_user_id(request: Request):
    try:
        body = parse_obj_as(Query, request.json())
        user_id = body.user_id
        return user_id
    except Exception as e:
        return get_remote_address(request)


# Define FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="./home/dan/langchain_projects/hcBot/static/BBALP00A.TTF")
templates = Jinja2Templates(directory="templates")

# Define limiter
limiter = Limiter(key_func=get_user_id)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests, please try again in an hour."},
    )

# Initialize user state
user_states = {}


# Define FastAPI endpoints
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
    #return templates.TemplateResponse("widget.html", {"request": request})

@app.get("/_health")
async def health_check():
    return {"status": "OK"}


@app.post("/sendMessage")
@limiter.limit("1/hour")
async def send_message(request: Request):
    data = await request.json()
    user_input = data.get("user_input")
    user_id = data.get("user_id")

    if not user_input or not user_id:
        raise HTTPException(status_code=400, detail="Invalid input")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.samanthabot.co/gpt",
                json={"user_input": user_input, "user_id": user_id},
                headers = {'Content-Type': 'application/json', "Authorization": f"Bearer {os.getenv('BACKEND_API_KEY')}"},
                timeout=30.0
            )
            response.raise_for_status()  # Will raise an exception for 4xx and 5xx status codes
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=500, detail="Server error")
    
    response_data = response.json()
    print(f"Server response: {response_data}")  # Debugging print statement

    chat_output = response_data.get("output", "No output provided.")

    chatty = {"output": chat_output}
    print(chatty)
    return chatty


############### START COMMAND ##########

#   uvicorn widget_server:app --reload --port 8008
#   uvicorn memory_api_bot:app --port 80 --host 0.0.0.0
