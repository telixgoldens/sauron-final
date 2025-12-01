import networkx as nx
from pyvis.network import Network
import pandas as pd
import os

def generate_cluster_map(df, center_address):
    try:
        G = nx.Graph()
        G.add_node(center_address, title="TARGET", color="#FF4B4B", size=30, label="TARGET")
        
        # Build Graph
        if 'sender' in df.columns and 'amount' in df.columns:
            grouped = df.groupby('sender')['amount'].sum().reset_index()
            for _, row in grouped.iterrows():
                sender = row['sender']
                total_vol = row['amount']
                if sender != center_address:
                    color = "#FFA500" if total_vol > 1000 else "#97C2FC"
                    size = 15 if total_vol > 1000 else 8
                    
                    # Tooltip with volume
                    title_text = f"Address: {sender}\nVol: {total_vol}"
                    G.add_node(sender, title=title_text, color=color, size=size)
                    G.add_edge(center_address, sender, weight=total_vol, color="rgba(255,255,255,0.3)")

        # Create Network
        net = Network(height="600px", width="100%", bgcolor="#0E1117", font_color="white")
        net.from_nx(G)
        net.force_atlas_2based()
        
        # --- THE FIX FOR WINDOWS ---
        # 1. Generate HTML string directly using write_html (if available) 
        # or save with explicit encoding.
        tmp_name = "graph.html"
        
        # Save the graph
        net.save_graph(tmp_name)
        
        # Read it back with FORCED UTF-8 encoding
        with open(tmp_name, 'r', encoding='utf-8') as f:
            html = f.read()
            
        # Clean up
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
            
        return html

    except Exception as e:
        # Return the error in red text so we can see it in the dashboard
        return f"<div style='color:red; padding:20px;'>Graph Error: {str(e)}</div>"