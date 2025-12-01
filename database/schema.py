from sqlalchemy import create_engine, Column, String, Integer, BigInteger, DateTime, Boolean, JSON
from sqlalchemy.orm import declarative_base  

Base = declarative_base()

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    tx_hash = Column(String, unique=True)
    height = Column(Integer)
    sender = Column(String)
    amount = Column(BigInteger)
    timestamp = Column(DateTime)
    tx_type = Column(String) 
    details = Column(JSON)    

class AddressLabel(Base):
    __tablename__ = 'address_labels'
    
    address = Column(String, primary_key=True)
    label = Column(String)
    category = Column(String)

def init_db(db_url):
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)