import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent
from analytics.graph_algo import SuspiciousBehaviorDetector

class AnalyticsAgent:
    def __init__(self, api_key=None):
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.db_url = os.getenv("DATABASE_URL")
        self.engine = create_engine(self.db_url) if self.db_url else None
        
    def ask(self, question: str) -> str:
        if not self.api_key:
            return 'AI features require an OPENAI_API_KEY in your .env file.'
            
        try:
            db = SQLDatabase.from_uri(self.db_url)
            llm = ChatOpenAI(temperature=0, model="gpt-4", api_key=self.api_key)
            
            agent_executor = create_sql_agent(
                llm=llm,
                db=db,
                agent_type="openai-tools",
                verbose=True
            )
            return agent_executor.invoke({"input": question})["output"]
            
        except Exception as e:
            return f"Error running analytics agent: {str(e)}"
    
    def analyze_wallet_deep_dive(self, address: str) -> str:
        """Perform deep dive analysis on a specific wallet address"""
        if not self.api_key:
            return 'AI features require an OPENAI_API_KEY in your .env file.'
            
        try:
            query = "SELECT sender, amount, timestamp FROM transactions WHERE sender = %(addr)s ORDER BY timestamp"
            
            df = pd.read_sql(query, self.engine, params={"addr": address})
            
            if df.empty:
                return f"No transactions found for address {address}"
            
            total_volume = df['amount'].sum()
            days_active = (df['timestamp'].max() - df['timestamp'].min()).days or 1
            frequency = len(df) / days_active
            avg_tx_size = df['amount'].mean()
            
            detector = SuspiciousBehaviorDetector()
            for _, row in df.iterrows():
                detector.add_transaction(
                    row['sender'], 
                    "unknown_receiver", 
                    row['amount'], 
                    row['timestamp']
                )
            
            wash_trades = detector.detect_wash_trading()
            fan_outs = detector.detect_fan_out(min_recipients=1) 
            
            stats = f"""
            Address: {address}
            Total Volume: {total_volume:,.2f}
            Transaction Frequency: {frequency:.2f} txs/day
            Average Transaction Size: {avg_tx_size:,.2f}
            Total Transactions: {len(df)}
            Suspicious Cycles Detected: {len(wash_trades)}
            Fan-out Patterns Detected: {len(fan_outs)}
            """
            
            llm = ChatOpenAI(temperature=0, model="gpt-4", api_key=self.api_key)
            prompt = f"""
            You are a blockchain forensic expert. Profile this address based on the following statistics: 
            {stats}
            
            Task:
            1. Is it a bot, a whale, or a retail user? 
            2. Explain why based on frequency and volume.
            3. Keep it short and professional.
            """
            
            response = llm.invoke(prompt)
            return response.content
            
        except Exception as e:
            return f"Error analyzing wallet: {str(e)}"