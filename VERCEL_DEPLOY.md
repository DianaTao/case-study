# Deploying to Vercel

This guide covers deploying the PartSelect Chat Agent to Vercel.

## ⚠️ Important: Backend Deployment

**Can you deploy the backend on Vercel?** 

**Short answer**: Technically yes, but **NOT recommended** for this project.

**Why?**
- Your backend uses **Playwright** for web scraping, which requires large browser binaries (~300MB)
- Vercel serverless functions have size and execution time limits
- Playwright doesn't work well in serverless environments

**Recommended Approach**:
- ✅ **Frontend**: Deploy to Vercel (perfect fit)
- ✅ **Backend**: Deploy separately to Railway/Render/Fly.io (see [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md))

If you want to try deploying backend on Vercel anyway, see [VERCEL_FULL_DEPLOY.md](./VERCEL_FULL_DEPLOY.md) (not recommended).

---

## 🚀 Quick Start

1. **Deploy Backend** (Railway/Render/Fly.io) → Get backend URL
2. **Deploy Frontend** (Vercel) → Connect repo → Add env vars → Deploy
3. **Update Backend CORS** → Add Vercel domain to allowed origins

**Total time**: ~15-20 minutes

---

## Architecture Overview

This application consists of:
- **Frontend**: Next.js 15 (deploys to Vercel) ✅
- **Backend**: Python FastAPI (deploy separately - see options below) ⚠️

## Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **GitHub/GitLab/Bitbucket**: Connect your repository
3. **Backend Deployment**: Choose a platform for the Python backend (see options below)

## Step 1: Deploy Backend (Required First)

**📖 For detailed backend deployment instructions, see [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md)**

The Python FastAPI backend must be deployed separately. Quick start options:

### Option A: Railway (Recommended)

1. Sign up at [railway.app](https://railway.app)
2. Create new project → "Deploy from GitHub repo"
3. Select your repository
4. Add environment variables:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   OPENAI_API_KEY=your_openai_key
   ```
5. Railway will auto-detect Python and install dependencies
6. Set the start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Note the deployed URL (e.g., `https://your-app.railway.app`)

### Option B: Render

1. Sign up at [render.com](https://render.com)
2. Create new "Web Service"
3. Connect your GitHub repo
4. Settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3
5. Add environment variables
6. Deploy and note the URL

### Option C: Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. In `backend/` directory, create `fly.toml`:
   ```toml
   app = "your-app-name"
   primary_region = "iad"

   [build]
     builder = "paketobuildpacks/builder:base"

   [[services]]
     internal_port = 8000
     protocol = "tcp"
   ```
3. Run: `fly launch` and follow prompts
4. Add secrets: `fly secrets set SUPABASE_URL=... OPENAI_API_KEY=...`
5. Deploy: `fly deploy`

### Option D: Keep Backend Local (Development Only)

For local development, run backend locally and use `http://localhost:8000` in frontend.

## Step 2: Deploy Frontend to Vercel

### Method 1: Vercel CLI (Recommended)

1. **Install Vercel CLI**:
   ```bash
   npm i -g vercel
   ```

2. **Login to Vercel**:
   ```bash
   vercel login
   ```

3. **Navigate to project root**:
   ```bash
   cd /path/to/case-study-main
   ```

4. **Deploy**:
   ```bash
   vercel
   ```
   - Follow prompts (use defaults for most)
   - When asked about environment variables, you can add them now or later

5. **Add Environment Variables**:
   ```bash
   vercel env add NEXT_PUBLIC_SUPABASE_URL
   vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
   vercel env add NEXT_PUBLIC_API_URL
   ```
   - For `NEXT_PUBLIC_API_URL`, use your backend URL (e.g., `https://your-app.railway.app`)

6. **Deploy to Production**:
   ```bash
   vercel --prod
   ```

### Method 2: Vercel Dashboard (Git Integration)

1. **Go to [vercel.com/new](https://vercel.com/new)**

2. **Import your Git repository**:
   - Connect GitHub/GitLab/Bitbucket
   - Select your repository
   - Click "Import"

3. **Configure Project**:
   - **Framework Preset**: Next.js (auto-detected)
   - **Root Directory**: `./` (project root)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `.next` (default)
   - **Install Command**: `npm install` (default)

4. **Add Environment Variables**:
   Click "Environment Variables" and add:
   ```
   NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
   NEXT_PUBLIC_API_URL=https://your-backend-url.com
   ```

5. **Deploy**:
   - Click "Deploy"
   - Wait for build to complete
   - Your app will be live at `https://your-app.vercel.app`

## Step 3: Configure Environment Variables

### Required Environment Variables

Add these in Vercel Dashboard → Project → Settings → Environment Variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGc...` |
| `NEXT_PUBLIC_API_URL` | Backend API URL | `https://your-app.railway.app` |

### Setting Environment Variables

**Via Vercel Dashboard**:
1. Go to your project → Settings → Environment Variables
2. Add each variable
3. Select environments (Production, Preview, Development)
4. Redeploy after adding variables

**Via Vercel CLI**:
```bash
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add NEXT_PUBLIC_API_URL production
```

## Step 4: Update API Client Configuration

The frontend API client (`lib/api.ts`) uses `NEXT_PUBLIC_API_URL` environment variable. Ensure it's set correctly:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

If `NEXT_PUBLIC_API_URL` is not set, it will fall back to `localhost:8000` (development only).

## Step 5: Verify Deployment

1. **Check Build Logs**:
   - Vercel Dashboard → Deployments → Click on latest deployment
   - Review build logs for errors

2. **Test the Application**:
   - Visit your Vercel URL: `https://your-app.vercel.app`
   - Test chat functionality
   - Verify API calls are going to your backend

3. **Check Network Tab**:
   - Open browser DevTools → Network
   - Verify API calls are using correct backend URL

## Troubleshooting

### Build Fails

**Error: "Module not found"**
- Ensure all dependencies are in `package.json`
- Run `npm install` locally to verify

**Error: "Environment variable not found"**
- Add all required environment variables in Vercel Dashboard
- Redeploy after adding variables

### API Calls Fail

**Error: "Failed to fetch" or CORS errors**
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check backend is running and accessible
- Ensure backend CORS allows your Vercel domain

**Backend CORS Configuration**:

The backend needs to allow requests from your Vercel domain. Update `backend/config.py`:

```python
# In backend/config.py
allowed_origins: List[str] = [
    "http://localhost:3000",  # Local development
    "https://your-app.vercel.app",  # Production Vercel URL
    # Add preview URLs as needed
]
```

**For Railway/Render/Fly.io**: Update the code before deploying, or use environment variables if your platform supports it.

**Quick Fix**: Temporarily allow all origins for testing (NOT recommended for production):
```python
allowed_origins: List[str] = ["*"]  # Allows all origins
```

**Better Solution**: Update `backend/config.py` to read from environment variable:
```python
import os
allowed_origins: List[str] = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000"
).split(",")
```

Then set in your backend platform:
```
ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
```

### Images Not Loading

**Error: "Image domain not configured"**
- Update `next.config.js` to include image domains:
```javascript
images: {
  domains: ['www.partselect.com', 'partselect.com', 'your-backend-url.com'],
}
```

## Custom Domain (Optional)

1. Go to Vercel Dashboard → Project → Settings → Domains
2. Add your custom domain
3. Follow DNS configuration instructions
4. Vercel will automatically provision SSL certificate

## Continuous Deployment

Vercel automatically deploys on every push to:
- **Production**: `main` or `master` branch
- **Preview**: All other branches and pull requests

Each preview deployment gets a unique URL for testing.

## Monitoring

- **Vercel Analytics**: Enable in Dashboard → Analytics
- **Logs**: View real-time logs in Vercel Dashboard → Deployments
- **Performance**: Check Web Vitals in Vercel Dashboard

## Cost Considerations

- **Vercel Hobby Plan**: Free for personal projects
  - 100GB bandwidth/month
  - Unlimited deployments
  - Preview deployments included

- **Backend Hosting**: 
  - Railway: Free tier available (limited hours)
  - Render: Free tier available (spins down after inactivity)
  - Fly.io: Free tier available (limited resources)

## Next Steps

1. Set up monitoring and error tracking (e.g., Sentry)
2. Configure custom domain
3. Set up staging environment
4. Enable Vercel Analytics
5. Configure automatic deployments from Git

---

**Need Help?**
- [Vercel Documentation](https://vercel.com/docs)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Railway Documentation](https://docs.railway.app)
