import sys
import asyncio
import httpx
import json
from datetime import datetime

sys.path.append('.')

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.schema import Base, Transaction
from dotenv import load_dotenv
import os

load_dotenv()

class BabylonIndexer:
    def __init__(self):
        self.NODES = [
            "https://babylon-archive.nodes.guru/api",
            "https://babylon-api.polkachu.com",
            "https://babylon.api.kjnodes.com",
            "https://babylon-mainnet-api.nodes.guru",
            "https://babylon-api.lavenderfive.com"
        ]
        self.current_node_index = 0
        self.BASE_URL = self.NODES[0]
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL not found in .env")
            
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)

    def switch_node(self):
        """Switch to the next node in the list if the current one fails"""
        self.current_node_index = (self.current_node_index + 1) % len(self.NODES)
        self.BASE_URL = self.NODES[self.current_node_index]
        print(f"Switching to backup node: {self.BASE_URL}")

    async def fetch_latest_block(self):
        async with httpx.AsyncClient() as client:
            for attempt in range(len(self.NODES)):
                try:
                    print(f"Connecting to {self.BASE_URL}...")
                    resp = await client.get(f"{self.BASE_URL}/cosmos/base/tendermint/v1beta1/blocks/latest", timeout=10.0)
                    resp.raise_for_status()
                    data = resp.json()
                    return int(data['block']['header']['height'])
                except Exception as e:
                    print(f"Node failed ({e}).")
                    self.switch_node() 
            
            print("All nodes failed. Please check your internet connection.")
            return None

    async def fetch_txs(self, height):
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.BASE_URL}/cosmos/tx/v1beta1/txs?events=tx.height={height}", timeout=10.0)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                print(f"Error fetching txs for block {height}: {e}")
                return None

    def extract_sender(self, tx_body):
        """Helper to find the address depending on the message type"""
        try:
            messages = tx_body.get('body', {}).get('messages', [])
            if not messages:
                return "unknown"
            
            msg = messages[0]
            if 'sender' in msg: return msg['sender']
            if 'from_address' in msg: return msg['from_address']
            if 'delegator_address' in msg: return msg['delegator_address']
            
            
            if 'staker_address' in msg: return msg['staker_address']
            if 'signer' in msg: return msg['signer']
            
            return "unknown"
        except Exception:
            return "unknown"

    def parse_message(self, tx_body):
        """
        Analyzes the transaction body to determine Type and Specific Details.
        Returns: (tx_type, details_dict)
        """
        try:
            messages = tx_body.get('body', {}).get('messages', [])
            if not messages:
                return "Unknown", {}

            msg = messages[0]
            raw_type = msg.get('@type', '')
            
            # --- 1. BTC STAKING (Babylon Specific) ---
            if 'MsgCreateBTCDelegation' in raw_type:
                return "BTC_Stake", {
                    "btc_pk": msg.get('btc_pk_hex'),
                    "finality_provider": msg.get('finality_provider_key'),
                    "staking_time": msg.get('staking_time')
                }
            
            # --- 2. VALIDATOR OPERATIONS ---
            if 'MsgDelegate' in raw_type:
                return "Delegate", {
                    "validator": msg.get('validator_address'),
                    "amount": msg.get('amount', {}).get('amount')
                }
            if 'MsgUndelegate' in raw_type:
                return "Undelegate", {
                    "validator": msg.get('validator_address')
                }
            
            # --- 3. GOVERNANCE ---
            if 'MsgVote' in raw_type:
                return "Governance_Vote", {
                    "proposal_id": msg.get('proposal_id'),
                    "option": msg.get('option')
                }

            # --- 4. STANDARD TRANSFER ---
            if 'MsgSend' in raw_type:
                return "Transfer", {
                    "recipient": msg.get('to_address')
                }

            # Fallback
            clean_type = raw_type.split('.')[-1].replace("Msg", "")
            return clean_type, {}

        except Exception as e:
            print(f"Parser Error: {e}")
            return "Error", {}

    async def run(self):
        latest_height = await self.fetch_latest_block()
        if not latest_height:
            return

        print(f"Latest Height: {latest_height}")
        print("Scanning for transactions...")

        session = self.Session()
        
        
        for h in range(latest_height, latest_height - 500, -1):
            print(f"Processing Block {h}...", end="\r")
            
            data = await self.fetch_txs(h)
            
            if data and 'tx_responses' in data and len(data['tx_responses']) > 0:
                responses = data.get('tx_responses', [])
                tx_bodies = data.get('txs', [])
                
                print(f"\n⚡ Found {len(responses)} Transactions in Block {h}")

                for i, resp in enumerate(responses):
                    try:
                        tx_hash = resp.get('txhash')
                        timestamp_str = resp.get('timestamp', datetime.now().isoformat()) # Use block timestamp if available
                        
                        
                        body = None
                        if i < len(tx_bodies):
                            body = tx_bodies[i]

                        if body:
                            tx_type, details = self.parse_message(body)
                            sender = self.extract_sender(body)
                        else:
                            tx_type, details = "Unknown", {}
                            sender = "unknown"

                        new_tx = Transaction(
                            tx_hash=tx_hash,
                            height=h,
                            sender=sender,
                            amount=0,
                            tx_type=tx_type, 
                            details=details, 
                            timestamp=datetime.now()
                        )
                        
                        try:
                            session.merge(new_tx) 
                            session.commit()
                            print(f"   Saved: {tx_type} | {tx_hash[:10]}...")
                        except Exception as db_err:
                            session.rollback()
                            print(f"   DB Error: {db_err}")

                    except Exception as e:
                        print(f"   Parsing Error: {e}")
                        continue
            
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    indexer = BabylonIndexer()
    try:
        asyncio.run(indexer.run())
    except KeyboardInterrupt:
        print("\nStopped by user.")