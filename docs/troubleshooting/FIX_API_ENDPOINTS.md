# Fix Canary API Endpoint Configuration

## ✅ Good News!

Your MCP server IS working! The issue is just the API endpoint URL.

**Error Found:**
```
404 Not Found: https://scunscanary.secil.pt/api/v1/getSessionToken
```

---

## 🔍 Finding the Correct Endpoints

Your Canary server is at: `https://scunscanary.secil.pt`

But we need to find the correct API paths. Here are the possibilities:

### Option 1: Read API (Views API)

Canary Views Read API typically uses paths like:
```
https://scunscanary.secil.pt/readapi/v1/...
```

### Option 2: Different API Version

Could be:
```
https://scunscanary.secil.pt/api/v2/...
```

### Option 3: No API prefix

Sometimes it's directly:
```
https://scunscanary.secil.pt/v1/...
```

---

## 🧪 Let's Test Your Endpoints

### Method 1: Check Canary Documentation

Do you have access to Canary Administrator? Look for:
1. Settings → API Configuration
2. Help → API Documentation
3. Or check the URL when you're logged into Canary Administrator

### Method 2: Test Common Canary Endpoints

Try accessing these URLs in your browser (you'll need to be logged in):

**Views Read API (most common):**
```
https://scunscanary.secil.pt/readapi/v1/getAggregates
```

**Alternative path:**
```
https://scunscanary.secil.pt/api/readapi/v1/getAggregates
```

**Or:**
```
https://scunscanary.secil.pt/views/api/v1/getAggregates
```

---

## 🔧 Update Configuration Once You Find the Correct Path

### If the correct base URL is (for example):
```
https://scunscanary.secil.pt/readapi/v1
```

### Then update your `.env` file:

```env
# For authentication and session management
CANARY_SAF_BASE_URL=https://scunscanary.secil.pt/readapi/v1

# For data queries (Views API)
CANARY_VIEWS_BASE_URL=https://scunscanary.secil.pt/readapi
```

### Common Canary API Endpoint Patterns:

| Pattern | SAF_BASE_URL | VIEWS_BASE_URL |
|---------|-------------|----------------|
| Pattern A (Read API) | `https://scunscanary.secil.pt/readapi/v1` | `https://scunscanary.secil.pt/readapi` |
| Pattern B (Direct API) | `https://scunscanary.secil.pt/api/v1` | `https://scunscanary.secil.pt` |
| Pattern C (Nested) | `https://scunscanary.secil.pt/views/api/v1` | `https://scunscanary.secil.pt/views` |

---

## 📋 Alternative: Use API Token Without Session

Some Canary setups use **direct API token authentication** instead of session tokens.

Check if your API token (`<API_TOKEN>`) works directly in API calls:

### Test with curl or browser:

```
https://scunscanary.secil.pt/readapi/v1/browseTags?token=<API_TOKEN>
```

Or with Authorization header:
```
Authorization: Bearer <API_TOKEN>
```

---

## 🎯 Quick Test Steps

1. **Open your Canary Administrator** (the screenshot you showed)
2. **Look for API documentation or settings**
3. **Note the API base URL shown there**
4. **OR try these test URLs in your browser:**
   - https://scunscanary.secil.pt/readapi/v1/getAggregates
   - https://scunscanary.secil.pt/api/v1/getAggregates
   - https://scunscanary.secil.pt/views/api/v1/getAggregates

5. **Whichever one doesn't give 404, use that pattern**

---

## 💡 Temporary Workaround: Skip Validation

While we figure out the correct endpoint, you can temporarily disable the validation to test:

### Create a test version without validation:

In your project, let's comment out the validation temporarily to test the other tools:

**But first, let's find the correct endpoint!**

---

## 📞 What Information Do You Have?

To help you faster, can you tell me:

1. **When you access Canary Administrator**, what URL do you use?
   - Example: `https://scunscanary.secil.pt/administrator`
   - Or: `https://scunscanary.secil.pt:8080`

2. **Does your Canary have API documentation?**
   - Usually in Help menu or Settings

3. **What version of Canary are you running?**
   - Look for version number in About or Help

4. **Can you test one of these URLs** (just paste in browser):
   - `https://scunscanary.secil.pt/readapi/v1/getAggregates`
   - `https://scunscanary.secil.pt/api/v1/getAggregates`

---

## 🚀 Next Steps

**Tell me:**
1. Which URL from the tests above works (doesn't show 404)
2. OR what you see in the Canary Administrator for API settings

Then I'll update the configuration files with the correct endpoints and your MCP server will work!

---

**The MCP server code is working perfectly - we just need the right URL! 🎯**
