# Deploying Everything on Vercel (Including Backend)

⚠️ **Warning**: This approach is **NOT recommended** for production due to Playwright limitations. See [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) for better alternatives.

## Why This Is Challenging

1. **Playwright Browser Binaries**: ~300MB, exceeds Vercel's serverless function limits
2. **Execution Time Limits**: 10s (Hobby) / 60s (Pro) may be too short for scraping
3. **Cold Starts**: Slow with large dependencies
4. **Memory Limits**: May not be enough for browser automation

## Alternative: Use a Headless Browser Service

Instead of Playwright in serverless, use:
- **Browserless.io** (paid service)
- **ScrapingBee** (paid service)
- **Puppeteer-as-a-Service** (various providers)

## If You Still Want to Try Vercel Backend

### Step 1: Convert FastAPI to Vercel Serverless Functions

Create `api/` directory in project root:

```
api/
  chat/
    index.py
  parts/
    index.py
  compatibility/
    index.py
  cart/
    index.py
```

### Step 2: Create Vercel Configuration

`vercel.json`:
```json
{
  "functions": {
    "api/**/*.py": {
      "runtime": "python3.11",
      "maxDuration": 60
    }
  },
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "/api/$1"
    }
  ]
}
```

### Step 3: Replace Playwright with HTTP Requests

Instead of Playwright, use `httpx` or `requests` for simple scraping, or integrate a headless browser service.

### Step 4: Deploy

```bash
vercel --prod
```

## Recommended: Hybrid Approach

**Best of both worlds:**

1. **Frontend**: Deploy to Vercel ✅
2. **Backend API (non-scraping)**: Vercel serverless functions ✅
3. **Scraping Service**: Separate service (Railway/Render) or use Browserless.io

This gives you:
- Fast frontend on Vercel
- Serverless API endpoints
- Dedicated scraping service for heavy operations

---

**Bottom Line**: For your use case with Playwright, **deploy backend separately** (Railway/Render) and frontend on Vercel. This is the most reliable and cost-effective approach.
