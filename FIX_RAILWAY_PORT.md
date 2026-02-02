# Fixing Railway PORT Error

## Problem

You're seeing errors like:
```
Error: Invalid value for '--port': '$PORT' is not a valid integer.
```

This means Railway isn't expanding the `$PORT` environment variable correctly in the start command.

## Quick Fix

### Option 1: Update Start Command in Railway Dashboard (Easiest)

1. **Go to [railway.app](https://railway.app)** → Your Project → Your Backend Service
2. **Click "Settings" tab**
3. **Scroll to "Deploy" section**
4. **Find "Start Command"**
5. **Change it from:**
   ```
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   
   **To:**
   ```
   python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```
   
   Or simply:
   ```
   python -m uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

6. **Click "Save"**
7. **Railway will auto-redeploy**

### Option 2: Use Procfile (Recommended)

Railway automatically detects a `Procfile` in your project root.

1. **Create `backend/Procfile`** (already created for you):
   ```
   web: python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
   ```

2. **Commit and push**:
   ```bash
   git add backend/Procfile
   git commit -m "Add Procfile for Railway"
   git push
   ```

3. **Railway will auto-detect and use it**

### Option 3: Update railway.json

The `backend/railway.json` has been updated with the correct format:

```json
{
  "deploy": {
    "startCommand": "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
  }
}
```

## Why This Happens

Railway provides the `PORT` environment variable, but:
- Some shells don't expand `$PORT` in start commands
- Using `python -m uvicorn` is more reliable than just `uvicorn`
- `${PORT:-8000}` provides a fallback if PORT isn't set

## Verify It's Working

After fixing, check Railway logs:

1. **Go to Railway Dashboard** → Your Service → Deployments
2. **Click on latest deployment** → View Logs
3. **Look for:**
   ```
   INFO:     Uvicorn running on http://0.0.0.0:XXXX (Press CTRL+C to quit)
   ```
   Where `XXXX` is the port Railway assigned

4. **Test the health endpoint:**
   ```bash
   curl https://case-study-production.up.railway.app/health
   ```
   Should return: `{"status":"healthy",...}`

## Alternative: Use Python Script

If the above doesn't work, update `backend/main.py` to read PORT from environment:

```python
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", settings.port))
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=port,
        reload=settings.environment == "development"
    )
```

Then use start command:
```
python main.py
```

## Troubleshooting

### Still getting PORT errors?

1. **Check Railway Variables:**
   - Go to Variables tab
   - Verify `PORT` is set (Railway sets this automatically)
   - If not, Railway might be using a different variable name

2. **Check Start Command:**
   - Settings → Deploy → Start Command
   - Make sure it's exactly: `python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
   - No extra spaces or quotes

3. **Check Root Directory:**
   - Settings → Root Directory should be: `backend`
   - This ensures Railway runs commands from the right directory

4. **Check Logs:**
   - Deployments → Latest → View Logs
   - Look for the exact error message
   - Check if uvicorn is even starting

### Backend still not responding?

1. **Verify build succeeded:**
   - Check build logs for errors
   - Make sure all dependencies installed

2. **Check if service is running:**
   - Go to Metrics tab
   - Should show CPU/memory usage if running

3. **Test locally with same command:**
   ```bash
   cd backend
   PORT=8000 python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

## Quick Checklist

- [ ] Start command uses `python -m uvicorn` (not just `uvicorn`)
- [ ] Port uses `${PORT:-8000}` format (with fallback)
- [ ] Root directory is set to `backend` in Railway
- [ ] Procfile exists in `backend/` directory (optional but recommended)
- [ ] Backend code reads PORT from environment (updated in main.py)
- [ ] Railway has redeployed after changes

---

**After fixing, your backend should:**
- ✅ Start successfully
- ✅ Respond to `/health` endpoint
- ✅ Accept requests from your Vercel frontend (after CORS is fixed)
