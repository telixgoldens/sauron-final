import requests
import pandas as pd
import time
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv
import json

load_dotenv()

BASE_URL = "https://babylon-api.polkachu.com" 
DB_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return create_engine(DB_URL)

def fetch_latest_height():
    try:
        url = f"{BASE_URL}/cosmos/base/tendermint/v1beta1/blocks/latest"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        return int(data['block']['header']['height'])
    except Exception as e:
        print(f"Error fetching height: {e}")
        return None

def parse_smart_details(msg):
    """
    Stolen from babylon_fetcher.py:
    Identifies specific Babylon events and returns clean Type + Details.
    """
    raw_type = msg.get('@type', '')
    
    # 1. BTC STAKING
    if 'MsgCreateBTCDelegation' in raw_type:
        return "BTC_Stake", f"BTC PK: {msg.get('btc_pk_hex', '')[:10]}..."
    
    # 2. VALIDATOR OPS
    if 'MsgDelegate' in raw_type:
        return "Delegate", f"Validator: {msg.get('validator_address', '')[:10]}..."
    if 'MsgUndelegate' in raw_type:
        return "Undelegate", f"Validator: {msg.get('validator_address', '')[:10]}..."
        
    # 3. GOVERNANCE
    if 'MsgVote' in raw_type:
        return "Governance_Vote", f"Proposal ID: {msg.get('proposal_id', '?')} | Option: {msg.get('option', '?')}"
        
    # 4. TRANSFER
    if 'MsgSend' in raw_type:
        return "Transfer", f"To: {msg.get('to_address', '')[:10]}..."

    
    clean_name = raw_type.split('.')[-1].replace("Msg", "")
    return clean_name, "None"

def parse_tx(tx_response):
    try:
        tx_hash = tx_response['txhash']
        timestamp = tx_response['timestamp']
        
        tx_body = tx_response['tx']['body']
        if not tx_body['messages']: return None
        
        first_msg = tx_body['messages'][0]
        
        tx_type, details_str = parse_smart_details(first_msg)
        
        sender = "Unknown"
        if 'sender' in first_msg: sender = first_msg['sender']
        elif 'from_address' in first_msg: sender = first_msg['from_address']
        elif 'delegator_address' in first_msg: sender = first_msg['delegator_address']
        elif 'voter' in first_msg: sender = first_msg['voter']
        elif 'signer' in first_msg: sender = first_msg['signer']
            
        amount = 0.0
        amt_obj = first_msg.get('amount')
        
        if isinstance(amt_obj, list) and len(amt_obj) > 0:
            amt_obj = amt_obj[0]
            
        if isinstance(amt_obj, dict):
            raw_val = float(amt_obj.get('amount', 0))
            denom = amt_obj.get('denom', 'ubbn')
            
            if denom == 'ubbn':
                amount = raw_val / 1_000_000
            else:
                amount = raw_val 

        return {
            "timestamp": timestamp,
            "tx_hash": tx_hash,
            "sender": sender,
            "amount": amount,
            "tx_type": tx_type,
            "details": details_str
        }
        
    except Exception as e:
        return None

def run_seed():
    print("Connecting to Babylon Mainnet (Smart Mode)...")
    engine = get_db_connection()
    
    latest_height = fetch_latest_height()
    if not latest_height:
        print("API Error. Check internet.")
        return
    
    print(f"Height: {latest_height}")
    all_txs = []
    
    for h in range(latest_height, latest_height - 20, -1):
        print(f"   Fetching Block {h}...")
        try:
            url = f"{BASE_URL}/cosmos/tx/v1beta1/txs/block/{h}"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            
            if 'tx_responses' in data:
                for tx in data['tx_responses']:
                    parsed = parse_tx(tx)
                    if parsed:
                        all_txs.append(parsed)
            time.sleep(0.1) 
        except Exception:
            continue

    if all_txs:
        print(f" Saving {len(all_txs)} transactions...")
        df = pd.DataFrame(all_txs)
        df.to_sql('transactions', engine, if_exists='replace', index=False)
        print(" Database Updated!")
    else:
        print("No recent transactions found.")

if __name__ == "__main__":
    run_seed()