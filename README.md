<div align="center">

# 🗺️ Google Maps Business Leads Scraper

### Production-Ready Lead Generation Engine

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-1.52-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**A high-performance, stealth-enabled Google Maps scraping engine that extracts structured business data (name, address, phone, website, rating, reviews, category) from any location or search query. Built for lead generation agencies, sales teams, and market researchers.**

[Features](#-key-features) · [Quick Start](#-quick-start) · [Usage](#-usage) · [Export](#-export-formats) · [Pricing](#-service-pricing-guide)

</div>

---

## 📋 Table of Contents

- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [Usage](#-usage)
- [Export Formats](#-export-formats)
- [Configuration](#-configuration)
- [Service Pricing Guide](#-service-pricing-guide)
- [Ethical Usage](#%EF%B8%8F-ethical-usage--legal-disclaimer)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **Multi-Field Extraction** | Business name, address, phone, website, rating, review count, category, plus code |
| 🛡️ **Full Stealth Mode** | Anti-bot-detection with fingerprint spoofing, navigator overrides, and randomized behavior |
| 🧠 **Human-Like Behavior** | Random typing delays, scroll patterns, and page-interaction timing |
| 📦 **Multi-Format Export** | CSV, XLSX (auto-width columns), and JSON output with timestamps |
| 🔄 **Batch Scraping** | Feed a text file of queries — scrapes each with automatic cooldowns |
| 🔁 **Auto-Retry with Backoff** | Tenacity-powered exponential backoff on transient failures |
| 🧹 **Smart Deduplication** | Removes duplicate leads by business name + address composite key |
| 📊 **Rich CLI Dashboard** | Beautiful terminal output with progress bars, tables, and colored logs |
| ⚙️ **Fully Configurable** | All settings via `.env` — no code changes needed |
| 🌐 **Proxy Support** | Optional proxy rotation for high-volume scraping |

---

## 🛠 Tech Stack

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Core runtime |
| Playwright | 1.52.0 | Browser automation engine |
| Rich | 14.0.0 | Terminal UI, logging, tables |
| Pandas | 2.2.3 | Data manipulation & export |
| openpyxl | 3.1.5 | Excel (.xlsx) writer |
| Tenacity | 9.1.2 | Retry logic with backoff |
| fake-useragent | 2.2.0 | Randomized user-agent strings |
| python-dotenv | 1.1.0 | Environment configuration |
| aiofiles | 24.1.0 | Async file I/O |

---

## 📁 Project Structure

```
Google-Maps-Business-Leads-Scraper/
├── main.py                 # CLI entry-point with argparse + batch mode
├── scraper.py              # Core Playwright scraping engine
├── config.py               # Centralized configuration loader
├── requirements.txt        # Pinned dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git exclusions
├── LICENSE                 # MIT License
├── README.md               # This file
├── utils/
│   ├── __init__.py
│   └── helpers.py          # Logging, stealth, export, dedup utilities
└── output/                 # Generated data files (git-ignored)
    ├── leads_20260415_120000.csv
    ├── leads_20260415_120000.xlsx
    └── leads_20260415_120000.json
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** installed ([download](https://www.python.org/downloads/))
- **Git** installed

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/facingshootingstar/Google-Maps-Business-Leads-Scraper.git
cd Google-Maps-Business-Leads-Scraper

# 2. Create & activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium

# 5. Configure environment
cp .env.example .env
# Edit .env with your preferred settings
```

---

## 💻 Usage

### Single Query

```bash
# Default query from .env
python main.py

# Custom query
python main.py -q "plumbers in Chicago" -n 50

# With visible browser (debug mode)
python main.py -q "dentists in Miami" --no-headless

# Export to Excel
python main.py -q "gyms in Los Angeles" -f xlsx -n 100
```

### Batch Mode

Create a `queries.txt` file:

```text
# Lead generation queries
restaurants in New York
plumbers in Chicago
dentists in Miami
real estate agents in Dallas
```

Run batch:

```bash
python main.py --batch queries.txt -n 30 -f csv
```

### All CLI Options

```
usage: main.py [-h] [-q QUERY] [-n MAX_RESULTS] [-f {csv,xlsx,json}]
               [--batch BATCH] [--no-headless] [--no-dedup]

Options:
  -q, --query         Search query (default from .env)
  -n, --max-results   Max number of results to scrape
  -f, --format        Export format: csv, xlsx, json
  --batch             Path to text file with queries (one per line)
  --no-headless       Run browser in visible mode
  --no-dedup          Skip deduplication of results
```

---

## 📤 Export Formats

All exports are saved to the `output/` directory with timestamps.

### CSV Output

```csv
business_name,address,phone,website,rating,reviews_count,category,plus_code,google_maps_url
Joe's Pizza,7 Carmine St New York,+1 212-366-1182,joespizzanyc.com,4.5,12847,Pizza restaurant,,https://...
```

### XLSX Output

- Auto-sized columns
- Ready for client delivery
- Compatible with Excel, Google Sheets, Airtable

### JSON Output

```json
[
  {
    "business_name": "Joe's Pizza",
    "address": "7 Carmine St, New York, NY 10014",
    "phone": "+1 212-366-1182",
    "website": "joespizzanyc.com",
    "rating": 4.5,
    "reviews_count": 12847,
    "category": "Pizza restaurant",
    "plus_code": "",
    "google_maps_url": "https://www.google.com/maps/place/..."
  }
]
```

---

## ⚙️ Configuration

All settings are managed via the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_QUERY` | `restaurants in New York` | Default search query |
| `MAX_RESULTS` | `100` | Maximum listings to scrape |
| `HEADLESS` | `true` | Run browser without GUI |
| `SLOW_MO` | `50` | Playwright slow-motion delay (ms) |
| `BROWSER_TIMEOUT` | `60000` | Page load timeout (ms) |
| `USE_STEALTH` | `true` | Enable anti-detection scripts |
| `RANDOM_DELAY_MIN` | `1.5` | Min random delay (seconds) |
| `RANDOM_DELAY_MAX` | `4.0` | Max random delay (seconds) |
| `EXPORT_FORMAT` | `csv` | Default export: csv, xlsx, json |
| `OUTPUT_DIR` | `output` | Export destination folder |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `PROXY_SERVER` | *(none)* | Optional HTTP proxy URL |

---

## 💰 Service Pricing Guide

This tool can be packaged and sold as a **fixed-price lead generation service**:

### Pricing Tiers

| Tier | Deliverable | Price Range |
|------|-------------|-------------|
| 🥉 **Starter** | 500 leads, 1 city, CSV export | **$800 – $1,000** |
| 🥈 **Professional** | 2,000 leads, 5 cities, XLSX + dedup | **$1,200 – $1,800** |
| 🥇 **Enterprise** | 5,000+ leads, unlimited cities, JSON API + ongoing | **$2,000 – $2,500** |

### How to Sell

1. **Identify clients**: Local marketing agencies, real estate firms, B2B sales teams, franchise consultants
2. **Offer on platforms**: Fiverr, Upwork, LinkedIn, or direct cold outreach
3. **Sample pitch**: *"I'll deliver 1,000+ verified business leads from Google Maps for your target market — name, phone, website, rating — in a clean spreadsheet, within 48 hours."*
4. **Upsell ideas**:
   - Monthly lead refresh subscriptions ($300–$500/mo)
   - Data enrichment (email, social profiles) as add-on
   - CRM-ready formatting (HubSpot, Salesforce import)
   - Competitive analysis reports

### Delivery Workflow

```
Client Request → Configure .env → Run Scraper → QA + Dedup → Deliver XLSX
        ↓                                                         ↓
   Define scope                                           Invoice & follow-up
```

---

## ⚖️ Ethical Usage & Legal Disclaimer

> **⚠️ IMPORTANT: Use this tool responsibly and ethically.**

- This tool is provided for **educational and research purposes**.
- **Respect Google's Terms of Service.** Automated scraping may violate Google's ToS. Use at your own risk.
- **Comply with local laws**, including GDPR, CCPA, and other data privacy regulations.
- **Do not use** extracted data for spamming, harassment, or any unlawful activity.
- **Rate-limit your requests** to avoid overloading servers. The built-in delays are designed for this.
- **Obtain consent** before using personal data for marketing or outreach.
- The authors assume **no liability** for misuse of this software.

By using this tool, you agree to use it in compliance with all applicable laws and regulations.

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.

---

<div align="center">

**Built with ❤️ by [facingshootingstar](https://github.com/facingshootingstar)**

⭐ Star this repo if it helped you generate leads!

</div>
