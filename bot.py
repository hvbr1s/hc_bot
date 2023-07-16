import os
import json
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from dotenv import main
import pinecone
import openai
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, parse_obj_as
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
# from web3 import Web3
# from eth_account.messages import encode_defunct
# from typing import Optional


main.load_dotenv()

# os.environ['WEB3_PROVIDER'] = f"https://polygon-mumbai.g.alchemy.com/v2/{os.environ['ALCHEMY_API_KEY']}"

# # Initialize web3
# web3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))


class Query(BaseModel):
    user_input: str
    user_id: str

# Prepare augmented query

openai.api_key=os.environ['OPENAI_API_KEY']
pinecone.init(api_key=os.environ['PINECONE_API_KEY'], enviroment=os.environ['PINECONE_ENVIRONMENT'])
pinecone.whoami()
index_name = 'hc'
#index_name = 'academyzd'
index = pinecone.Index(index_name)

embed_model = "text-embedding-ada-002"

primer = """

You are Samantha, a highly intelligent and helpful virtual assistant designed to support Ledger, a French cryptocurrency company led by CEO Pascal Gauthier. Your primary responsibility is to assist Ledger users by providing accurate answers to their questions. If a question is unclear or lacks detail, ask for more information instead of making assumptions. If you are unsure of an answer, be honest and seek clarification.

Users may ask about various Ledger products, including the Ledger Nano S (no battery, low storage), Nano X (Bluetooth, large storage, has a battery), Nano S Plus (large storage, no Bluetooth, no battery), Ledger Stax (unreleased), Ledger Recover and Ledger Live.
The official Ledger store is located at https://shop.ledger.com/. The Ledger Recover White Paper is located at https://github.com/LedgerHQ/recover-whitepaper . For authorized resellers, please visit https://www.ledger.com/reseller/. Do not modify or share any other links for these purposes.

When users inquire about tokens, crypto or coins supported in Ledger Live , it is crucial to strictly recommend checking the Crypto Asset List link to verify support: https://support.ledger.com/hc/en-us/articles/10479755500573?docs=true/. Do NOT provide any other links to the list.

VERY IMPORTANT:

- The Ledger device and Ledger Live app have independent cryptocurrency compatibilities. If a coin/token is supported by your device but not the app, you'll need to use a compatible third-party wallet instead.
- If the query is not about Ledger products, disregard the CONTEXT. Respond courteously and invite any Ledger-related questions.
- When responding to a question, include a maximum of two URL links from the provided CONTEXT, choose the most relevant.
- Avoid sharing URLs if none are mentioned within the CONTEXT.
- Always present URLs as plain text, never use markdown formatting.
- If a user ask to speak to a human agent, invite them to contact us via this link: https://support.ledger.com/hc/en-us/articles/4423020306705-Contact-Us?support=true 
- If a user reports a scam or unauthorized crypto transactions, empathetically acknowledge their situation, promptly connect them with a live agent, and share this link for additional help: https://support.ledger.com/hc/en-us/articles/7624842382621-Loss-of-funds?support=true.
- Direct users who want to learn more about Ledger products or compare devices to https://www.ledger.com/.
- Updating or downloading Ledger Live must always be done via this link: https://www.ledger.com/ledger-live
- Share this list for tips on keeping your recovery phrase safe: https://support.ledger.com/hc/en-us/articles/360005514233-How-to-keep-your-24-word-recovery-phrase-and-PIN-code-safe-?docs=true/

Begin!

"""

# #####################################################


# # Define authentication function
# def authenticate(signature):
#     w3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))
#     message = "Access to chat bot"
#     message_hash = encode_defunct(text=message)
#     signed_message = w3.eth.account.recover_message(message_hash, signature=signature)
#     balance = int(contract.functions.balanceOf(signed_message).call())
#     print(balance)
#     if balance > 0:
#         token = uuid.uuid4().hex
#         response = JSONResponse(content={"redirect": "/check"})  # Use JSONResponse to set a custom response
#         response.set_cookie("authToken", token, httponly=True, secure=True, samesite="strict")
#         return response
#     else:
#         return "You don't have the required NFT!"

# # Define function to check for authToken cookie
# def has_auth_token(request):
#     authToken = request.cookies.get("authToken")
#     return authToken is not None

def get_user_id(request: Request):
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
#limiter = Limiter(key_func=get_remote_address)
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
    #return templates.TemplateResponse("auth.html", {"request": request})
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/_health")
async def health_check():
    return {"status": "OK"}

# @app.get("/api/clerk-api-key")
# def get_api_key():
#     clerk_api_key = os.getenv("CLERK_API_KEY")
#     return {"api_key": clerk_api_key}

# @app.get("/auth", response_class=HTMLResponse)
# async def auth(request: Request, signature: Optional[str] = None):
#     response = authenticate(signature)
#     return response

# @app.get("/check", response_class=HTMLResponse)
# async def gpt(request: Request):
#     if has_auth_token(request):
#         return templates.TemplateResponse("index.html", {"request": request})
#     else:
#         return RedirectResponse(url="/")

@app.post('/gpt')
@limiter.limit("1/hour")
def react_description(query: Query, request: Request):
    
    global last_response
    user_id = query.user_id
    if user_id not in user_states:
        user_states[user_id] = None
    last_response = user_states[user_id]
    try:
        res_embed = openai.Embedding.create(
            input=[query.user_input],
            engine=embed_model
        )

        xq = res_embed['data'][0]['embedding']

        res_query = index.query(xq, top_k=5, include_metadata=True)
        print(res_query)

        contexts = [item['metadata']['text'] for item in res_query['matches'] if item['score'] > 0.78]

        prev_response_line = f"YOUR PREVIOUS RESPONSE: {last_response}\n\n-----\n\n" if last_response else ""

        augmented_query = "CONTEXT: " + "\n\n-----\n\n" + "\n\n---\n\n".join(contexts) + "\n\n-----\n\n" + prev_response_line + "USER QUESTION: " + "\n\n" + '"' + query.user_input + '" ' + "\n\n" + "YOUR RESPONSE: "

    
        print(augmented_query)

        res = openai.ChatCompletion.create(
            temperature=0.0,
            model='gpt-4',
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ]
        )
        response = res['choices'][0]['message']['content']

        # Save the response to the global variable
        last_response = response

        # Save the response to a thread
        user_states[user_id] = response
        print(user_states)
        print(response)
        return {'output': response}
        
    except ValueError as e:
        print(e)
        raise HTTPException(status_code=400, detail="Invalid input")


############### START COMMAND ##########

#   uvicorn memory_api_bot:app --reload --port 8008
#   uvicorn memory_api_bot:app --port 80 --host 0.0.0.0
