# Fixing CORS Errors in Railway Backend

## Problem

You're seeing errors like:
```
Access to fetch at 'https://case-study-production.up.railway.app/api/chat' 
from origin 'https://case-study-dianataos-projects.vercel.app' 
has been blocked by CORS policy
```

This means your **backend is not allowing requests from your Vercel frontend**.

## Quick Fix (2 minutes)

### Step 1: Update Backend CORS in Railway

1. **Go to [railway.app](https://railway.app)** → Your Project → Your Backend Service
2. **Click on "Variables" tab**
3. **Find or add `ALLOWED_ORIGINS` environment variable**
4. **Set the value to** (comma-separated, no spaces):
   ```
   http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://*.vercel.app
   ```

   **Or if you want to allow all Vercel preview deployments:**
   ```
   http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://case-study-*.vercel.app,https://*.vercel.app
   ```

5. **Click "Save"** or "Add Variable"

### Step 2: Redeploy Backend

After updating the environment variable, Railway will automatically redeploy. If not:

1. **Go to "Deployments" tab**
2. **Click "Redeploy"** on the latest deployment
3. **Wait for deployment to complete** (usually 1-2 minutes)

### Step 3: Verify CORS is Working

Test if CORS is fixed:

```bash
# Test from command line
curl -X OPTIONS https://case-study-production.up.railway.app/api/chat \
  -H "Origin: https://case-study-dianataos-projects.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

You should see headers like:
```
< Access-Control-Allow-Origin: https://case-study-dianataos-projects.vercel.app
< Access-Control-Allow-Methods: POST, GET, OPTIONS
```

Or test in browser console on your Vercel site:
```javascript
fetch('https://case-study-production.up.railway.app/health')
  .then(r => r.json())
  .then(console.log)
```

## Detailed Steps

### Option 1: Using Railway Dashboard

1. **Navigate to your service** in Railway
2. **Click "Variables" tab** (left sidebar)
3. **If `ALLOWED_ORIGINS` exists:**
   - Click the edit icon (pencil)
   - Update the value
   - Click "Save"
4. **If `ALLOWED_ORIGINS` doesn't exist:**
   - Click "New Variable"
   - Key: `ALLOWED_ORIGINS
   - Value: `http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://*.vercel.app`
   - Click "Add"

### Option 2: Using Railway CLI

```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login
railway login

# Link to your project
railway link

# Set the variable
railway variables set ALLOWED_ORIGINS="http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://*.vercel.app"
```

## Understanding ALLOWED_ORIGINS Format

The `ALLOWED_ORIGINS` environment variable should be a **comma-separated list** of allowed origins:

```
http://localhost:3000,https://your-app.vercel.app,https://*.vercel.app
```

**Important:**
- ✅ Use **comma-separated** (no spaces around commas)
- ✅ Include **protocol** (`https://` not just domain)
- ✅ Use `https://*.vercel.app` to allow all Vercel preview deployments
- ❌ Don't use spaces: `http://localhost:3000, https://app.vercel.app` (wrong)
- ❌ Don't forget protocol: `your-app.vercel.app` (wrong)

## Your Specific Values

Based on your error, use:

```
ALLOWED_ORIGINS=http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://*.vercel.app
```

This allows:
- `http://localhost:3000` - Local development
- `https://case-study-dianataos-projects.vercel.app` - Your production Vercel URL
- `https://*.vercel.app` - All Vercel preview deployments

## Verify Backend is Running

Before fixing CORS, make sure your backend is actually running:

```bash
# Test health endpoint
curl https://case-study-production.up.railway.app/health

# Should return:
# {"status":"healthy","database":"connected",...}
```

If this fails, your backend isn't running - fix that first.

## Troubleshooting

### Still getting CORS errors after update?

1. **Verify variable is set correctly:**
   - Railway Dashboard → Variables → Check `ALLOWED_ORIGINS` value
   - Make sure there are no extra spaces or typos

2. **Check backend logs:**
   - Railway Dashboard → Deployments → Latest → View Logs
   - Look for CORS-related errors

3. **Verify backend restarted:**
   - After setting environment variable, Railway should auto-redeploy
   - Check Deployments tab - should show a new deployment

4. **Test CORS directly:**
   ```bash
   curl -X OPTIONS https://case-study-production.up.railway.app/api/chat \
     -H "Origin: https://case-study-dianataos-projects.vercel.app" \
     -H "Access-Control-Request-Method: POST" \
     -v 2>&1 | grep -i "access-control"
   ```

5. **Check backend code:**
   - Make sure `backend/config.py` reads from `ALLOWED_ORIGINS` environment variable
   - The code should split by comma: `.split(",")`

### Backend not reading ALLOWED_ORIGINS?

Check `backend/config.py` - it should have:

```python
_allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
allowed_origins: List[str] = (
    [origin.strip() for origin in _allowed_origins_env.split(",") if origin.strip()]
    if _allowed_origins_env
    else ["http://localhost:3000"]
)
```

If it doesn't, update the file and redeploy.

### Wildcard not working?

Some platforms don't support `https://*.vercel.app` wildcards. In that case, list specific domains:

```
ALLOWED_ORIGINS=http://localhost:3000,https://case-study-dianataos-projects.vercel.app,https://case-study-git-main-dianataos-projects.vercel.app
```

## Quick Checklist

- [ ] Backend is deployed and running (test `/health` endpoint)
- [ ] `ALLOWED_ORIGINS` is set in Railway Variables
- [ ] Value includes your Vercel domain: `https://case-study-dianataos-projects.vercel.app`
- [ ] Value is comma-separated (no spaces)
- [ ] Backend has been redeployed after setting variable
- [ ] Tested CORS with curl or browser

## After Fixing

Once CORS is fixed:
1. ✅ Refresh your Vercel frontend
2. ✅ Try using the chat
3. ✅ Check browser console - CORS errors should be gone
4. ✅ API calls should work

---

**Still having issues?** Check:
- Railway deployment logs for errors
- Backend is actually running (test `/health`)
- Environment variable is set correctly (no typos)
- Backend code reads from `ALLOWED_ORIGINS` correctly
