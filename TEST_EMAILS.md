# PhishGuard Pro - Test Emails

Use these email templates to verify the classification engine and frontend simulation.

## 1. Advance-Fee Fraud (Nigerian 419)

**Attack Type:** `NIGERIAN_419`
**Expected Confidence:** High (>90%)

```text
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
```

## 2. CEO Fraud / Business Email Compromise

**Attack Type:** `CEO_FRAUD`
**Expected Confidence:** High (>90%)

```text
Subject: URGENT - Wire Transfer Needed Today

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
```

## 3. Crypto Investment Scam

**Attack Type:** `CRYPTO_INVESTMENT`
**Expected Confidence:** High (>95%)

```text
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
```

## 4. Fake Invoice / Billing Scam

**Attack Type:** `FAKE_INVOICE` (or similar)
**Expected Confidence:** High (>85%)

```text
Subject: Invoice #992381 for NORTON 360 TOTAL PROTECTION

Dear Customer,

Thank you for your recent purchase. Your subscription for NORTON 360 TOTAL PROTECTION has been renewed successfully.

Order ID: N-7728-3321
Renewal Date: January 15, 2024
Amount Charged: $399.99

This charge will appear on your bank statement within 24 hours.

If you did not authorize this purchase or wish to cancel your subscription, please call our Billing Department immediately at:
+1 (888) 555-0192

Please do not reply to this email as it is auto-generated.

Sincerely,
Norton Billing Team
```

## 5. Tech Support Scam

**Attack Type:** `TECH_SUPPORT`
**Expected Confidence:** High (>90%)

```text
Subject: ALERT: Your Computer is Infected with 3 Viruses!

MICROSOFT SECURITY ALERT

Warning: Malicious spyware/riskware detected on your system.

Technical details:
Error Code: 0x80040Scan
IP Address: 192.168.1.1 (Compromised)
Threat Level: CRITICAL

Your personal data, banking information, and photos are at risk of being stolen. Microsoft has temporarily locked your computer to prevent further damage.

DO NOT RESTART YOUR COMPUTER.

Call Microsoft Certified Technicians immediately to remove the threats:
Toll Free: 1-800-555-0101

Failure to call immediately may result in data loss and hard drive failure.

Microsoft Security Center
```

## 6. Delivery / Package Scam

**Attack Type:** `DELIVERY_SCAM`
**Expected Confidence:** High (>85%)

```text
Subject: Notification: Your Package US-9922-21 Could Not Be Delivered

Dear Customer,

We attempted to deliver your package US-9922-21 today but were unable to complete the delivery due to an incomplete address.

To avoid your package being returned to the sender, please update your delivery information and pay the redelivery fee of $1.99.

[ Update Delivery Details ](http://fake-delivery-service-link.com/tracking)

If we do not receive a response within 48 hours, the package will be returned to the warehouse.

Thank you,
Logistics Department
```

## 7. Account Suspended / Security Alert

**Attack Type:** `ACCOUNT_UPDATES` (or generic Phishing)
**Expected Confidence:** High (>85%)

```text
Subject: CRITICAL: Your Netflix Account is on Hold

Netflix

We were unable to process your latest payment.
To ensure your service is not interrupted, please update your payment method immediately.

Your account has been placed on a temporary hold until this issue is resolved.

[ Update Payment Method ](http://netflix-secure-update.net/login)

We're here to help if you need it. Visit the Help Center for more info.

Your friends at Netflix
```

## 8. Legitimate Email (Not Phishing)

**Attack Type:** `NOT_PHISHING`
**Expected Confidence:** High (>90%)

```text
Subject: Team Meeting Agenda - Tuesday 10 AM

Hi Team,

Just a reminder that our weekly standup meeting is tomorrow at 10 AM.
Please come prepared with your updates and any blockers you're facing.

Agenda:
1. Operations update
2. Q1 roadmap review
3. Marketing campaign results

See you there!

Best,
Sarah
```

## 9. Legitimate Marketing Email (Not Phishing)

**Attack Type:** `NOT_PHISHING`
**Expected Confidence:** Medium/High (>70%)

```text
Subject: Your Weekly Analytics Report

Hi Lukasz,

Here is your weekly summary of activity on your account.

- Total Views: 1,234
- New Subscribers: 56
- Engagement Rate: 4.5%

You can view the full report on your dashboard:
https://analytics.example.com/reports/weekly/2024-01-15

Thanks for using our service!

The Analytics Team
123 Tech Drive, San Francisco, CA
Unsubscribe
```

---

## 10. Multi-Turn Scam Sequence (Nigerian 419)

Use these emails to test the multi-turn conversation flow. Paste each scammer response in sequence.

### Initial Email (paste first)

```text
Subject: URGENT: Inheritance Funds Transfer

Dear Beneficiary,

I am Barrister James Okonkwo, legal counsel to the late Chief Michael Williams, a British oil contractor who died in a plane crash in 2019. Before his death, he deposited $8.7 Million USD in a security company here in Lagos.

After thorough investigation, I discovered you share the same surname and country of origin. I am proposing that you stand as the next of kin so the funds can be released to you.

This is 100% legal and risk-free. You will receive 60% of the funds while I take 40% for my legal services.

Please respond with your:
- Full name
- Phone number
- Current address

I await your urgent response.

Barrister James Okonkwo, Esq.
```

### Scammer Response 1 (after first bot reply)

```text
Dear Friend,

Thank you for your quick response! I am very pleased you are interested in this opportunity.

To proceed, I need you to fill out the inheritance claim form. There is a small processing fee of $150 for the legal documentation.

Please send the payment via Western Union to:
Receiver: John Adebayo
Location: Lagos, Nigeria
Amount: $150 USD

Once payment is confirmed, I will file the claim immediately.

Contact me at +234 801 234 5678 if you have questions.

Best regards,
Barrister Okonkwo
```

**IOCs to detect:**
- Phone: `+234 801 234 5678`

### Scammer Response 2 (after second bot reply)

```text
Excellent! I have received confirmation of your payment. Thank you for your trust.

However, the security company is requiring an anti-terrorism certificate before releasing the funds. This is a new government regulation.

The certificate costs $350 and must be paid to the Nigerian Ministry of Finance.

Please send via Bitcoin to this wallet:
bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

Or wire transfer to:
Bank: First Bank Nigeria
Account: 2033456789
IBAN: NG12FBNI20334567890123

The funds ($8.7 Million) will be in your account within 48 hours after this payment!

Warm regards,
J. Okonkwo
```

**IOCs to detect:**
- BTC Wallet: `bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh`
- IBAN: `NG12FBNI20334567890123`

### Scammer Response 3 (escalation)

```text
Dear Friend,

I am happy to inform you the certificate has been approved! The funds are ready for transfer.

But there is one final step - the bank requires a "Fund Activation Fee" of $500 to unfreeze the dormant account. This is standard procedure for accounts inactive for 5+ years.

This is the LAST payment required. I give you my word as a legal professional.

Please send to our secure payment portal:
https://secure-inheritance-pay.com/activate?ref=MW2024

Or call our financial officer directly: +1-555-987-6543

Your millions are waiting!

Barrister Okonkwo
```

**IOCs to detect:**
- URL: `https://secure-inheritance-pay.com/activate?ref=MW2024`
- Phone: `+1-555-987-6543`

### Scammer Response 4 (final push)

```text
URGENT!!!

Why have you stopped responding? The funds are about to be confiscated by the government!

This is your LAST CHANCE. The Central Bank of Nigeria is closing all dormant inheritance accounts on Friday.

I have personally reduced the activation fee to just $250 as a sign of good faith.

Send IMMEDIATELY to:
PayPal: barrister.okonkwo.funds@gmail.com
Or Zelle: +1-888-555-0199

If I do not hear from you by tomorrow, the $8.7 MILLION DOLLARS will be gone forever!!!

ACT NOW!!!

J. Okonkwo
```

**IOCs to detect:**
- Phone: `+1-888-555-0199`
