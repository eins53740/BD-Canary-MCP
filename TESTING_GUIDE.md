# Canary MCP Server - Testing Guide

## 🎯 Setup Complete! Your Files are Ready:

✅ **`.env`** - Contains your Canary API token and configuration
✅ **`claude_desktop_config.json`** - Claude Desktop MCP server configuration

---

## 📦 Step 1: Install Claude Desktop Configuration

### Windows 11 Setup:

1. **Locate Claude Desktop config directory:**
   ```
   %APPDATA%\Claude\
   ```
   Full path: `C:\Users\bsdias\AppData\Roaming\Claude\`

2. **Copy the configuration file:**
   - Copy `claude_desktop_config.json` from this project folder
   - To: `C:\Users\bsdias\AppData\Roaming\Claude\claude_desktop_config.json`

   **OR** merge with existing config if you already have one.

3. **Restart Claude Desktop** completely (close and reopen)

---

## 🔧 Step 2: Verify MCP Server is Connected

When you open Claude Desktop, you should see:
- 🔌 **MCP server indicator** (usually a plugin icon or status)
- The server name: **"canary-historian"**
- Available tools should be listed

---

## 🧪 Step 3: Test Basic Connectivity

### Test 1: Ping the Server
Ask Claude:
```
Can you ping the Canary MCP server to check if it's working?
```

**Expected**: Response like "pong - Canary MCP Server is running!"

---

## 🔍 Step 4: Explore Your Canary Hierarchy

Based on the image you showed me, your tags are structured like:
```
Views/Secil/Portugal/Cement/Maceira/
  ├─ 400 - Clinker Production/
      ├─ 431 - Kiln/
          ├─ Normalised/
              ├─ Energy/
                  └─ P431  (Plant Area Instant Power)
```

### Test 2: List Namespaces
Ask Claude:
```
Can you list the available namespaces in the Canary historian?
```

**Expected**: Should show hierarchy starting with "Views/Secil/..."

---

## 🎯 Step 5: Find "Kiln 5 431 Shell Velocity"

### Test 3: Search for Shell Velocity Tags
Ask Claude:
```
Search for tags related to kiln 5 431 shell velocity in the Canary system
```

**What Claude will do:**
1. Use `search_tags("*431*shell*velocity*")` or similar patterns
2. Look through the results
3. Suggest the most likely tag path

### Likely Tag Path Pattern:
Based on your structure, expect something like:
```
Views/Secil/Portugal/Cement/Maceira/400 - Clinker Production/431 - Kiln/[Category]/[ShellVelocity_Tag]
```

Possible categories: `Mechanical`, `Process`, `Normalised`, etc.

---

## 📊 Step 6: Get the Latest Data

### Test 4: Read Recent Data
Once Claude finds the tag, ask:
```
What is the latest value for kiln 5 431 shell velocity?
```

**What Claude will do:**
1. Use `read_timeseries()` with:
   - The discovered tag path
   - Time range: "past 24 hours" to "now"
   - Page size: 1 (just get the latest)
2. Return the most recent value with timestamp and quality

---

## 🎨 Example Full Conversation

**You:** "What is the kiln 5 431 latest shell velocity?"

**Claude will:**
1. Search for tags: `search_tags("*431*shell*velocity*")`
2. Find candidates (e.g., multiple matches)
3. May ask you to confirm which tag if multiple found
4. Read recent data: `read_timeseries(tag_path, "past 24 hours", "now")`
5. Report: "The latest shell velocity for Kiln 5 431 is X rpm at [timestamp], quality: Good"

---

## 🔬 Advanced Testing

### Test with Natural Language Time Expressions:
```
Show me the average kiln 5 431 shell velocity from yesterday
```

Claude will:
- Parse "yesterday" → ISO timestamps for yesterday 00:00 to 23:59
- Search for the tag
- Read timeseries data for that period
- Calculate average (if multiple data points)

### Test Multiple Tags:
```
Compare the kiln 5 instant power P431 with the shell velocity over the last 24 hours
```

---

## 🐛 Troubleshooting

### Problem: "MCP server not found"
- **Solution**: Verify `claude_desktop_config.json` is in the correct location
- **Check**: `C:\Users\bsdias\AppData\Roaming\Claude\claude_desktop_config.json`
- **Restart**: Claude Desktop after copying

### Problem: "Authentication failed"
- **Solution**: Verify token in `.env` file is correct
- **Check**: Token = `0120fd2e-e9c2-4c8d-8115-a6ceb41490ce`

### Problem: "Tag not found"
- **Solution**: Use `list_namespaces()` first to explore the hierarchy
- **Try**: Broader search patterns like `*431*` or `*kiln*`

### Problem: "No data available"
- **Solution**: Check if the tag is actively logging data
- **Verify**: Use the Canary Administrator (as shown in your image) to confirm recent data

---

## 📝 Available MCP Tools

Your MCP server currently provides these tools:

1. **`ping()`** - Test connectivity
2. **`list_namespaces()`** - Browse tag hierarchy
3. **`search_tags(pattern)`** - Find tags by pattern (supports wildcards)
4. **`get_tag_metadata(tag_path)`** - Get detailed tag properties
5. **`read_timeseries(tag_names, start_time, end_time, page_size)`** - Retrieve historical data
   - Supports natural language times: "yesterday", "last week", "past 24 hours"
   - Supports multiple tags
   - Returns timestamps, values, and quality flags

---

## 🚀 Next Steps

After successful testing, you may want to:

1. **Implement Semantic Resolution** (Story 1.7+)
   - Fuzzy tag name matching
   - Context-aware search (plant/area/unit)
   - Synonym expansion (speed ↔ rpm, velocity)
   - As described in `docs/MCP_API_semantics_tags.md`

2. **Add More Tools** (Epic 1 remaining stories)
   - `get_server_info()` - Server health/capabilities
   - Test data fixtures
   - Enhanced error handling

3. **Production Hardening** (Epic 2)
   - Connection pooling
   - Caching layer
   - Advanced retry logic
   - Performance validation

---

## 📞 Need Help?

If you encounter issues:
1. Check the server is actually running
2. Look at console logs for error messages
3. Verify network connectivity to `scunscanary.secil.pt`
4. Test with simpler queries first (like `ping()`)

**Happy Testing! 🎉**
