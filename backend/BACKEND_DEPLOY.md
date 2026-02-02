# Backend Deployment Guide

This guide covers deploying the Python FastAPI backend to various platforms.

## Prerequisites

- Python 3.11+
- Supabase account and credentials
- OpenAI API key
- Git repository (GitHub/GitLab/Bitbucket)

## Required Environment Variables

Before deploying, ensure you have these environment variables:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
OPENAI_API_KEY=sk-...
ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app
```

## Option 1: Railway (Recommended - Easiest)

Railway auto-detects Python and handles most configuration automatically.

### Steps:

1. **Sign up**: Go to [railway.app](https://railway.app) and sign up with GitHub

2. **Create New Project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository
   - Railway will auto-detect it's a Python project

3. **Configure Service**:
   - Railway will create a service automatically
   - Click on the service to configure

4. **Set Root Directory**:
   - Go to Settings → Root Directory
   - Set to: `backend`

5. **Add Environment Variables**:
   - Go to Variables tab
   - Add all required variables (see above)
   - For `ALLOWED_ORIGINS`, include:
     - `http://localhost:3000` (for local dev)
     - `https://your-frontend.vercel.app` (your Vercel URL)
     - `https://*.vercel.app` (for preview deployments)

6. **Set Start Command** (if needed):
   - Go to Settings → Deploy
   - Start Command: `python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
   - **OR** Railway will auto-detect `Procfile` if present in `backend/` directory
   - **See [FIX_RAILWAY_PORT.md](../FIX_RAILWAY_PORT.md) if you get "$PORT is not a valid integer" errors**

7. **Deploy**:
   - Railway will automatically deploy on every push to your main branch
   - Check the Deployments tab for logs
   - Once deployed, note your Railway URL (e.g., `https://your-app.railway.app`)

8. **Get Your Backend URL**:
   - Railway provides a public URL automatically
   - Go to Settings → Networking → Public Domain
   - Copy this URL (e.g., `https://your-app-name.up.railway.app`)
   - Use this as your `NEXT_PUBLIC_API_URL` in Vercel
   - **See [RAILWAY_URL_GUIDE.md](../RAILWAY_URL_GUIDE.md) for detailed instructions**

### Railway Pricing:
- **Free Tier**: $5 credit/month (enough for small projects)
- **Hobby**: $5/month for 500 hours
- Auto-scales based on usage

---

## Option 2: Render

Render offers a free tier with automatic deployments.

### Steps:

1. **Sign up**: Go to [render.com](https://render.com) and sign up

2. **Create New Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your repository

3. **Configure Service**:
   - **Name**: `partselect-backend` (or your choice)
   - **Environment**: `Docker` (important: use Docker instead of Python 3)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile` (or leave empty if Dockerfile is in backend/)
   - **Start Command**: (leave empty, handled by Dockerfile CMD)
   
   **OR if using Python 3 environment:**
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Note**: Skip `playwright install-deps` as it causes issues - dependencies are handled differently

4. **Add Environment Variables**:
   - Scroll to "Environment Variables"
   - Add all required variables
   - For `ALLOWED_ORIGINS`, use comma-separated values:
     ```
     http://localhost:3000,https://your-frontend.vercel.app
     ```

5. **Deploy**:
   - Click "Create Web Service"
   - Render will build and deploy automatically
   - Check logs for any errors
   - Once deployed, your URL will be: `https://your-app.onrender.com`

### Render Pricing:
- **Free Tier**: Spins down after 15 minutes of inactivity (wakes up on request)
- **Starter**: $7/month for always-on service

**Note**: Free tier has cold starts (30-60s first request after inactivity)

---

## Option 3: Fly.io

Fly.io offers global deployment with Docker.

### Steps:

1. **Install Fly CLI**:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**:
   ```bash
   fly auth login
   ```

3. **Navigate to backend directory**:
   ```bash
   cd backend
   ```

4. **Initialize Fly app**:
   ```bash
   fly launch
   ```
   - Follow prompts
   - Choose app name
   - Select region
   - Don't deploy yet (we'll configure first)

5. **Configure `fly.toml`** (created automatically):
   ```toml
   app = "your-app-name"
   primary_region = "iad"  # or your preferred region

   [build]
     dockerfile = "Dockerfile"

   [env]
     PORT = "8000"

   [[services]]
     internal_port = 8000
     protocol = "tcp"
     
     [[services.ports]]
       port = 80
       handlers = ["http"]
       force_https = true
     
     [[services.ports]]
       port = 443
       handlers = ["tls", "http"]

   [[services.http_checks]]
     interval = "10s"
     timeout = "2s"
     grace_period = "5s"
     method = "GET"
     path = "/health"
   ```

6. **Set Secrets**:
   ```bash
   fly secrets set SUPABASE_URL=your_url
   fly secrets set SUPABASE_KEY=your_key
   fly secrets set OPENAI_API_KEY=your_key
   fly secrets set ALLOWED_ORIGINS="http://localhost:3000,https://your-frontend.vercel.app"
   ```

7. **Deploy**:
   ```bash
   fly deploy
   ```

8. **Get URL**:
   ```bash
   fly status
   ```
   Your app will be at: `https://your-app-name.fly.dev`

### Fly.io Pricing:
- **Free Tier**: 3 shared-cpu VMs, 3GB persistent volumes
- **Paid**: Starts at $1.94/month per VM

---

## Option 4: Docker + Any Platform

The backend includes a Dockerfile for containerized deployment.

### Build and Test Locally:

```bash
cd backend
docker build -t partselect-backend .
docker run -p 8000:8000 \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  -e ALLOWED_ORIGINS="http://localhost:3000" \
  partselect-backend
```

### Deploy to Platforms Supporting Docker:

- **DigitalOcean App Platform**: Connect repo, auto-detects Dockerfile
- **Google Cloud Run**: `gcloud run deploy`
- **AWS ECS/Fargate**: Use Dockerfile in ECS task definition
- **Azure Container Instances**: Deploy Docker container
- **Heroku**: Use Container Registry

---

## Verifying Backend Deployment

Once deployed, verify your backend is running:

1. **Health Check**:
   ```bash
   curl https://your-backend-url.com/health
   ```
   Should return:
   ```json
   {
     "status": "healthy",
     "database": "connected",
     "environment": "production"
   }
   ```

2. **Root Endpoint**:
   ```bash
   curl https://your-backend-url.com/
   ```
   Should return:
   ```json
   {
     "status": "healthy",
     "service": "PartSelect Chat Agent API",
     "version": "1.0.0"
   }
   ```

3. **Test API Endpoint**:
   ```bash
   curl -X POST https://your-backend-url.com/api/chat \
     -H "Content-Type: application/json" \
     -d '{"session_id":"test","message":"hello"}'
   ```

---

## Updating CORS Configuration

After deploying, update your backend's CORS to allow your Vercel frontend:

### Method 1: Environment Variable (Recommended)

Set `ALLOWED_ORIGINS` in your platform's environment variables:
```
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app,https://*.vercel.app
```

Then update `backend/config.py` to read from environment:
```python
import os
allowed_origins: List[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"
).split(",")
```

### Method 2: Direct Code Update

Edit `backend/config.py`:
```python
allowed_origins: List[str] = [
    "http://localhost:3000",
    "https://your-app.vercel.app",
    # Add more as needed
]
```

Then redeploy.

---

## Troubleshooting

### Backend Won't Start

**Error: "Module not found"**
- Check `requirements.txt` includes all dependencies
- Verify build command installs dependencies
- Check build logs for missing packages

**Error: "Port already in use"**
- Ensure using `$PORT` environment variable (platform-provided)
- Check start command uses `--port $PORT`

**Error: "Database connection failed"**
- Verify `SUPABASE_URL` and `SUPABASE_KEY` are correct
- Check Supabase project is active
- Verify network connectivity

### CORS Errors

**Error: "Access-Control-Allow-Origin"**
- Add your frontend URL to `ALLOWED_ORIGINS`
- Include protocol (`https://` not just domain)
- Redeploy after updating CORS

### Playwright Issues

**Error: "Playwright browsers not installed"**
- Add to build command: `playwright install chromium && playwright install-deps`
- Some platforms may need additional system dependencies

---

## Monitoring and Logs

### Railway:
- View logs in Deployments tab
- Set up alerts in Settings → Notifications

### Render:
- View logs in Logs tab
- Set up email alerts in Settings

### Fly.io:
```bash
fly logs  # View real-time logs
fly status  # Check app status
```

---

## Next Steps

After backend is deployed:

1. **Update Frontend**: Set `NEXT_PUBLIC_API_URL` in Vercel to your backend URL
2. **Test Integration**: Verify frontend can communicate with backend
3. **Monitor**: Set up error tracking (Sentry, etc.)
4. **Scale**: Adjust resources based on usage

---

**Need Help?**
- [Railway Docs](https://docs.railway.app)
- [Render Docs](https://render.com/docs)
- [Fly.io Docs](https://fly.io/docs)
