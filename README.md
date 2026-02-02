# PartSelect Chat Agent

**AI-powered chat assistant for PartSelect refrigerator and dishwasher parts**

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15.5-black.svg)](https://nextjs.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)



---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Supabase account
- OpenAI API key

### Setup

```bash
# 1. Clone and navigate
cd /path/to/case-study-main

# 2. Backend setup
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials

# 3. Run database migrations (in Supabase SQL Editor)
# - 001_initial_schema.sql
# - 002_seed_catalog.sql
# - 003_troubleshooting_symptoms.sql

# 4. Load seed data
python seed/load_seed_catalog.py

# 5. Start backend
uvicorn main:app --reload --port 8000

# 6. Start frontend (new terminal)
cd ..
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

**Visit:** http://localhost:3000

---

## ✨ Key Features

### Natural Language Understanding
No appliance selection required. Just start typing:

```
"The ice maker on my Whirlpool fridge is not working"
→ Auto-detects: refrigerator, Whirlpool, ice maker, symptom
→ Shows relevant parts from database
```

### Symptom-Based Recommendations
Database-driven part suggestions based on manufacturer's troubleshooting data:

```
User: "dishwasher not drying dishes"
→ Searches symptom database
→ Returns: Heating Element, Vent Assembly, etc.
```

### Dynamic Installation Instructions 
Real-time scraping of PartSelect pages + OpenAI summarization:

```
User: "How can I install part number PS11752778?"
→ Scrapes product page with Playwright
→ Extracts: description, instructions, safety, tools
→ OpenAI summarizes into clear steps
→ Returns: Formatted installation guide
```

### Dynamic Compatibility Checking 
Real-time scraping + OpenAI-powered compatibility verification:

```
User: "Is this part compatible with my WDT780SAEM1 model?"
→ Scrapes "replaces these" part numbers
→ Extracts "works with" appliance types
→ OpenAI intelligently matches model with data
→ Returns: Compatible / Not Compatible / Unknown (with reasoning)
```

### Intelligent Troubleshooting
Branching decision trees that lead to specific part recommendations:

```
Q1: Is water reaching the ice maker?
  ├─ No → Check filter age → Recommend water filter
  └─ Yes → Check for noise → Recommend ice maker assembly
```

### Live Data Scraping
UI-triggered price/stock updates from product pages using Playwright.

### E-commerce Integration
Shopping cart, compatibility checks, installation guidance.

---

## 🏗️ Architecture

```
Next.js Frontend (TypeScript + Tailwind)
        ↕ REST API
Python FastAPI Backend (Agent Orchestrator)
        ↕
┌───────────────┬──────────────┬───────────────┐
│ Supabase      │ OpenAI API   │ PartSelect    │
│ (PostgreSQL)  │ (GPT-4)      │ (Web Scraping)│
└───────────────┴──────────────┴───────────────┘
```

---

## 📊 Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS, Zustand |
| **Backend** | Python 3.11, FastAPI, Pydantic |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **LLM** | OpenAI GPT-4 |
| **Scraping** | Playwright, BeautifulSoup4 |
| **Deployment** | Docker, Docker Compose |

---

---

## 🎯 Solution Overview

### For Users
- **Find parts** by description, part number, or symptom
- **Check compatibility** with appliance models
- **Troubleshoot issues** with interactive Q&A
- **View installation** guidance and videos
- **Add to cart** and checkout
- **Zero-click onboarding** - No appliance selection required, auto-detects from natural language

### Implementation Highlights
- **Natural language parsing** - Robust regex entity extraction with LLM fallback
- **Symptom-to-part mapping** - Database-driven recommendations from scraped data
- **Agentic architecture** - Modular sub-agent pattern with intent classification
- **Live web scraping** - On-demand price/stock updates using Playwright
- **Context-aware** - Conversation history lookup for missing entities
- **Production-ready** - Docker, error handling, rate limiting, graceful degradation

---

## 🔧 Core Capabilities

### 1. Entity Extraction (Regex-Based)

| Entity | Pattern | Example |
|--------|---------|---------|
| PartSelect # | `\bPS(\d{6,9})\b` | PS11701542 |
| Model # | `\b([A-Z0-9]{5,15})\b` | WRS325SDHZ00 |
| Appliance | Keywords + context | refrigerator, dishwasher |
| Brand | `\b(whirlpool\|ge\|...)\b` | Whirlpool, GE, Samsung |
| Symptom | 9 symptom patterns | not making ice, leaking |

### 2. Symptom Database

**Scraped from product pages:**
```json
{
  "partselect_number": "PS8260087",
  "troubleshooting_symptoms": [
    "Not drying dishes properly",
    "Not cleaning dishes properly",
    "Will Not Start"
  ]
}
```

**Reverse index for fast lookup:**
```sql
SELECT * FROM part_symptoms 
WHERE symptom ILIKE '%not drying%'
  AND appliance_type = 'dishwasher';
```

### 3. Branching Troubleshooting

Different outcomes based on user answers:
- Ice maker flow → 3 steps → Water filter or ice maker assembly
- Cooling flow → 2 steps → Professional service or DIY fix
- Drain flow → 3 steps → Pump or filter

---

## 🧪 Testing

### Example Inquiries (Case Study Requirements)

These are the three example inquiries from the case study requirements:

| Query | Expected Behavior |
|-------|-------------------|
| **"How can I install part number PS11752778?"** | ✅ Scrapes installation instructions, shows InstallStepsCard with summary, difficulty, tools, and collapsible steps |
| **"Is this part compatible with my WDT780SAEM1 model?"** | ✅ Model page scraping verification, returns CompatibilityCard with confidence level and evidence |
| **"The ice maker on my Whirlpool fridge is not working. How can I fix it?"** | ✅ Auto-detects appliance/brand/symptom, shows symptom-based parts, offers troubleshooting flow |

### Additional Test Queries

| Query | Expected Behavior |
|-------|-------------------|
| "The ice maker is not making ice" | ✅ Shows 3-5 parts from symptom database |
| "My dishwasher is not draining" | ✅ Shows drain pump, filter parts |
| "PS11701542" | ✅ Direct part lookup with details |
| "Is PS11701542 compatible with WRS325SDHZ00?" | ✅ Compatibility check |
| "Can you help with my washing machine?" | ✅ Out-of-scope rejection with helpful message |

### Watch Backend Terminal

```
🔍 Detected appliance: refrigerator
🔍 Detected brand: Whirlpool
🔍 Detected symptoms: not making ice
✅ Updated session with appliance type: refrigerator

🔍 Using database symptom search for: ['not making ice']
🔍 Searching parts by symptom: 'not making ice'
   ✅ Found 3 parts matching symptom
```

---

## 🐳 Docker Deployment

### Production
```bash
docker-compose up -d
docker-compose exec backend python seed/load_seed_catalog.py
```

### Development (with hot-reload)
```bash
docker-compose -f docker-compose.dev.yml up
docker-compose exec backend python seed/load_seed_catalog.py
```

---

## 📦 Optional: Web Scraping

Enrich your catalog with live data from PartSelect:

```bash
# Install Playwright
pip install playwright
playwright install chromium

# Scrape troubleshooting symptoms, price, stock
python backend/scraper/comprehensive_scraper.py \
    --input backend/seed/seed_parts.json \
    --output backend/seed/seed_parts_enriched.json \
    --headless

# Load enriched data
mv backend/seed/seed_parts_enriched.json backend/seed/seed_parts.json
python backend/seed/load_seed_catalog.py
```

**Extracts:**
- Troubleshooting symptoms ("This part fixes the following symptoms:")
- Price & stock status
- Manufactured by line
- Image URLs

---


---

## 🎯 Quick Navigation

1. **New here?** Start with [Quick Start](#-quick-start) above
2. **Want architecture details?** Read [DESIGN.md](./DESIGN.md) for comprehensive system design
3. **Need setup help?** Check [RUN_GUIDE.md](./RUN_GUIDE.md) for detailed instructions
4. **Ready to deploy?** See [FREE_DEPLOYMENT.md](./FREE_DEPLOYMENT.md) for deployment guides



This implementation demonstrates:
- ✅ **Extensible architecture** - Modular sub-agent pattern for easy extension
- ✅ **Scalable design** - Database-driven with caching and rate limiting
- ✅ **User-focused UX** - Zero-click onboarding, context-aware responses
- ✅ **Production-ready** - Error handling, graceful degradation, comprehensive documentation

