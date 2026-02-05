# Polar Weekly Training Report System

An automated system that fetches your Polar fitness data via the Polar Accesslink API and generates comprehensive weekly email reports every Monday morning.

## Features

### Weekly Training Report
- **Training Volume Tracking**: Sessions, duration, distance, calories by sport
- **Heart Rate Zone Analysis**: Time in each zone with percentage distribution
- **Recovery Metrics**: Nightly Recharge, ANS Charge, HRV trends
- **Sleep Quality**: Duration, scores, stage breakdown (Deep/Light/REM)
- **Week-over-Week Comparisons**: Percentage changes for all metrics
- **Smart Highlights**: Achievements and concerns automatically identified
- **Beautiful HTML Reports**: Mobile-responsive email design

### Weekly Health Digest (Advanced Analytics)
- **ACWR (Acute:Chronic Workload Ratio)**: Detect injury risk (0.8-1.3 optimal)
- **Training Monotony & Strain**: Assess overtraining risk from load variation
- **HRV Trend Analysis**: Quadrant analysis (Coping Well, Adapting, Fatigued, Maladaptation)
- **Aerobic Decoupling**: Measure aerobic fitness through pace:HR drift
- **Sleep Architecture**: Deep/REM/Light percentages with deficit tracking
- **Sleep Debt Tracker**: Accumulated sleep deficit with recovery timeline
- **Early Warning System**: Detect illness/overtraining 24-48h before symptoms
- **Weather-Performance Correlation**: Find optimal training conditions
- **Time-of-Day Optimization**: Identify personal peak performance windows
- **Performance Management Chart (CTL/ATL/TSB)**: Track fitness, fatigue, and form

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd Polaremail

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Beginner-Friendly Setup (Non-Technical Guide)

If you are not technical, follow these steps carefully and copy/paste the commands exactly as shown.

### What You Need
- A Polar account with your training data
- A Gmail, Outlook, or other email account to send reports
- 15-20 minutes of uninterrupted time

### Step 1: Install Python
1. Go to https://www.python.org/downloads/ and install **Python 3.10+**
2. During installation on Windows, check **"Add Python to PATH"**
3. Restart your computer if the installer asks

### Step 2: Download the Project
1. Open the repository page in your browser
2. Click the green **Code** button → **Download ZIP**
3. Unzip the file somewhere easy (e.g., Desktop)

### Step 3: Open a Terminal
- **Windows**: Open **Command Prompt** or **PowerShell**
- **Mac**: Open **Terminal** (Applications → Utilities)

### Step 4: Install the App
Replace `PATH_TO_FOLDER` with the folder you unzipped, and `PROJECT_FOLDER_NAME` with the extracted folder name (it often ends with `-main`).

```bash
cd PATH_TO_FOLDER/PROJECT_FOLDER_NAME
python -m venv venv
```

Activate the virtual environment:
- **Windows**: `venv\Scripts\activate`
- **Mac/Linux**: `source venv/bin/activate`

Install the app:
```bash
pip install -r requirements.txt
```

### Step 5: Fill In Your Settings
Copy the example settings file:

```bash
cp .env.example .env  # Mac/Linux
```
```bash
copy .env.example .env  # Windows
```

Open the `.env` file with Notepad/TextEdit and fill in:
- **POLAR_CLIENT_ID** and **POLAR_CLIENT_SECRET** from https://admin.polaraccesslink.com
- **EMAIL_USERNAME**, **EMAIL_PASSWORD**, **EMAIL_RECIPIENT**
- **REPORT_DAY**, **REPORT_TIME**, **TIMEZONE** (optional)

### Step 6: Connect Your Polar Account
```bash
python -m polar_report auth
```
This command starts a small local server and does not open a browser automatically. Open http://localhost:5000/auth in your browser and log in to Polar when asked.

### Step 7: Sync Your Data and Send a Test
```bash
python -m polar_report sync
python -m polar_report report --send
```

### Step 8: Keep It Running Every Week
```bash
python -m polar_report schedule
```

Keep this window open for weekly reports. If you close it, reports stop.
For automatic startup, consider using your system scheduler (Windows Task Scheduler or macOS/Linux cron).

### 2. Configuration

Copy the example environment file and configure:

```bash
# Linux/Mac
cp .env.example .env

# Windows (Command Prompt or PowerShell)
copy .env.example .env
```

Edit `.env` with your settings:

```env
# Get from https://admin.polaraccesslink.com
POLAR_CLIENT_ID=your_client_id
POLAR_CLIENT_SECRET=your_client_secret

# Email settings (Gmail example)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your_email@gmail.com
EMAIL_PASSWORD=your_app_password  # Use App Password, not regular password
EMAIL_RECIPIENT=your_email@gmail.com

# Schedule (default: Monday 8:00 AM Brussels time)
REPORT_DAY=Monday
REPORT_TIME=08:00
TIMEZONE=Europe/Brussels
```

### 3. Authenticate with Polar

```bash
# Start the authentication server
python -m polar_report auth

# Open http://localhost:5000/auth in your browser
# Log in with your Polar account and authorize
```

### 4. Sync Your Data

```bash
# Sync existing data from Polar API
python -m polar_report sync
```

### 5. Generate a Test Report

```bash
# Generate and save report locally
python -m polar_report report --save

# Generate and send via email
python -m polar_report report --send
```

### 6. Start the Scheduler

```bash
# Run scheduled weekly reports
python -m polar_report schedule
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Polar Cloud                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Exercises   │  │    Sleep     │  │   Recharge   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
    ┌─────────────────────────────────────────────────┐
    │              Webhook Listener                    │
    │           (Flask on port 5000)                   │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              SQLite Database                     │
    │  ┌──────────┬──────────┬──────────┬──────────┐  │
    │  │exercises │  sleep   │ recharge │ webhook  │  │
    │  │          │          │          │  events  │  │
    │  └──────────┴──────────┴──────────┴──────────┘  │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │           Weekly Report Generator                │
    │  ┌──────────────────────────────────────────┐   │
    │  │  Aggregator → Template → Email Sender    │   │
    │  └──────────────────────────────────────────┘   │
    └─────────────────────┬───────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────┐
    │              Your Email Inbox                    │
    │       📧 Weekly Training Report                  │
    └─────────────────────────────────────────────────┘
```

## CLI Commands

```bash
# Authentication
python -m polar_report auth              # Start OAuth flow
python -m polar_report auth --port 8080  # Use different port

# Webhook
python -m polar_report webhook           # Run webhook listener
python -m polar_report setup-webhook     # Register webhook with Polar
python -m polar_report setup-webhook --status  # Check webhook status

# Data
python -m polar_report sync              # Sync from Polar API
python -m polar_report status            # Show system status

# Reports
python -m polar_report report            # Generate report
python -m polar_report report --save     # Save HTML to file
python -m polar_report report --send     # Send via email
python -m polar_report report --week 2025-01-06  # Specific week

# Health Digest (Advanced Analytics)
python -m polar_report digest            # Generate health digest
python -m polar_report digest --save     # Save HTML to file
python -m polar_report digest --send     # Send via email
python -m polar_report digest --week 2025-01-06  # Specific week

# Scheduling
python -m polar_report schedule          # Start scheduler
python -m polar_report schedule --next   # Show next report time
python -m polar_report schedule --run-now  # Run immediately

# Email
python -m polar_report test-email        # Send test email
python -m polar_report test-email --test-connection  # Test SMTP
```

## Webhook Setup

For real-time data updates, set up webhooks:

### Using ngrok (for local development)

```bash
# Install ngrok: https://ngrok.com/download
ngrok http 5000

# Copy the https URL (e.g., https://abc123.ngrok.io)
# Add to .env:
WEBHOOK_URL=https://abc123.ngrok.io/webhook
WEBHOOK_SECRET=your_secure_random_string

# Register with Polar
python -m polar_report setup-webhook

# Start webhook listener
python -m polar_report webhook
```

### Production Deployment

For production, deploy the webhook listener to a server with HTTPS:

```bash
# Using gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 polar_report.webhook:app
```

## Email Setup

### Gmail

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: https://support.google.com/accounts/answer/185833
3. Use the App Password in `EMAIL_PASSWORD`

### Other Providers

Update `EMAIL_SMTP_SERVER` and `EMAIL_SMTP_PORT`:

| Provider | Server | Port |
|----------|--------|------|
| Gmail | smtp.gmail.com | 587 |
| Outlook | smtp-mail.outlook.com | 587 |
| Yahoo | smtp.mail.yahoo.com | 587 |

## Project Structure

```
Polaremail/
├── polar_report/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── config.py        # Configuration management
│   ├── models.py        # Database models
│   ├── auth.py          # OAuth2 authentication
│   ├── polar_api.py     # Polar API client
│   ├── webhook.py       # Flask webhook listener
│   ├── aggregator.py    # Data aggregation
│   ├── report.py        # Report generation
│   ├── health_digest.py # Health Digest calculations
│   ├── health_digest_report.py  # Health Digest report
│   ├── chart_generator.py  # Chart generation (QuickChart.io)
│   ├── weather_api.py   # OpenWeatherMap integration
│   ├── email_sender.py  # Email delivery
│   └── scheduler.py     # Scheduled jobs
├── templates/
│   ├── email_report.html  # Email template
│   └── email_health_digest.html  # Health Digest template
├── reports/             # Generated HTML reports
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Metrics Explained

### Health Digest Metrics

#### ACWR (Acute:Chronic Workload Ratio)
- **< 0.8**: Undertrained - risk of detraining
- **0.8-1.3**: Optimal training zone
- **1.3-1.5**: Caution - elevated injury risk
- **> 1.5**: Danger zone - high injury risk

#### Training Monotony
- **< 1.5**: Good variation in training
- **1.5-2.0**: Elevated risk - add more variety
- **> 2.0**: High illness/injury risk

#### HRV Quadrant Analysis
- **Coping Well**: High HRV + Low CV - optimal recovery
- **Adapting**: High HRV + High CV - responding to training
- **Fatigued**: Low HRV + High CV - needs recovery
- **Maladaptation**: Low HRV + Low CV - chronic stress warning

#### Performance Management (CTL/ATL/TSB)
- **CTL (Fitness)**: 42-day exponential moving average of training load
- **ATL (Fatigue)**: 7-day exponential moving average of training load
- **TSB (Form)**: CTL - ATL (race readiness: +10 to +25)

### Training Load
- **Cardio Load**: Cardiovascular stress from training
- **Muscle Load**: Muscular stress from training

### Nightly Recharge (1-5 scale)
- 5: Very Good - Well recovered
- 4: Good - Recovered
- 3: Compromised - Partially recovered
- 2: Poor - Not well recovered
- 1: Very Poor - Poorly recovered

### Heart Rate Zones
- Zone 1: Recovery (50-60% max HR)
- Zone 2: Light (60-70% max HR)
- Zone 3: Moderate (70-80% max HR)
- Zone 4: Hard (80-90% max HR)
- Zone 5: Maximum (90-100% max HR)

## Troubleshooting

### "No access token configured"

Run the authentication flow:
```bash
python -m polar_report auth
```

### "Failed to send email"

1. Check SMTP credentials in `.env`
2. For Gmail, ensure you're using an App Password
3. Test connection: `python -m polar_report test-email --test-connection`

### "No data in report"

1. Sync data first: `python -m polar_report sync`
2. Check data exists: `python -m polar_report status`
3. Ensure workouts are synced to Polar Flow

### Webhook not receiving data

1. Verify webhook URL is accessible from internet
2. Check webhook registration: `python -m polar_report setup-webhook --status`
3. Review webhook listener logs

## Development

```bash
# Run tests
pytest

# Run with debug logging
python -m polar_report -v status
```

## API Reference

- [Polar Accesslink API Documentation](https://www.polar.com/accesslink-api/)
- [Register Application](https://admin.polaraccesslink.com)
- [API Support](mailto:b2bhelpdesk@polar.com)

## License

MIT License - See LICENSE file for details.
