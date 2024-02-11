import os
from dotenv import main
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, parse_obj_as
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import httpx
from typing import Optional
from fastapi import Request


main.load_dotenv()

class Query(BaseModel):
    user_input: str
    user_id: str
    locale: str
    platform: str


# #####################################################


async def get_user_id(request: Request):
    try:
        body = parse_obj_as(Query, request.json())
        user_id = body.user_id
        return user_id
    except Exception as e:
        return get_remote_address(request)


# Define FastAPI app
app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="./static/BBALP00A.TTF")

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


# Define FastAPI endpoints

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/_health")
async def health_check():
    return {"status": "OK"}

@app.post('/gpt')
@limiter.limit("10/hour")
async def react_description(query: Query, request: Request):
    
    global last_response
    user_input = query.user_input
    user_id = query.user_id
    locale = query.locale
    platform = query.platform

    try:
        async with httpx.AsyncClient() as client:
            print('check!')
            response = await client.post(

                "https://www.samanthabot.co/",
                json={
                    "user_input": user_input, 
                    "user_id": user_id,
                    "locale": locale,
                    "platform": platform
                },
                headers = {
                    'Content-Type': "application/json", 
                    "Authorization": f"Bearer {os.getenv('BACKEND_API_KEY')}"
                },
                timeout=30.0
            )
            resp = response.raise_for_status()  # Will raise an exception for 4xx and 5xx status codes
            print(resp)
    except httpx.HTTPStatusError as e:
        print(f"Exception occurred: {e}")   
        raise HTTPException(status_code=500, detail="Server error")
    
    response_data = response.json()
    print(f"Server response: {response_data}")  # Debugging print statement
    

    chat_output = response_data[0]

    chatty = {"output": chat_output}
    print(chatty)

    return chatty


############### START COMMAND ##########

#   uvicorn bot:app --reload --port 8008
#   uvicorn memory_api_bot:app --port 80 --host 0.0.0.0
