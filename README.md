# Fraud-shield

**An AI fraud analyst for small online sellers who don't have a fraud team.**

Built solo for the PayPal AI Hackathon.

- **Live dashboard:** https://saumyapatil05-cloud.github.io/Fraud-shield/dashboard/
- **Demo video:** [PASTE YOUTUBE LINK]

## The problem

Small online sellers get PayPal payments all day but have no fraud team. A suspicious payment is either missed, or the seller doesn't know how risky it is or what to do about it.

## What it does

1. A payment arrives in the seller's PayPal account.
2. PayPal sends a webhook to an AWS Lambda function.
3. A rule flags payments over $500.
4. Google Gemini explains the fraud risk in plain English and recommends freeze or approve.
5. The seller gets a Telegram alert with **Freeze** and **Approve** buttons.
6. One tap records the decision. A live dashboard shows every flagged payment, its AI explanation, and its status.

Normal payments pass quietly, so the seller is only interrupted when it matters.

## Architecture

```
PayPal Sandbox ──webhook──▶ Lambda (paypal-webhook-receiver)
                              │  1. rule: amount > $500
                              │  2. Gemini explains the risk
                              │  3. save row (status: pending)
                              ▼
                          DynamoDB ◀──── Lambda (telegram-button-handler)
                              ▲                      ▲
                              │                      │ button tap
                  Lambda (dashboard-api)        Telegram alert
                              ▲                (Freeze / Approve)
                              │
                     Dashboard (GitHub Pages)
```

## How AI is used

- **Google Gemini** reads each flagged payment and writes a short, plain-English risk assessment with a recommendation. This is what turns a raw alert into something a non-expert seller can act on.
- The code tries several Gemini models in order, so a slow or unavailable model doesn't stop the alert. If every model fails, the seller still gets the alert with a note to review manually.
- **Claude (Anthropic)** was used as a coding and learning assistant while building this project.

## Tech stack

PayPal Developer Sandbox (Webhooks, Checkout) · AWS Lambda (Python 3.12) · Lambda Function URLs · Amazon DynamoDB · Amazon CloudWatch · Google Gemini API · Telegram Bot API · GitHub Pages

The Lambda code uses only the Python standard library plus `boto3`, which is built into Lambda. No packaging is needed.

## Repository layout

```
├── lambda_function.py     Webhook receiver: rule, Gemini call, save, Telegram alert
├── telegram_handler.py    Handles Freeze/Approve button taps, updates DynamoDB
├── dashboard_api.py       Returns the transactions table as JSON
├── dashboard/index.html   Live dashboard (auto-refreshes every 5 seconds)
└── checkout/index.html    Sandbox demo shop for making test payments
```

## Setup

1. **PayPal:** create a Sandbox REST app (Merchant type). Create a Personal (buyer) sandbox account in a **different country** from the seller, because India-to-India payments are blocked.
2. **DynamoDB:** create the table `fraud-guard-transactions` with partition key `id` (String), in `ap-south-1`.
3. **Lambdas:** create three Python 3.12 functions from the three `.py` files, each with a Function URL (auth NONE for the demo).
4. **Environment variables** (never commit these):
   - `paypal-webhook-receiver`: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - `telegram-button-handler`: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
5. **IAM:** give each Lambda's role a policy scoped to that one table (`PutItem`, `UpdateItem`, `Scan` as needed).
6. **Webhooks:** register the receiver's Function URL as a webhook in the PayPal app for `PAYMENT.CAPTURE.COMPLETED`. Point the Telegram bot's webhook at the button handler's URL using Telegram's `setWebhook`.
7. **Frontend:** put your `dashboard-api` URL in `dashboard/index.html` and your sandbox Client ID in `checkout/index.html`. Enable GitHub Pages from the `main` branch.

## Security notes

- Secrets live only in Lambda environment variables, never in the repo.
- The button handler only accepts taps from the owner's Telegram chat.
- IAM policies are limited to one table and only the actions needed.

## Limitations and next steps

Being honest about scope:

- **Freeze records the seller's decision but does not yet hold funds in PayPal.** The next step is calling PayPal's API to actually hold the payment.
- **Webhook signature verification is not implemented yet**, and the Function URLs are public, so this is a sandbox demo only. Verifying PayPal's webhook signature is the planned fix.
- The dashboard API is public and unauthenticated. Real use would add authentication.
- Fraud detection is currently an amount rule plus AI explanation. Planned: a velocity rule (3+ payments in 10 minutes) and richer context for the AI.

## License

MIT

Built by SAUMYA PATIL.
