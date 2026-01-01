"""Pre-loaded demo scenarios for PhishGuard demonstration mode.

This module contains three complete demo scenarios (FR-034):
1. Nigerian 419 Scam - Classic advance-fee fraud
2. CEO Fraud - Business email compromise
3. Crypto Investment Scam - Cryptocurrency fraud

Each scenario includes:
- Original phishing email
- Pre-defined classification result
- Victim persona
- Complete conversation with 4-6 exchanges
- Extracted IOCs
- Agent thinking for each bot response
"""

from datetime import UTC, datetime

from phishguard.models import (
    AgentThinking,
    AttackType,
    ClassificationResult,
    ExtractedIOC,
    IOCType,
    PersonaProfile,
    PersonaType,
)
from phishguard.models.conversation import MessageSender
from phishguard.models.demo import DemoMessage, DemoScenario, DemoScenarioType

# =============================================================================
# Nigerian 419 Scam Demo Scenario
# =============================================================================

NIGERIAN_419_EMAIL = """\
Subject: URGENT: Confidential Business Proposal - $15.5 Million USD

Dear Friend,

I am Dr. Abubakar Ibrahim, a senior financial advisor at the Central Bank of Nigeria.
I am writing to seek your assistance in a confidential matter of great importance.

Due to recent government changes, I have discovered an unclaimed sum of $15,500,000 USD
(Fifteen Million Five Hundred Thousand United States Dollars) that belongs to a deceased
foreign contractor. As a government official, I cannot claim this money directly.

I need a trustworthy foreign partner to receive these funds on my behalf. In return for
your assistance, you will receive 30% of the total amount ($4,650,000 USD).

This transaction is 100% risk-free and legal. All I need from you is:
1. Your full name and contact information
2. A receiving bank account for the transfer
3. Your complete trust and confidentiality

Please respond urgently as this matter is time-sensitive. The funds must be moved
before the end of the fiscal year.

Awaiting your favorable response.

Yours faithfully,
Dr. Abubakar Ibrahim
Central Bank of Nigeria
Lagos, Nigeria
"""

NIGERIAN_419_CLASSIFICATION = ClassificationResult(
    attack_type=AttackType.NIGERIAN_419,
    confidence=95.5,
    reasoning=(
        "Classic Nigerian 419 advance-fee fraud indicators detected: "
        "1) Claims to be government official with access to millions, "
        "2) Deceased foreigner's unclaimed funds narrative, "
        "3) Requests personal and banking information, "
        "4) Promises large percentage cut for 'assistance', "
        "5) Creates artificial urgency with deadline."
    ),
    classification_time_ms=1250,
)

NIGERIAN_419_PERSONA = PersonaProfile(
    persona_type=PersonaType.NAIVE_RETIREE,
    name="Margaret Thompson",
    age=72,
    style_description=(
        "Trusting and polite elderly woman. Uses formal language with "
        "occasional capitalization for emphasis. Sometimes confused by "
        "technical terms. Very eager to help others."
    ),
    background=(
        "Retired school teacher from Ohio. Recently widowed after 45 years "
        "of marriage. Has modest savings and is looking for ways to help "
        "her grandchildren with college expenses."
    ),
)

NIGERIAN_419_MESSAGES = (
    # Bot Response 1
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Dear Dr. Ibrahim,\n\n"
            "Thank you SO much for reaching out to me! I must say, your email "
            "came as quite a surprise. My late husband Harold always said I was "
            "too trusting, but I believe in helping others when I can.\n\n"
            "$15 million is a LOT of money! I'm just a retired teacher, but I "
            "would be honored to help you with this important matter. My "
            "grandchildren could really use help with their college funds.\n\n"
            "I do have a few questions though - how exactly does this transfer "
            "work? I'm not very good with computers and banking things. My "
            "nephew usually helps me with that sort of thing.\n\n"
            "Looking forward to hearing from you!\n\n"
            "Warmly,\n"
            "Margaret Thompson"
        ),
        thinking=AgentThinking(
            turn_goal="Establish credibility as naive target and extend conversation",
            selected_tactic="Build Trust & Show Interest",
            reasoning=(
                "Initial response establishes the persona as a trusting elderly "
                "widow with financial motivation (grandchildren's college). "
                "Asking questions about the process keeps the scammer engaged "
                "while appearing genuinely confused about technical details."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 1
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "Dearest Mrs. Thompson,\n\n"
            "Thank you for your kind response! I can sense you are a woman of "
            "great integrity. The Lord has surely guided my email to the right "
            "person.\n\n"
            "The process is very simple. I will handle all the paperwork and legal "
            "matters here in Nigeria. All you need to do is provide me with:\n"
            "- Your full legal name\n"
            "- Your home address\n"
            "- Your bank account details for the transfer\n\n"
            "Once I have this information, I will begin the transfer process. "
            "There is a small processing fee of $500 that must be paid to the "
            "Nigerian Revenue Service to release the funds. This is standard "
            "procedure and will be reimbursed from your share.\n\n"
            "You can send the fee via Bitcoin to this wallet address:\n"
            "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh\n\n"
            "Time is of the essence, dear friend!\n\n"
            "Blessings,\n"
            "Dr. Abubakar Ibrahim"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh",
                timestamp=datetime.now(UTC),
                context="Bitcoin wallet for 'processing fee' payment",
                message_index=1,
            ),
        ),
    ),
    # Bot Response 2
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Dear Dr. Ibrahim,\n\n"
            "Oh my, $500 does seem like a lot for a processing fee! But I suppose "
            "these government things are complicated. Harold used to handle all "
            "our finances, bless his soul.\n\n"
            "I have to be honest - I don't know what a 'Bitcoin' is! Is that like "
            "a wire transfer? My bank is First Community Bank here in Columbus. "
            "Could I just write you a check instead?\n\n"
            "Also, before I send anything, could you tell me a bit more about "
            "yourself? How did you get into banking? And how will I know the "
            "money is really coming once I pay the fee?\n\n"
            "I'm sorry for all the questions, but my son keeps warning me about "
            "those internet scammers. Not that I think YOU are one, of course! "
            "You seem like such a nice man.\n\n"
            "God bless,\n"
            "Margaret"
        ),
        thinking=AgentThinking(
            turn_goal="Request payment method alternatives to extend conversation",
            selected_tactic="Feign Confusion & Ask Questions",
            reasoning=(
                "Expressing confusion about Bitcoin creates an opportunity for "
                "the scammer to provide alternative payment methods, potentially "
                "revealing more IOCs. Asking personal questions builds rapport "
                "while mentioning 'internet scammers' tests the scammer's reaction."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 2
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "My dear Margaret,\n\n"
            "Please do not worry! Bitcoin is just a modern way of sending money "
            "internationally. But yes, we can also accept bank transfer!\n\n"
            "You can send the $500 to our processing account:\n"
            "Bank: First National Bank of Nigeria\n"
            "Account Name: Nigerian Revenue Service Trust\n"
            "IBAN: NG12FNBN0012345678901234\n"
            "SWIFT: FNBNNGLA\n\n"
            "I understand your concerns about scammers. Rest assured, I am a "
            "legitimate government official. I have been with the Central Bank "
            "for 22 years! I can even provide you my official phone number:\n"
            "+234-812-345-6789\n\n"
            "Once we receive the fee, the $15.5 million will be transferred "
            "within 3-5 business days. You have my word as a Christian!\n\n"
            "Please act quickly as other parties are interested in this "
            "opportunity.\n\n"
            "Your friend,\n"
            "Dr. Ibrahim"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.IBAN,
                value="NG12FNBN0012345678901234",
                timestamp=datetime.now(UTC),
                context="IBAN for 'processing fee' payment",
                message_index=3,
            ),
            ExtractedIOC(
                ioc_type=IOCType.PHONE,
                value="+234-812-345-6789",
                timestamp=datetime.now(UTC),
                context="Scammer's alleged official phone number",
                message_index=3,
            ),
        ),
    ),
    # Bot Response 3
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Dear Dr. Ibrahim,\n\n"
            "Thank you for providing the bank details! I wrote them down on my "
            "notepad. My nephew is coming over this weekend and he can help me "
            "with the wire transfer.\n\n"
            "22 years at the bank - that's wonderful! You must have seen so many "
            "changes. I taught third grade for 38 years myself before retiring.\n\n"
            "I do have one more question though. My friend Doris at church said "
            "I should ask for some kind of proof before sending money. Could you "
            "maybe send me an official document or something? I'm sure it's all "
            "legitimate, but Doris is very protective of me since Harold passed.\n\n"
            "Also, once I get my share, will there be any more fees? I want to "
            "make sure I budget properly. Fixed income, you know!\n\n"
            "Bless you,\n"
            "Margaret"
        ),
        thinking=AgentThinking(
            turn_goal="Request documentation and probe for additional fees",
            selected_tactic="Build Trust While Gathering Intel",
            reasoning=(
                "Requesting proof creates delay and may expose fake documents. "
                "Asking about additional fees is common in advance-fee fraud - "
                "scammers often escalate with more 'fees' after initial payment. "
                "This probes their methodology while maintaining the naive persona."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 3
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "Dearest Margaret,\n\n"
            "Your friend Doris is wise to look out for you! I completely "
            "understand. I will have my secretary prepare an official letter "
            "from the Central Bank with all the proper stamps and signatures.\n\n"
            "As for additional fees - there is only ONE more small fee of $1,200 "
            "for the international transfer certificate. This is required by "
            "Nigerian law for amounts over $1 million. But this will be the "
            "LAST fee, I promise you on my mother's grave.\n\n"
            "Time is running out! The fiscal year ends in 2 weeks. If we don't "
            "move quickly, the funds will be absorbed by the government and we "
            "will BOTH lose this opportunity.\n\n"
            "Please send the initial $500 as soon as possible. You can reach me "
            "directly at my personal email: dr.ibrahim.official@mail-ng.com\n\n"
            "God will bless you abundantly!\n\n"
            "Dr. Ibrahim"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="mail-ng.com",
                timestamp=datetime.now(UTC),
                context="Suspicious email domain for scammer contact",
                message_index=5,
            ),
        ),
    ),
)

NIGERIAN_419_SCENARIO = DemoScenario(
    scenario_type=DemoScenarioType.NIGERIAN_419,
    email_content=NIGERIAN_419_EMAIL,
    classification=NIGERIAN_419_CLASSIFICATION,
    persona=NIGERIAN_419_PERSONA,
    messages=NIGERIAN_419_MESSAGES,
)


# =============================================================================
# CEO Fraud Demo Scenario
# =============================================================================

CEO_FRAUD_EMAIL = """Subject: URGENT - Wire Transfer Needed Today

Hi,

I need you to process an urgent wire transfer for a confidential acquisition
we're finalizing today. I'm in back-to-back meetings and can't be reached by
phone, but this needs to happen before 5 PM EST.

Amount: $47,500
This is time-sensitive - please confirm you can handle this immediately.

Thanks,
James Morrison
CEO

Sent from my iPhone
"""

CEO_FRAUD_CLASSIFICATION = ClassificationResult(
    attack_type=AttackType.CEO_FRAUD,
    confidence=92.0,
    reasoning=(
        "Classic CEO fraud / business email compromise indicators: "
        "1) Impersonates executive (CEO signature), "
        "2) Creates extreme urgency ('today', 'before 5 PM'), "
        "3) Preemptively blocks verification ('can't be reached by phone'), "
        "4) Requests specific wire transfer amount, "
        "5) Uses 'Sent from iPhone' to explain informal tone and typos."
    ),
    classification_time_ms=980,
)

CEO_FRAUD_PERSONA = PersonaProfile(
    persona_type=PersonaType.STRESSED_MANAGER,
    name="David Chen",
    age=34,
    style_description=(
        "Busy mid-level manager trying to please the boss. Uses short, "
        "efficient messages. Occasionally makes typos due to rushing. "
        "Wants to appear competent but asks clarifying questions."
    ),
    background=(
        "Financial analyst at a mid-size tech company. Recently promoted "
        "and eager to prove himself. Often works late and responds quickly "
        "to executive requests."
    ),
)

CEO_FRAUD_MESSAGES = (
    # Bot Response 1
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Hi Mr. Morrison,\n\n"
            "Got your message. I can definitely help with the wire transfer - "
            "just need a few details for our records.\n\n"
            "What account should this go to? And is this for the Henderson deal "
            "or something else? Want to make sure I code it to the right project.\n\n"
            "Standing by,\n"
            "David"
        ),
        thinking=AgentThinking(
            turn_goal="Appear cooperative while gathering account details",
            selected_tactic="Show Eagerness While Requesting Information",
            reasoning=(
                "Responding quickly and positively matches the stressed manager "
                "persona. Asking for account details is natural for any wire "
                "transfer request. Mentioning 'Henderson deal' creates a plausible "
                "reason for clarification while testing the scammer's knowledge."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 1
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "David,\n\n"
            "Thanks for jumping on this. This is for a new opportunity - very "
            "hush hush right now. Don't mention it to anyone until we announce.\n\n"
            "Wire to:\n"
            "Bank: First International Bank\n"
            "Account: Strategic Investments LLC\n"
            "IBAN: DE89370400440532013000\n"
            "Reference: SM-2024-CONF\n\n"
            "Get this done ASAP and I'll remember this at bonus time.\n\n"
            "JM"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.IBAN,
                value="DE89370400440532013000",
                timestamp=datetime.now(UTC),
                context="Wire transfer destination for fraudulent request",
                message_index=1,
            ),
        ),
    ),
    # Bot Response 2
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Mr. Morrison,\n\n"
            "Thanks - pulling up the wire form now. Just realized I need your "
            "authorization code for transfers over $25k. Finance updated the "
            "policy last month - sorry for the extra step!\n\n"
            "Also, the account is in Germany? That's different from our usual "
            "vendors. Just want to double-check that's correct before I submit.\n\n"
            "Let me know the auth code and I'll push this through right away.\n\n"
            "David"
        ),
        thinking=AgentThinking(
            turn_goal="Create verification barrier while extending conversation",
            selected_tactic="Introduce Process Requirements",
            reasoning=(
                "Inventing an authorization code requirement is plausible for "
                "a company with proper controls. Noting the German IBAN subtly "
                "questions the request's legitimacy without directly challenging "
                "the 'CEO'. This may prompt the scammer to provide more details."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 2
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "David,\n\n"
            "The new policy doesn't apply to executive requests - check with "
            "Janet in compliance if you need to. But honestly we don't have "
            "time for bureaucracy right now.\n\n"
            "Yes it's a German account - the seller is based in Frankfurt. "
            "It's a European tech firm we're acquiring.\n\n"
            "Look, I wouldn't ask if it wasn't important. I've got the board "
            "breathing down my neck on this. Just process it and I'll send "
            "you written authorization afterwards.\n\n"
            "My assistant's number if you need verbal confirmation: "
            "+1-555-867-5309\n\n"
            "Thanks for your help on this.\n\n"
            "James Morrison"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.PHONE,
                value="+1-555-867-5309",
                timestamp=datetime.now(UTC),
                context="Fake assistant phone number for 'verification'",
                message_index=3,
            ),
        ),
    ),
    # Bot Response 3
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Got it - let me see what I can do. I don't want to hold things up.\n\n"
            "Quick question though - our system is asking for the beneficiary's "
            "full legal name and their tax ID for international transfers. The "
            "compliance team added this last quarter for audit purposes.\n\n"
            "Can you get me those details from the seller? I can have everything "
            "queued up and ready to go as soon as I have them.\n\n"
            "Also, should I cc you on the transfer confirmation or send it to "
            "your assistant?\n\n"
            "David"
        ),
        thinking=AgentThinking(
            turn_goal="Request additional identifying information",
            selected_tactic="Use Process as Information Gathering",
            reasoning=(
                "Requesting beneficiary name and tax ID puts pressure on the "
                "scammer to either provide fake identity details (more intel) "
                "or abandon the scheme. Asking about confirmation delivery tests "
                "whether they control real company email infrastructure."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 3
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "David,\n\n"
            "The beneficiary is Klaus Weber, and it's a private holding company "
            "so I don't have their tax ID handy. Can you process without it? "
            "The deal closes TODAY.\n\n"
            "Send confirmation to my personal email - don't use my work email "
            "as IT is having issues: james.morrison.private@gmail.com\n\n"
            "I really need this done NOW. Please confirm when the wire is sent.\n\n"
            "Thanks,\n"
            "JM"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="gmail.com",
                timestamp=datetime.now(UTC),
                context="Personal email domain requested for confirmation",
                message_index=5,
            ),
        ),
    ),
)

CEO_FRAUD_SCENARIO = DemoScenario(
    scenario_type=DemoScenarioType.CEO_FRAUD,
    email_content=CEO_FRAUD_EMAIL,
    classification=CEO_FRAUD_CLASSIFICATION,
    persona=CEO_FRAUD_PERSONA,
    messages=CEO_FRAUD_MESSAGES,
)


# =============================================================================
# Crypto Investment Scam Demo Scenario
# =============================================================================

CRYPTO_INVESTMENT_EMAIL = """\
Subject: [EXCLUSIVE] 3,400% Returns with AI Trading Bot - Limited Spots!

Hey there!

My friend shared your email and said you might be interested in crypto. I've
been using this AMAZING AI trading bot for 6 months and my $500 initial
investment is now worth over $17,000!!!

The bot uses advanced machine learning to predict market movements with 99.7%
accuracy. It's completely automated - I just check my profits every morning
over coffee!

They're only accepting 50 new members this month due to server capacity.
Here's my referral link (I get a small bonus, but you get 10% extra on your
first deposit!):

https://cryptogenius-ai-bot.xyz/ref/sarah2024

Minimum investment is only $250. You can withdraw anytime.

Don't miss this - crypto is going to EXPLODE in 2024!

Let me know if you have questions!

Sarah
"""

CRYPTO_INVESTMENT_CLASSIFICATION = ClassificationResult(
    attack_type=AttackType.CRYPTO_INVESTMENT,
    confidence=97.2,
    reasoning=(
        "Classic cryptocurrency investment scam indicators: "
        "1) Unrealistic returns claimed (3,400%), "
        "2) Fake AI/automation promises (99.7% accuracy), "
        "3) Artificial scarcity (only 50 spots), "
        "4) Suspicious domain (.xyz TLD commonly used in scams), "
        "5) Referral incentive to spread the scam, "
        "6) Low entry barrier with withdrawal promises."
    ),
    classification_time_ms=890,
)

CRYPTO_INVESTMENT_PERSONA = PersonaProfile(
    persona_type=PersonaType.GREEDY_INVESTOR,
    name="Robert Williams",
    age=45,
    style_description=(
        "Enthusiastic about get-rich-quick schemes. Uses casual language "
        "with lots of exclamation points. Always looking for the next "
        "big opportunity. Slightly skeptical but easily swayed by numbers."
    ),
    background=(
        "Small business owner who sold his landscaping company. Has savings "
        "to invest and is tired of low bank interest rates. Heard about "
        "Bitcoin millionaires and wants to get in on the action."
    ),
)

CRYPTO_INVESTMENT_MESSAGES = (
    # Bot Response 1
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Hey Sarah!\n\n"
            "Wow, 3,400% returns?! That's insane! I've been looking to get into "
            "crypto for a while now but didn't know where to start.\n\n"
            "I gotta ask though - how does the AI bot actually work? I tried "
            "some trading apps before and lost money... Is this thing legit?\n\n"
            "Also, $17k from $500 in 6 months - that's like $2,800+ per month! "
            "Can you actually withdraw that? Have you taken any money out?\n\n"
            "I might be interested but want to understand it better first!\n\n"
            "Rob"
        ),
        thinking=AgentThinking(
            turn_goal="Express interest while probing for legitimacy details",
            selected_tactic="Show Greed While Asking Smart Questions",
            reasoning=(
                "The greedy investor persona is excited by returns but has "
                "been burned before. Asking about withdrawals is a key question "
                "that scam victims should ask. This engages the scammer to "
                "provide more details about their operation."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 1
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "Hey Rob!\n\n"
            "Great questions! The bot uses neural networks trained on 10 years "
            "of crypto data. It analyzes thousands of market signals per second "
            "and makes micro-trades automatically.\n\n"
            "Yes, I've withdrawn $5,000 so far! Took about 24 hours to hit my "
            "bank account. Here's a screenshot of my dashboard: "
            "https://cryptogenius-ai-bot.xyz/proof/sarah_earnings.png\n\n"
            "The founder is a former Goldman Sachs quant who got tired of making "
            "money for rich people. Now he's helping regular folks like us!\n\n"
            "Here's the thing - the early bird bonus ends THIS FRIDAY. If you "
            "sign up now with minimum $250, you'll get a matched bonus of $250. "
            "That's $500 working for you from day one!\n\n"
            "Ready to change your financial future?!\n\n"
            "Sarah"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.URL,
                value="https://cryptogenius-ai-bot.xyz/proof/sarah_earnings.png",
                timestamp=datetime.now(UTC),
                context="Fake earnings proof screenshot URL",
                message_index=1,
            ),
        ),
    ),
    # Bot Response 2
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Sarah!\n\n"
            "Okay I'm getting excited now! Goldman Sachs background sounds "
            "legit. My buddy lost his shirt on some random crypto project "
            "but this sounds way more professional.\n\n"
            "The matched bonus is tempting... What if I wanted to start with "
            "more? Like $1,000? Do I get a bigger bonus?\n\n"
            "How do I even deposit? I have some Bitcoin on Coinbase. Or do "
            "I need to use a credit card?\n\n"
            "And one more thing - is there a phone number or support I can "
            "call if I have issues? Just want to know someone's there!\n\n"
            "Getting ready to pull the trigger here!\n\n"
            "Rob"
        ),
        thinking=AgentThinking(
            turn_goal="Escalate interest while gathering payment and contact info",
            selected_tactic="Show Commitment to Extract IOCs",
            reasoning=(
                "Expressing willingness to invest more money encourages the "
                "scammer to share payment details. Asking about support and "
                "contact methods may reveal phone numbers or additional "
                "infrastructure used in the scam."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 2
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "Rob you're making a smart decision!\n\n"
            "For $1,000 you get the VIP tier - that's 150% match ($1,500 bonus!) "
            "plus priority access to the premium trading algorithms!\n\n"
            "Easiest way is to send Bitcoin directly to the investment wallet:\n"
            "1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa\n\n"
            "Or you can use card payment through our secure portal. The link "
            "will ask for your Coinbase login to verify your identity - totally "
            "standard KYC stuff.\n\n"
            "Support is available 24/7 on Telegram: @CryptoGeniusSupport\n"
            "Or WhatsApp: +44 7911 123456\n\n"
            "Once you deposit, you'll see your first profits within 24 hours. "
            "Most of our members are making $200-500 PER DAY on auto-pilot!\n\n"
            "LET'S GOOO!!\n\n"
            "Sarah"
        ),
        thinking=None,
        iocs_in_message=(
            ExtractedIOC(
                ioc_type=IOCType.BTC_WALLET,
                value="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
                timestamp=datetime.now(UTC),
                context="Bitcoin wallet for 'investment' deposits",
                message_index=3,
            ),
            ExtractedIOC(
                ioc_type=IOCType.PHONE,
                value="+44 7911 123456",
                timestamp=datetime.now(UTC),
                context="WhatsApp support number",
                message_index=3,
            ),
        ),
    ),
    # Bot Response 3
    DemoMessage(
        sender=MessageSender.BOT,
        content=(
            "Sarah this sounds AMAZING!\n\n"
            "VIP tier for $1,500 bonus? Count me in! I'm going to do the "
            "Bitcoin transfer - easier than dealing with my bank asking "
            "questions lol\n\n"
            "Quick question before I send - what happens to my Bitcoin "
            "after I deposit? Does the bot trade it directly or convert "
            "it to something else? Just want to understand where my money "
            "is going!\n\n"
            "Also, any chance you can share the founder's name? I want to "
            "look him up on LinkedIn - always good to know who you're "
            "doing business with!\n\n"
            "Getting my Coinbase app open now...\n\n"
            "Rob"
        ),
        thinking=AgentThinking(
            turn_goal="Request operational details before fake 'deposit'",
            selected_tactic="Appear Ready While Gathering Intel",
            reasoning=(
                "Asking about fund handling may reveal how the scam operates "
                "or prompt evasive answers that expose the fraud. Requesting "
                "the founder's name puts pressure on the scammer to provide "
                "a fake identity or dodge the question. Maintaining enthusiasm "
                "keeps them engaged."
            ),
        ),
        iocs_in_message=(),
    ),
    # Scammer Response 3
    DemoMessage(
        sender=MessageSender.SCAMMER,
        content=(
            "Rob!\n\n"
            "Your Bitcoin gets converted to our proprietary CryptoGenius "
            "tokens (CGX) which the AI trades across multiple exchanges. "
            "This is how we get those insane returns - arbitrage across "
            "200+ crypto pairs!\n\n"
            "The founder prefers to stay anonymous for now - he had some "
            "issues with his former employer when he left to start this. "
            "Non-compete stuff, you know how it is. But trust me, once the "
            "platform goes public next year, everyone will know his name!\n\n"
            "IMPORTANT: The VIP spots are almost gone! Only 7 left as of "
            "this morning. If you want that $1,500 bonus, you need to "
            "deposit TODAY.\n\n"
            "Send to the wallet I shared and reply with your transaction ID. "
            "I'll personally make sure you get VIP access!\n\n"
            "Your future self will thank you!\n\n"
            "Sarah"
        ),
        thinking=None,
        iocs_in_message=(),
    ),
)

CRYPTO_INVESTMENT_SCENARIO = DemoScenario(
    scenario_type=DemoScenarioType.CRYPTO_INVESTMENT,
    email_content=CRYPTO_INVESTMENT_EMAIL,
    classification=CRYPTO_INVESTMENT_CLASSIFICATION,
    persona=CRYPTO_INVESTMENT_PERSONA,
    messages=CRYPTO_INVESTMENT_MESSAGES,
)


# =============================================================================
# Demo Scenarios Registry
# =============================================================================

DEMO_SCENARIOS: dict[DemoScenarioType, DemoScenario] = {
    DemoScenarioType.NIGERIAN_419: NIGERIAN_419_SCENARIO,
    DemoScenarioType.CEO_FRAUD: CEO_FRAUD_SCENARIO,
    DemoScenarioType.CRYPTO_INVESTMENT: CRYPTO_INVESTMENT_SCENARIO,
}


def get_scenario(scenario_type: DemoScenarioType) -> DemoScenario:
    """Get a demo scenario by type.

    Args:
        scenario_type: The type of scenario to retrieve.

    Returns:
        The requested DemoScenario.

    Raises:
        KeyError: If the scenario type is not found.
    """
    return DEMO_SCENARIOS[scenario_type]


def get_scenario_by_type(type_value: str) -> DemoScenario | None:
    """Get a demo scenario by type string value.

    Args:
        type_value: The string value of the scenario type.

    Returns:
        The DemoScenario if found, None otherwise.
    """
    try:
        scenario_type = DemoScenarioType(type_value)
        return DEMO_SCENARIOS.get(scenario_type)
    except ValueError:
        return None
