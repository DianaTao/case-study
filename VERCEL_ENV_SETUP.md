# Fixing Vercel Environment Variables

## Problem: Frontend trying to connect to localhost

If you see errors like:
```
Access to fetch at 'http://localhost:8000/api/chat' from origin 'https://your-app.vercel.app'
```

This means `NEXT_PUBLIC_API_URL` is not set in Vercel.

## Quick Fix (5 minutes)

### Step 1: Get Your Backend URL

First, make sure your backend is deployed. You should have a URL like:
- `https://your-app.railway.app`
- `https://your-app.onrender.com`
- `https://your-app.fly.dev`

### Step 2: Set Environment Variable in Vercel

#### Option A: Vercel Dashboard (Easiest)

1. Go to [vercel.com/dashboard](https://vercel.com/dashboard)
2. Click on your project
3. Go to **Settings** → **Environment Variables**
4. Click **Add New**
5. Add these variables:

   | Name | Value | Environment |
   |------|-------|-------------|
   | `NEXT_PUBLIC_API_URL` | `https://your-backend-url.com` | Production, Preview, Development |
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://xxx.supabase.co` | Production, Preview, Development |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `eyJhbGc...` | Production, Preview, Development |

6. **Important**: Make sure to select all three environments (Production, Preview, Development)
7. Click **Save**

#### Option B: Vercel CLI

```bash
# Set API URL
vercel env add NEXT_PUBLIC_API_URL production
# When prompted, enter: https://your-backend-url.com

# Set Supabase URL
vercel env add NEXT_PUBLIC_SUPABASE_URL production
# When prompted, enter: https://xxx.supabase.co

# Set Supabase Key
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
# When prompted, enter: your_supabase_anon_key
```

### Step 3: Redeploy

After adding environment variables, you need to redeploy:

**Option A: Via Dashboard**
1. Go to **Deployments** tab
2. Click the **⋯** menu on the latest deployment
3. Click **Redeploy**

**Option B: Via CLI**
```bash
vercel --prod
```

**Option C: Push to Git**
```bash
git commit --allow-empty -m "Trigger redeploy"
git push
```

### Step 4: Verify

1. Wait for deployment to complete
2. Visit your Vercel URL
3. Open browser DevTools → Console
4. You should no longer see `localhost:8000` errors
5. Try using the chat - it should connect to your backend

## Troubleshooting

### Still seeing localhost errors?

1. **Check environment variables are set**:
   - Go to Vercel Dashboard → Settings → Environment Variables
   - Verify `NEXT_PUBLIC_API_URL` is set and has the correct value
   - Make sure it's enabled for **Production** environment

2. **Check the value is correct**:
   - Should be `https://your-backend-url.com` (no trailing slash)
   - Should NOT be `http://localhost:8000`

3. **Verify backend is running**:
   ```bash
   curl https://your-backend-url.com/health
   ```
   Should return: `{"status":"healthy",...}`

4. **Check CORS on backend**:
   - Make sure your backend's `ALLOWED_ORIGINS` includes your Vercel domain
   - Example: `https://your-app.vercel.app`
   - See [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) for CORS setup

### Environment variable not taking effect?

- **Next.js caches environment variables at build time**
- You MUST redeploy after adding/changing environment variables
- Just saving in dashboard is not enough - trigger a new deployment

### Check current environment variables

**Via Dashboard:**
- Settings → Environment Variables → See all variables

**Via CLI:**
```bash
vercel env ls
```

## Required Environment Variables

Make sure you have ALL of these set:

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Your backend URL | `https://your-app.railway.app` |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGc...` |

**Note**: All `NEXT_PUBLIC_*` variables are exposed to the browser, so they're safe to use in client-side code.

## Still Having Issues?

1. **Check browser console** for specific error messages
2. **Check Vercel deployment logs** for build errors
3. **Check backend logs** to see if requests are reaching it
4. **Verify backend CORS** allows your Vercel domain

---

**Quick Checklist:**
- [ ] Backend is deployed and accessible
- [ ] `NEXT_PUBLIC_API_URL` is set in Vercel
- [ ] `NEXT_PUBLIC_SUPABASE_URL` is set in Vercel
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` is set in Vercel
- [ ] Redeployed after setting variables
- [ ] Backend CORS allows Vercel domain
