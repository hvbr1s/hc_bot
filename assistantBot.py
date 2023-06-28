import os
import uuid
import json
from dotenv import load_dotenv
from flask import Flask, render_template, request, make_response, redirect, jsonify
from web3 import Web3
from eth_account.messages import encode_defunct
import pinecone
import openai
import re
from langchain.vectorstores import Pinecone

load_dotenv()


env_vars = [
    'OPENAI_API_KEY',
    'ALCHEMY_API_KEY',
    'PINECONE_API_KEY',
    'PINECONE_ENVIRONMENT',
]

os.environ.update({key: os.getenv(key) for key in env_vars})
os.environ['WEB3_PROVIDER'] = f"https://polygon-mumbai.g.alchemy.com/v2/{os.environ['ALCHEMY_API_KEY']}"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
ORGANIZATION = os.getenv("ORGANIZATION")
openai.api_key=os.environ['OPENAI_API_KEY']

# Initialize web3
web3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))


# Prepare augmented query

pinecone.init(api_key=os.environ['PINECONE_API_KEY'], enviroment=os.environ['PINECONE_ENVIRONMENT'])
pinecone.whoami()
index_name = 'hc'
#index_name = 'academyzd'
index = pinecone.Index(index_name)

embed_model = "text-embedding-ada-002"

primer = """

You are Samantha, a highly intelligent and helpful virtual assistant designed to support Ledger, a French cryptocurrency company led by CEO Pascal Gauthier. Your primary responsibility is to assist Ledger customer support agents by providing accurate answers to their questions. If a question is unclear or lacks detail, ask for more information instead of making assumptions. If you are unsure of an answer, be honest and seek clarification.

Agents may ask about various Ledger products, including the Ledger Nano S (no battery, low storage), Nano X (Bluetooth, large storage, has a battery), Nano S Plus (large storage, no Bluetooth, no battery), Ledger Stax (unreleased), Ledger Recover and Ledger Live.
The official Ledger store is located at https://shop.ledger.com/. The Ledger Recover White Paper is located at https://github.com/LedgerHQ/recover-whitepaper . For authorized resellers, please visit https://www.ledger.com/reseller/. Do not modify or share any other links for these purposes. 

When agents inquire about tokens, crypto or coins supported in Ledger Live , it is crucial to strictly recommend checking the Crypto Asset List link to verify support. 
The link to the Crypto Asset List of supported crypto coins and tokens is: https://support.ledger.com/hc/en-us/articles/10479755500573?docs=true/. Do NOT provide any other links to the list.

VERY IMPORTANT:

- If the query is not about Ledger products, disregard the CONTEXT. Respond courteously and invite any Ledger-related questions.
- When answering a question, make sure to incorporate only the most relevant URL link from the CONTEXT in your response. 
- Only share URLs that are explicitly mentioned within the CONTEXT.
- If the provided CONTEXT does not include URLs, do not include any in your response.
- Always format URL links in markdown format.
- Direct users who want to learn more about Ledger products or compare devices to https://www.ledger.com/.
- Updating or downloading Ledger Live must always be done via this link: https://www.ledger.com/ledger-live
- Share this list for tips on keeping your recovery phrase safe: https://support.ledger.com/hc/en-us/articles/360005514233-How-to-keep-your-24-word-recovery-phrase-and-PIN-code-safe-?docs=true/


Begin!

"""

# #####################################################


# Define Flask app
app = Flask(__name__, static_folder='static')

# Define authentication function
def authenticate(signature):
    w3 = Web3(Web3.HTTPProvider(os.environ['WEB3_PROVIDER']))
    message = "Access to chat bot"
    message_hash = encode_defunct(text=message)
    signed_message = w3.eth.account.recover_message(message_hash, signature=signature)
    balance = int(contract.functions.balanceOf(signed_message).call())
    print(balance)
    if balance > 0:
        token = uuid.uuid4().hex
        response = make_response(redirect('/gpt'))
        response.set_cookie("authToken", token, httponly=True, secure=True, samesite="strict")
        return response
    else:
        return "You don't have the required NFT!"

# Define function to check for authToken cookie
def has_auth_token(request):
    authToken = request.cookies.get("authToken")
    return authToken is not None

# Define Flask endpoints
@app.route("/")
def home():
    return render_template("auth.html")
    #return render_template('index.html')

@app.route("/auth")
def auth():
    signature = request.args.get("signature")
    print(signature)
    response = authenticate(signature)
    return response

@app.route("/gpt")
def gpt():
    if has_auth_token(request):
        return render_template("index.html")
    else:
        return redirect("/")

@app.route('/api', methods=['POST'])
def react_description():
    user_input = request.json.get('user_input')
    try:

        res_embed = openai.Embedding.create(
            input=[user_input],
            engine=embed_model
        )

        xq = res_embed['data'][0]['embedding']

        res_query = index.query(xq, top_k=5, include_metadata=True)

        contexts = [item['metadata']['text'] for item in res_query['matches']]

        augmented_query = "CONTEXT: " + "\n\n-----\n\n" + "\n\n---\n\n".join(contexts) + "\n\n-----\n\n"+ "QUESTION: " + "\n\n" + '"' + user_input + '" ' + "Please provide an answer to the question."

        print(augmented_query)

        res = openai.ChatCompletion.create(
            temperature=0.0,
            model='gpt-4',
            #model="gpt-3.5-turbo-16k",
            #model="gpt-3.5-turbo-0613",
            #model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ]
        )
        response = res['choices'][0]['message']['content']
        print(response)
        return jsonify({'output': response})
    except ValueError as e:
        print(e)
        return jsonify({'output': 'Sorry, could you please repeat the question?'})


ADDRESS = "0xb022C9c672592c274397557556955eE968052969"
ABI = [{"inputs":[{"internalType":"string","name":"_name","type":"string"},{"internalType":"string","name":"_symbol","type":"string"}],"stateMutability":"nonpayable","type":"constructor"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"approved","type":"address"},{"indexed":True,"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"owner","type":"address"},{"indexed":True,"internalType":"address","name":"operator","type":"address"},{"indexed":False,"internalType":"bool","name":"approved","type":"bool"}],"name":"ApprovalForAll","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"previousOwner","type":"address"},{"indexed":True,"internalType":"address","name":"newOwner","type":"address"}],"name":"OwnershipTransferred","type":"event"},{"anonymous":False,"inputs":[{"indexed":True,"internalType":"address","name":"from","type":"address"},{"indexed":True,"internalType":"address","name":"to","type":"address"},{"indexed":True,"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"Transfer","type":"event"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"approve","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"getApproved","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"operator","type":"address"}],"name":"isApprovedForAll","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"owner","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"ownerOf","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"renounceOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"string","name":"tokenURI","type":"string"}],"name":"safeMint","outputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"safeTransferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"},{"internalType":"bytes","name":"_data","type":"bytes"}],"name":"safeTransferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"operator","type":"address"},{"internalType":"bool","name":"approved","type":"bool"}],"name":"setApprovalForAll","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"bytes4","name":"interfaceId","type":"bytes4"}],"name":"supportsInterface","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"uint256","name":"index","type":"uint256"}],"name":"tokenOfOwnerByIndex","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"tokenURI","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"},{"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"tokenId","type":"uint256"}],"name":"transferFrom","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"newOwner","type":"address"}],"name":"transferOwnership","outputs":[],"stateMutability":"nonpayable","type":"function"}]
contract = web3.eth.contract(address=ADDRESS, abi=ABI)

# Start the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1000, debug=False, use_reloader=False)
