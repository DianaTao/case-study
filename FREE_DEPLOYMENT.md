# Free Deployment Options

Complete guide to deploying the PartSelect Chat Agent **100% FREE**.

## ✅ Frontend (Next.js) - FREE on Vercel

### Vercel Hobby Plan (FREE)

**What's Included:**
- ✅ Unlimited deployments
- ✅ 100GB bandwidth/month
- ✅ Preview deployments for every branch/PR
- ✅ Automatic SSL certificates
- ✅ Global CDN
- ✅ Custom domains
- ✅ Analytics (basic)

**Limitations:**
- Personal projects only (not for commercial use)
- No team collaboration features
- Limited support

**Perfect for:** Personal projects, portfolios, case studies

**Deploy:** See [VERCEL_DEPLOY.md](./VERCEL_DEPLOY.md)

---

## ✅ Backend (Python FastAPI) - FREE Options

### Option 1: Render (Best Free Option) ⭐

**Free Tier:**
- ✅ Always free for web services
- ✅ Automatic deployments from GitHub
- ✅ SSL certificates included
- ✅ Custom domains

**Limitations:**
- ⚠️ Spins down after **15 minutes of inactivity**
- ⚠️ Cold start: **30-60 seconds** on first request after spin-down
- ⚠️ 750 hours/month limit (enough for most projects)

**Best For:** Projects with occasional traffic, development/testing

**Deploy:** See [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) - Option 2

---

### Option 2: Railway (Good for Active Projects)

**Free Tier:**
- ✅ **$5 credit/month** (enough for small projects)
- ✅ Always-on service (no spin-down)
- ✅ Fast cold starts
- ✅ Automatic deployments

**Limitations:**
- ⚠️ Limited to $5 worth of usage/month
- ⚠️ May need to upgrade if usage exceeds credit

**Best For:** Projects with regular traffic

**Deploy:** See [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) - Option 1

---

### Option 3: Fly.io (Most Generous Free Tier)

**Free Tier:**
- ✅ **3 shared-cpu VMs** (always-on)
- ✅ **3GB persistent volumes**
- ✅ Global edge network
- ✅ No spin-down

**Limitations:**
- ⚠️ Shared CPU (slower than dedicated)
- ⚠️ Limited to 3 VMs

**Best For:** Projects needing always-on service

**Deploy:** See [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) - Option 3

---

## 🎯 Recommended FREE Setup

### For Development/Testing:
1. **Frontend**: Vercel (FREE) ✅
2. **Backend**: Render (FREE) ✅
   - Accept the 30-60s cold start
   - Perfect for testing and demos

### For Production (Always-On):
1. **Frontend**: Vercel (FREE) ✅
2. **Backend**: Railway (FREE - $5 credit/month) ✅
   - No cold starts
   - Always available
   - Monitor usage to stay within free tier

### For Maximum Free Resources:
1. **Frontend**: Vercel (FREE) ✅
2. **Backend**: Fly.io (FREE) ✅
   - 3 always-on VMs
   - No spin-down
   - Most generous free tier

---

## 💰 Cost Comparison

| Platform | Free Tier | Always-On | Cold Starts | Best For |
|----------|-----------|-----------|-------------|----------|
| **Vercel** | ✅ Yes | ✅ Yes | ❌ No | Frontend |
| **Render** | ✅ Yes | ⚠️ No (spins down) | ⚠️ 30-60s | Development |
| **Railway** | ✅ $5 credit | ✅ Yes | ❌ No | Production |
| **Fly.io** | ✅ 3 VMs | ✅ Yes | ❌ No | Production |

---

## 🚀 Quick Start: 100% Free Deployment

### Step 1: Deploy Frontend (5 minutes)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
cd /path/to/case-study-main
vercel

# Add environment variables
vercel env add NEXT_PUBLIC_SUPABASE_URL
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY
vercel env add NEXT_PUBLIC_API_URL  # Will set after backend deploy

# Deploy to production
vercel --prod
```

### Step 2: Deploy Backend on Render (10 minutes)

1. Go to [render.com](https://render.com) → Sign up (FREE)
2. New → Web Service → Connect GitHub
3. Configure:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium && playwright install-deps`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `OPENAI_API_KEY`
   - `ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app`
5. Deploy → Copy backend URL

### Step 3: Connect Frontend to Backend (2 minutes)

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Update `NEXT_PUBLIC_API_URL` with your Render backend URL
3. Redeploy (or wait for auto-deploy)

**Total Time**: ~15-20 minutes  
**Total Cost**: $0/month ✅

---

## ⚠️ Important Notes

### Render Free Tier Limitations:
- **Cold Starts**: First request after 15 min inactivity takes 30-60s
- **Solution**: Use a "ping" service (UptimeRobot, etc.) to keep it awake
- **Or**: Upgrade to Starter ($7/month) for always-on

### Railway Free Tier:
- Monitor usage in dashboard
- $5 credit usually lasts the month for small projects
- Upgrade if you exceed credit

### Fly.io Free Tier:
- Most generous free tier
- 3 VMs should be enough for most projects
- Good for production use

---

## 🎁 Bonus: Keep Backend Awake (Render)

To avoid cold starts on Render free tier, use a free uptime monitor:

1. Sign up for [UptimeRobot](https://uptimerobot.com) (FREE)
2. Add monitor for your Render backend URL
3. Set check interval to 5 minutes
4. This keeps your backend awake (stays within free tier limits)

---

## 📊 Summary

**✅ You can deploy everything 100% FREE:**

- **Frontend**: Vercel Hobby (FREE) - Perfect ✅
- **Backend**: Render (FREE) or Railway ($5 credit) or Fly.io (FREE) ✅

**Recommended for case study:**
- Frontend: Vercel
- Backend: Render (accept cold starts) or Railway (if you want always-on)

**All platforms offer:**
- Automatic deployments from GitHub
- SSL certificates
- Custom domains
- Environment variables
- Logs and monitoring

---

**Need Help?**
- Frontend: [VERCEL_DEPLOY.md](./VERCEL_DEPLOY.md)
- Backend: [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md)
