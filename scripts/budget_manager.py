import json
import os
from datetime import datetime

LOG_FILE = "logs/expenditure.json"

# Claude 3.5 Sonnet pricing (USD per 1M tokens)
PRICE_INPUT = 3.00
PRICE_OUTPUT = 15.00
EXCHANGE_RATE_THB = 36.0  # Default rate

def get_spent():
    if not os.path.exists(LOG_FILE):
        return 0.0
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
            return data.get("total_spent_usd", 0.0)
    except:
        return 0.0

def can_afford(max_budget_usd):
    return get_spent() < max_budget_usd

def record_usage(batch_id, input_tokens, output_tokens):
    cost_usd = (input_tokens / 1_000_000 * PRICE_INPUT) + (output_tokens / 1_000_000 * PRICE_OUTPUT)
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {"total_spent_usd": 0.0, "history": []}
        
    data["total_spent_usd"] += cost_usd
    data["history"].append({
        "timestamp": datetime.now().isoformat(),
        "batch_id": batch_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost_usd, 4),
        "cost_thb": round(cost_usd * EXCHANGE_RATE_THB, 2)
    })
    
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
    return cost_usd

def get_report():
    spent = get_spent()
    return f"Total Spent: ${spent:.4f} (~{spent * EXCHANGE_RATE_THB:.2f} THB)"

if __name__ == "__main__":
    print(get_report())
