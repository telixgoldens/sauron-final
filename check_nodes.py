import requests

CANDIDATES = [
                
    "https://babylon.api.kjnodes.com",              
    "https://babylon-mainnet.api.kjnodes.com", 
    "https://babylon-archive.nodes.guru/api",     
    "https://api.babylon.nodes.guru",               
    "https://babylon-api.lavenderfive.com",         
    "https://babylon-api.dankhash.net" ,
    "https://mainnet-babylon-api.highstakes.ch"             
]

print("Scanning for working Babylon Mainnet Nodes...")

working_node = None

for url in CANDIDATES:
    try:
        print(f"👉 Testing: {url} ... ", end="")
        
        resp = requests.get(f"{url}/cosmos/base/tendermint/v1beta1/blocks/latest", timeout=5)
        
        if resp.status_code == 200:
            height = resp.json()['block']['header']['height']
            print(f"SUCCESS! (Height: {height})")
            working_node = url
            break 
        else:
            print(f"Failed (Status: {resp.status_code})")
            
    except Exception as e:
        print(f"Connection Error")

print("-" * 30)
if working_node:
    print(f"RECOMMENDED NODE: {working_node}")
    print("Update your script to use this URL.")
else:
    print("No public nodes are reachable right now. The network might be congested.")