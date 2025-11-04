# MCP Server Improvements Applied

## Changes Made

### 1. Fixed Type Coercion Issue
**Problem:** Claude Desktop was sending strings for boolean/number parameters, causing validation errors.

**Solution:** Added `.coerce` to Zod schemas:
```typescript
// Before
deep: z.boolean().optional()
maxSize: z.number().optional()

// After
deep: z.coerce.boolean().optional()
maxSize: z.coerce.number().optional()
```

**Files Modified:**
- `src/tools/browseTags.ts`
- `src/tools/getTagData.ts`

### 2. Simplified Tool Set
Reduced from 9 tools to 2 essential tools:
- ✅ `browse_tags` - Find tags
- ✅ `get_tag_data` - Query historical data

Other tools commented out in `src/tools/index.ts` for clarity.

### 3. Updated Configuration
- `.mcp.json` - Updated with correct Canary server URL and API token
- Both Claude Desktop and Claude Code configs synchronized

## Current Status

### ✅ Working
- MCP server starts successfully
- Tools register correctly
- Type validation fixed
- Authentication configured

### ⚠️ Known Issues
- Empty results from `browse_tags` - needs investigation
  - Could be: no tags at root, path needs specification, or data visibility issue

## Next Steps to Enable in Claude Code

1. **Restart Claude Code session** to load the updated `.mcp.json`
2. **Test connection** by trying to call `browse_tags`
3. **Investigate empty results** - may need to:
   - Test direct API calls to Canary
   - Check specific paths/hierarchies
   - Verify data permissions

## For Claude Desktop Users

The server is already working in Claude Desktop. Restart the application to get the type coercion fixes.

## Testing Commands

Once MCP is loaded, try:
```
browse_tags with search="temperature"
browse_tags with path="/Plant"
```

If still empty, we may need to explore the Canary hierarchy structure.
