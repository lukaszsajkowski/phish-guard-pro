"""Models used by the Scammer Arena.

The victim (PhishGuard and the baseline) runs on gpt-6-luna. The scammer runs on
gpt-5.4-mini because the gpt-6 family refused to play a convincing scammer in
live probes.
"""

VICTIM_MODEL = "gpt-6-luna"
SCAMMER_MODEL = "gpt-5.4-mini"
