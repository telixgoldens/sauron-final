import random
import secrets
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database.schema import Transaction, Base
from dotenv import load_dotenv
import os

load_dotenv()

def run_seed():
    """
    Master Seed Function:
    1. Creates Tables (if missing)
    2. Clears Old Data
    3. Plants 'Crime Scene' & 'Clusters'
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL not found")

    engine = create_engine(db_url)
    
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()

    print("Starting Master Seed Process...")

    try:
        try:
            session.execute(text("TRUNCATE TABLE transactions"))
            session.commit()
        except Exception:
            session.rollback()
            session.query(Transaction).delete()
            session.commit()

        SUSPECT_ADDR = "bbn1badguy9999999999999999999999999999999"
        LAUNDER_A = "bbn1launderA..............................."
        base_time = datetime.now() - timedelta(hours=2)

        for i in range(12):
            session.add(Transaction(
                tx_hash=f"TX_FANOUT_{i}",
                height=50000 + i,
                sender=SUSPECT_ADDR,
                amount=5000, 
                timestamp=base_time + timedelta(minutes=i),
                tx_type="Transfer"
            ))

        session.add(Transaction(tx_hash="TX_WASH_1", height=50100, sender=SUSPECT_ADDR, amount=10000, timestamp=base_time + timedelta(hours=1), tx_type="Transfer"))
        session.add(Transaction(tx_hash="TX_WASH_2", height=50101, sender=LAUNDER_A, amount=10000, timestamp=base_time + timedelta(hours=1, minutes=5), tx_type="Transfer"))

        HUB_ADDRESS = "bbn1_MASTER_MIND_999999999999999999999"
        BOT_ARMY = [f"bbn1_bot_wallet_{i}_{secrets.token_hex(4)}" for i in range(20)]
        NOW = datetime.now()

        for i, bot in enumerate(BOT_ARMY):
            session.add(Transaction(
                tx_hash=f"TX_FUNDING_{i}_{secrets.token_hex(4)}",
                height=60000 + i,
                sender=HUB_ADDRESS, 
                amount=random.randint(1000, 5000), 
                timestamp=NOW - timedelta(minutes=60) + timedelta(seconds=i*10),
                tx_type="BTC_Stake" 
            ))

        tx_count = 0
        for i, bot in enumerate(BOT_ARMY):
            for j in range(random.randint(3, 5)):
                session.add(Transaction(
                    tx_hash=f"TX_BOT_ACT_{i}_{j}",
                    height=60050 + tx_count,
                    sender=bot, 
                    amount=random.randint(10, 50), 
                    timestamp=NOW - timedelta(minutes=30) + timedelta(minutes=j),
                    tx_type="Governance_Vote" 
                ))
                tx_count += 1

        for i in range(50):
            session.add(Transaction(
                tx_hash=secrets.token_hex(16),
                height=random.randint(40000, 49000),
                sender=f"bbn1user{secrets.token_hex(4)}",
                amount=random.randint(1, 100),
                timestamp=base_time - timedelta(minutes=random.randint(0, 1000)),
                tx_type="Transfer"
            ))

        session.commit()
        print("ALL DATA INJECTED SUCCESSFULLY.")

    except Exception as e:
        session.rollback()
        print(f"Error during seeding: {e}")
        raise e 
    finally:
        session.close()

if __name__ == "__main__":
    run_seed()