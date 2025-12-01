import networkx as nx
from collections import defaultdict
from datetime import datetime, timedelta

class SuspiciousBehaviorDetector:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.transactions = []
    
    def add_transaction(self, from_addr, to_addr, amount, timestamp):
        """Add a transaction to the graph"""
        self.graph.add_edge(from_addr, to_addr, weight=amount, timestamp=timestamp)
        self.transactions.append({
            'from': from_addr,
            'to': to_addr,
            'amount': amount,
            'timestamp': timestamp
        })
    
    def detect_wash_trading(self, min_cycle_length=2, max_cycle_length=10):
        """Detect potential wash trading by finding cycles in the transaction graph"""
        suspicious_cycles = []
        
        try:
            cycles = list(nx.simple_cycles(self.graph))
            
            for cycle in cycles:
                if min_cycle_length <= len(cycle) <= max_cycle_length:
                    total_volume = 0
                    for i in range(len(cycle)):
                        from_node = cycle[i]
                        to_node = cycle[(i + 1) % len(cycle)]
                        if self.graph.has_edge(from_node, to_node):
                            total_volume += self.graph[from_node][to_node]['weight']
                    
                    suspicious_cycles.append({
                        'cycle': cycle,
                        'length': len(cycle),
                        'total_volume': total_volume
                    })
        
        except nx.NetworkXError:
            pass
        
        return sorted(suspicious_cycles, key=lambda x: x['total_volume'], reverse=True)
    
    def detect_fan_out(self, time_window_minutes=60, min_recipients=10, min_amount=0):
        """Detect fan-out patterns where wallets send to many addresses quickly"""
        fan_out_patterns = []
        sender_activity = defaultdict(list)
        
        for tx in self.transactions:
            if tx['amount'] >= min_amount:
                sender_activity[tx['from']].append(tx)
        
        for sender, txs in sender_activity.items():
            txs.sort(key=lambda x: x['timestamp'])
            
            for i in range(len(txs)):
                window_start = txs[i]['timestamp']
                window_end = window_start + timedelta(minutes=time_window_minutes)
                
                window_txs = [tx for tx in txs[i:] if tx['timestamp'] <= window_end]
                unique_recipients = set(tx['to'] for tx in window_txs)
                
                if len(unique_recipients) >= min_recipients:
                    total_amount = sum(tx['amount'] for tx in window_txs)
                    fan_out_patterns.append({
                        'sender': sender,
                        'recipients': list(unique_recipients),
                        'recipient_count': len(unique_recipients),
                        'total_amount': total_amount,
                        'transaction_count': len(window_txs),
                        'time_window': f"{window_start} - {window_end}"
                    })
        
        return sorted(fan_out_patterns, key=lambda x: x['recipient_count'], reverse=True)