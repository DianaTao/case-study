# How to Find Your Railway Backend URL

This guide shows you how to get your Railway backend URL to use as `NEXT_PUBLIC_API_URL` in Vercel.

## Step 1: Deploy Your Backend on Railway

If you haven't deployed yet, follow [backend/BACKEND_DEPLOY.md](./backend/BACKEND_DEPLOY.md) - Option 1: Railway.

## Step 2: Get Your Railway URL

### Method 1: Railway Dashboard (Easiest)

1. **Go to [railway.app](https://railway.app)** and sign in
2. **Click on your project** (the one with your backend)
3. **Click on your service** (the backend service)
4. **Go to the "Settings" tab**
5. **Scroll down to "Networking" section**
6. **Look for "Public Domain"** or **"Generate Domain"**

   You'll see something like:
   ```
   Public Domain: your-app-name.up.railway.app
   ```

7. **Copy the full URL** (including `https://`):
   ```
   https://your-app-name.up.railway.app
   ```

### Method 2: Railway Dashboard - Deployments Tab

1. **Go to your service** in Railway
2. **Click on the "Deployments" tab**
3. **Click on the latest deployment**
4. **Look at the logs** - Railway often prints the URL during deployment
5. **Or check the "Settings" → "Networking"** section

### Method 3: Railway CLI

If you have Railway CLI installed:

```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Get the URL
railway domain
```

This will show your Railway domain.

## Step 3: Verify Your Backend is Running

Before using the URL, verify it's working:

```bash
# Test the health endpoint
curl https://your-app-name.up.railway.app/health

# Should return:
# {"status":"healthy","database":"connected",...}
```

Or open in browser:
```
https://your-app-name.up.railway.app/health
```

## Step 4: Use This URL in Vercel

1. **Copy your Railway URL**: `https://your-app-name.up.railway.app`
2. **Go to Vercel Dashboard** → Your Project → Settings → Environment Variables
3. **Add/Edit `NEXT_PUBLIC_API_URL`**:
   - Value: `https://your-app-name.up.railway.app`
   - **Important**: No trailing slash!
4. **Select all environments** (Production, Preview, Development)
5. **Save**
6. **Redeploy** your Vercel frontend

## Railway URL Format

Railway URLs typically look like:
- `https://your-app-name.up.railway.app`
- `https://your-project-production.up.railway.app`
- `https://backend-production-xxxx.up.railway.app`

**Always use `https://`** - Railway provides SSL automatically.

## Custom Domain (Optional)

If you want a custom domain:

1. **Railway Dashboard** → Your Service → Settings → Networking
2. **Click "Custom Domain"**
3. **Add your domain** (e.g., `api.yourdomain.com`)
4. **Follow DNS instructions** Railway provides
5. **Use this custom domain** as your `NEXT_PUBLIC_API_URL`

## Troubleshooting

### Can't find the URL?

1. **Check if service is deployed**:
   - Go to Deployments tab
   - Make sure latest deployment is successful (green checkmark)

2. **Check if public domain is enabled**:
   - Settings → Networking
   - Make sure "Public Domain" is enabled/generated

3. **Check service is running**:
   - Go to Metrics tab
   - Should show active requests/CPU usage

### URL not working?

1. **Test the URL directly**:
   ```bash
   curl https://your-app-name.up.railway.app/health
   ```

2. **Check Railway logs**:
   - Go to Deployments → Latest → View Logs
   - Look for errors

3. **Verify environment variables**:
   - Settings → Variables
   - Make sure `SUPABASE_URL`, `SUPABASE_KEY`, etc. are set

4. **Check if service crashed**:
   - Metrics tab should show activity
   - If not, check logs for errors

### URL changes after redeploy?

- Railway URLs are **stable** - they don't change unless you:
  - Delete and recreate the service
  - Change the service name
- If you need a permanent URL, use a **Custom Domain**

## Quick Reference

**Railway Backend URL Format:**
```
https://[service-name].up.railway.app
```

**Example:**
```
https://partselect-backend-production.up.railway.app
```

**Use in Vercel:**
```
NEXT_PUBLIC_API_URL=https://partselect-backend-production.up.railway.app
```

---

**Next Steps:**
1. ✅ Get your Railway URL
2. ✅ Test it works (`/health` endpoint)
3. ✅ Set it in Vercel as `NEXT_PUBLIC_API_URL`
4. ✅ Redeploy Vercel frontend
5. ✅ Test the full integration

See [VERCEL_ENV_SETUP.md](./VERCEL_ENV_SETUP.md) for setting up Vercel environment variables.
