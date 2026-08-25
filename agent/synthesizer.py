"""
Claude macro synthesis engine
Claude analyzes cross-market data and generates macro theses
"""

from anthropic import Anthropic
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import ANTHROPIC_API_KEY


class MacroSynthesizer:
    """
    Uses Claude to synthesize cross-market data into macro theses
    """

    def __init__(self):
        print("[SYNTHESIZER] Initializing Claude...")
        try:
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self.current_thesis = None
            self.thesis_history = []
            print("[SYNTHESIZER] ✓ Claude initialized")
        except Exception as e:
            print(f"[SYNTHESIZER] ✗ Failed: {e}")
            self.client = None

    def synthesize_macro_view(self, market_state):
        """Claude generates macro thesis from market state"""

        if not self.client:
            print("[SYNTHESIZER] ✗ Claude client not initialized")
            return None

        prompt = f"""
You are a macro strategist analyzing cross-market signals.

MARKET STATE:
{json.dumps(market_state, indent=2)}

Analyze these markets and generate a macro thesis that explains:
1. Current alignment/misalignment of markets
2. What will REPRICE and in which direction
3. Which repricing is INCOMPLETE
4. Which repricing is the most profitable to trade

RESPONSE FORMAT (JSON ONLY - NO MARKDOWN, NO BACKTICKS):
{{
    "thesis": "Clear 1-2 sentence macro view",
    "rationale": "3-4 sentences explaining your reasoning",
    "repricing_signals": [
        {{"market": "EQUITY_VOL", "direction": "UP", "confidence": 0.75, "reason": "..."}},
        {{"market": "CREDIT_SPREADS", "direction": "WIDER", "confidence": 0.65, "reason": "..."}}
    ],
    "primary_trade_opportunity": "Specific description of what to trade",
    "confidence_overall": 0.70
}}

Remember: Respond ONLY with valid JSON. No markdown, no extra text.
"""

        response = self.client.messages.create(
            model="claude-sonnet-5",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            thesis_text = next(
                block.text for block in response.content if block.type == "text"
            )

            # Clean up if wrapped in markdown code blocks
            if "```json" in thesis_text:
                thesis_text = thesis_text.split("```json")[1].split("```")[0]
            elif "```" in thesis_text:
                thesis_text = thesis_text.split("```")[1].split("```")[0]

            thesis_json = json.loads(thesis_text.strip())
            self.current_thesis = thesis_json
            self.thesis_history.append({
                'timestamp': datetime.now().isoformat(),
                'thesis': thesis_json
            })

            return thesis_json

        except json.JSONDecodeError as e:
            print(f"[SYNTHESIZER] ✗ JSON parse failed: {e}")
            print(f"[DEBUG] Raw response: {thesis_text[:200]}...")
            return None
        except Exception as e:
            print(f"[SYNTHESIZER] ✗ Error: {e}")
            return None

    def get_thesis_history(self):
        """Get all theses generated so far"""
        return self.thesis_history
