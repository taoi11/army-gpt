import json
import os
import math
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, Optional
from .logger import logger

# Constants for cost tracking
DATA_DIR = Path("/data")  # Docker volume mount point
COST_FILE = DATA_DIR / "costs.json"
CAD_USD_RATE = 0.70  # 1 CAD = 0.70 USD
MONTHLY_SERVER_RENT_USD = 15.75  # Changed to USD

# OpenRouter API settings
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

def ceil_cents(amount: float) -> float:
    """Round up to nearest cent"""
    return math.ceil(amount * 100) / 100

class CostTracker:
    def __init__(self):
        self._bootstrap()
        self.costs = self._load_costs()

    def _bootstrap(self) -> None:
        """Initialize cost.json if it doesn't exist"""
        try:
            # Create initial costs structure
            initial_costs = {
                "current_month": {
                    "api_costs_usd": 0.0,
                    "server_rent_usd": MONTHLY_SERVER_RENT_USD,  # Changed to USD
                    "billing_start_date": self._get_current_billing_start().isoformat()
                },
                "previous_months": []
            }

            # Only write if file doesn't exist
            if not COST_FILE.exists():
                logger.info("Initializing cost tracking file...")
                try:
                    # Ensure directory exists
                    DATA_DIR.mkdir(exist_ok=True)
                    # Write initial data
                    with open(COST_FILE, 'w') as f:
                        json.dump(initial_costs, f, indent=2)
                    logger.info(f"Created cost tracking file: {COST_FILE}")
                except (OSError, IOError) as e:
                    logger.warning(f"Could not create cost file: {e}")
                    # Use memory-only tracking if file operations fail
                    self.costs = initial_costs
            else:
                logger.debug("Cost tracking file exists")

        except Exception as e:
            logger.warning(f"Cost tracking initialization error: {e}")
            # Fallback to memory-only tracking
            self.costs = initial_costs

    def _load_costs(self) -> Dict:
        """Load costs from JSON file or return default structure"""
        try:
            if COST_FILE.exists():
                with open(COST_FILE, 'r') as f:
                    return json.load(f)
            else:
                # Return default structure if file doesn't exist
                return {
                    "current_month": {
                        "api_costs_usd": 0.0,
                        "server_rent_usd": MONTHLY_SERVER_RENT_USD,  # Changed to USD
                        "billing_start_date": self._get_current_billing_start().isoformat()
                    },
                    "previous_months": []
                }
        except (OSError, IOError, json.JSONDecodeError) as e:
            logger.warning(f"Could not load cost file: {e}")
            # Return default structure on error
            return {
                "current_month": {
                    "api_costs_usd": 0.0,
                    "server_rent_usd": MONTHLY_SERVER_RENT_USD,  # Changed to USD
                    "billing_start_date": self._get_current_billing_start().isoformat()
                },
                "previous_months": []
            }

    def _save_costs(self, costs: Dict) -> None:
        """Save costs to JSON file, gracefully handle failures"""
        try:
            # Ensure directory exists
            DATA_DIR.mkdir(exist_ok=True)
            # Write data
            with open(COST_FILE, 'w') as f:
                json.dump(costs, f, indent=2)
            logger.debug(f"Saved costs to file. Current total: ${costs['current_month']['api_costs_usd']:.6f} USD")
        except (OSError, IOError) as e:
            logger.warning(f"Could not save cost file: {e}")
            # Continue with in-memory tracking if file operations fail

    def _get_current_billing_start(self) -> datetime:
        """Get the start date of the current billing cycle"""
        now = datetime.now()
        if now.day >= 2:
            billing_start = datetime(now.year, now.month, 2)
        else:
            # If current day is 1, use previous month's billing date
            if now.month == 1:
                billing_start = datetime(now.year - 1, 12, 2)
            else:
                billing_start = datetime(now.year, now.month - 1, 2)
        return billing_start

    def _check_billing_cycle(self) -> None:
        """Check if we need to start a new billing cycle"""
        current_start = datetime.fromisoformat(self.costs["current_month"]["billing_start_date"])
        new_start = self._get_current_billing_start()

        if new_start > current_start:
            # Archive current month and start new one
            self.costs["previous_months"].append(self.costs["current_month"])
            self.costs["current_month"] = {
                "api_costs_usd": 0.0,
                "server_rent_usd": MONTHLY_SERVER_RENT_USD,  # Changed to USD
                "billing_start_date": new_start.isoformat()
            }
            self._save_costs(self.costs)

    async def track_api_call(self, generation_id: str) -> None:
        """Track cost of an API call using the generation ID"""
        try:
            logger.debug(f"Tracking cost for generation {generation_id}")
            response = requests.get(
                f"https://openrouter.ai/api/v1/generation?id={generation_id}",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://github.com/taoi11/army-gpt",
                    "X-Title": "Army-GPT"
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "data" in data and "total_cost" in data["data"]:
                # Add the cost to current month's total - store exact value
                self._check_billing_cycle()
                cost = float(data["data"]["total_cost"])
                
                # Update and save
                self.costs["current_month"]["api_costs_usd"] += cost
                self._save_costs(self.costs)
                logger.debug(f"Added cost: ${cost:.6f} USD")
            else:
                logger.warning("No cost data found in OpenRouter response")
                if logger.isEnabledFor(10):  # Debug level
                    logger.debug(f"OpenRouter response: {data}")
                
        except Exception as e:
            # Log error but don't fail - cost tracking is non-critical
            logger.error(f"Error tracking API cost: {str(e)}")
            if logger.isEnabledFor(10):  # Debug level
                logger.debug(f"Full error details: {str(e)}", exc_info=True)

    def get_current_costs(self) -> Dict:
        """Get current month's costs in both USD and CAD"""
        try:
            self._check_billing_cycle()
            current = self.costs["current_month"]
            
            # Get total USD cost (API + server)
            total_usd = current["api_costs_usd"] + current["server_rent_usd"]
            
            # Convert to CAD
            total_cad = total_usd / CAD_USD_RATE
            api_costs_cad = current["api_costs_usd"] / CAD_USD_RATE
            server_rent_cad = current["server_rent_usd"] / CAD_USD_RATE
            
            # Format response
            response = {
                "api_costs": {
                    "usd": ceil_cents(current["api_costs_usd"]),
                    "cad": ceil_cents(api_costs_cad),
                    "usd_exact": round(current["api_costs_usd"], 6),
                    "cad_exact": round(api_costs_cad, 6)
                },
                "server_rent": {
                    "usd": current["server_rent_usd"],
                    "cad": ceil_cents(server_rent_cad)
                },
                "total": {
                    "usd": ceil_cents(total_usd),
                    "cad": ceil_cents(total_cad)
                },
                "billing_start": current["billing_start_date"]
            }
            
            if logger.isEnabledFor(10):  # Only log in debug mode
                logger.debug(f"Returning costs: {response}")
            return response
            
        except KeyError as e:
            logger.error(f"Missing key in cost data: {e}")
            return {
                "api_costs": {"usd": 0.00, "cad": 0.00},
                "server_rent": {"usd": MONTHLY_SERVER_RENT_USD, "cad": MONTHLY_SERVER_RENT_USD / CAD_USD_RATE},
                "total": {"usd": MONTHLY_SERVER_RENT_USD, "cad": MONTHLY_SERVER_RENT_USD / CAD_USD_RATE},
                "billing_start": self._get_current_billing_start().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating costs: {str(e)}")
            raise

# Create singleton instance
cost_tracker = CostTracker() 