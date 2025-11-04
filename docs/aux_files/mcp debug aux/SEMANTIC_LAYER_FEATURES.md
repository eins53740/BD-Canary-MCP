# Semantic Layer Features - MCP Server Improvements

## 🎯 Overview

The MCP server now includes intelligent semantic search and business context, making it much easier for AI to work with industrial data without needing to know technical tag paths.

## ✨ Key Improvements

### 1. Semantic Search Layer
**New Knowledge Base**: `src/data/tag-knowledge.json`
- Maps technical Canary paths to business-friendly descriptions
- Includes keywords, equipment names, plant info for each sensor
- Example: "Kiln 5 production" → finds the exact tag path automatically

### 2. Renamed Tools (More Intuitive)

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `search_tags` | **`find_sensors`** | PRIMARY tool - Search by plain English |
| `browse_tags` | **`browse_hierarchy`** | ADVANCED - Navigate technical paths |
| `get_tag_data` | **`get_sensor_data`** | Query data with auto-enrichment |

### 3. Intelligent Tool: `find_sensors`

**What it does:**
- Searches using plain English queries
- Returns sensor paths WITH business descriptions
- Includes equipment, plant, and unit context
- Supports filtering by equipment or plant

**Example queries:**
```
find_sensors: "Kiln 5 production"
find_sensors: "pressure sensors"
find_sensors: "alternative fuel rate"
find_sensors: "Kiln 6 LCC feed"
```

**Response includes:**
```json
{
  "found": 2,
  "query": "Kiln 5 pressure",
  "tags": [
    {
      "tagPath": "Secil.Portugal.Cement.Maceira...FO5PT_387.Value",
      "description": "Maceira Kiln 5 Kiln Outlet Pressure",
      "equipment": "Kiln 5",
      "plant": "Maceira",
      "unit": "Kiln"
    }
  ]
}
```

### 4. Auto-Enriched Data Responses

When you query sensor data with `get_sensor_data`, responses now include:
- ✅ Business description (not just technical path)
- ✅ Equipment name
- ✅ Plant name
- ✅ Statistics (avg, min, max)
- ✅ Data points with timestamps

**Example:**
```json
{
  "Secil.Portugal.Cement.Maceira...Running": {
    "description": "Maceira Kiln 5 Producing",
    "equipment": "Kiln 5",
    "plant": "Maceira",
    "count": 100,
    "data": [...],
    "statistics": {
      "average": 0.95,
      "min": 0,
      "max": 1
    }
  }
}
```

### 5. Intelligent Guidance in `browse_hierarchy`

When `browse_hierarchy` returns no results, it now provides:

**✅ Actionable suggestions:**
- Try adding a search parameter
- Use find_sensors instead
- Specific examples based on the query

**Example empty response:**
```json
{
  "statusCode": "Good",
  "tags": [],
  "message": "⚠️ No tags found at this path.",
  "suggestions": [
    {
      "action": "Try adding a search filter",
      "description": "Use the 'search' parameter to filter...",
      "example": {
        "path": "/your/path",
        "search": "Kiln",
        "deep": true
      }
    },
    {
      "action": "Try find_sensors tool instead",
      "description": "The find_sensors tool is easier...",
      "example": {
        "tool": "find_sensors",
        "query": "Kiln 5 production"
      }
    }
  ]
}
```

## 🔧 Technical Architecture

### New Components Created

1. **`src/data/tag-knowledge.json`**
   - Structured knowledge base
   - 26 sensors mapped with full context

2. **`src/services/tagKnowledge.ts`**
   - TagKnowledgeService class
   - Methods: searchByDescription, getTagInfo, enrichTags, etc.

3. **`src/tools/findSensors.ts`**
   - Semantic search implementation
   - Keyword matching with filters

4. **Enhanced Tools**
   - `browseHierarchy.ts` - Now provides guidance on empty results
   - `getSensorData.ts` - Auto-enriches responses with context

## 📊 Usage Workflow

### For AI/Users:

1. **Finding sensors:** Always start with `find_sensors`
   ```
   find_sensors(query: "Kiln 5 production")
   → Returns exact tag paths
   ```

2. **Getting data:** Use returned paths with `get_sensor_data`
   ```
   get_sensor_data(
     tags: ["Secil.Portugal.Cement.Maceira..."],
     startTime: "yesterday",
     endTime: "now"
   )
   → Returns enriched data with descriptions
   ```

3. **Advanced browsing:** Only use `browse_hierarchy` for technical exploration
   ```
   browse_hierarchy(path: "/Secil/Portugal", search: "Kiln")
   → Gets guidance if empty
   ```

## 🎯 Benefits

### For AI:
- ✅ No need to guess technical paths
- ✅ Can use natural language queries
- ✅ Gets helpful guidance when stuck
- ✅ Receives business context automatically

### For Users:
- ✅ Ask questions in plain English
- ✅ "Show me Kiln 5 production data"
- ✅ AI understands equipment names
- ✅ Results include meaningful descriptions

### For Developers:
- ✅ Easy to extend knowledge base
- ✅ Add new sensors to JSON file
- ✅ No code changes needed for new mappings
- ✅ Cached for performance

## 📈 Coverage

Currently mapped:
- **Equipment:** Kiln 5, Kiln 6
- **Plant:** Maceira
- **Sensor types:** Production status, fuel rates, feed rates, pressure sensors
- **Total sensors:** 26 tags

**To extend:** Simply add entries to `src/data/tag-knowledge.json`

## 🚀 Next Steps

1. **Restart Claude Desktop** to load new version
2. **Test with queries like:**
   - "Show me Kiln 5 production status"
   - "What's the alternative fuel rate for Kiln 6?"
   - "Get pressure data for Kiln 5"

3. **Add more sensors** to knowledge base as needed

## 🎉 Result

The MCP server is now **much smarter** and acts as a true semantic layer, not just an API wrapper. The AI can understand business context and guide users effectively without requiring technical knowledge of the Canary structure.
