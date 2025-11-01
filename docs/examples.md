# Example Query Library & Use Cases

**Story 2.7: Example Query Library & Use Cases**

Real-world examples for using the Canary MCP Server in daily plant operations.

## Table of Contents

- [Validation Use Cases](#validation-use-cases)
- [Troubleshooting Use Cases](#troubleshooting-use-cases)
- [Optimization Use Cases](#optimization-use-cases)
- [Reporting Use Cases](#reporting-use-cases)
- [Integration Examples](#integration-examples)

---

## Validation Use Cases

### 1. Verify Sensor Reading Against Expected Range

**Scenario**: Check if Kiln 6 temperature is within operational limits

**Natural Language Query:**
```
"Is Kiln 6 temperature within the normal range of 800-900°C?"
```

**MCP Tool Calls:**
```
1. get_tag_metadata(tag_path="Maceira.Cement.Kiln6.Temperature")
2. read_timeseries(
     tag_name="Maceira.Cement.Kiln6.Temperature",
     start_time="past 24 hours",
     end_time="now"
   )
```

**Expected Response:**
```json
{
  "analysis": "Current temperature is 850°C, within normal range (800-900°C)",
  "status": "NORMAL",
  "latest_value": 850.2,
  "timestamp": "2024-01-15T14:30:00Z"
}
```

---

### 2. Cross-Validate Multiple Sensors

**Scenario**: Verify consistent readings across redundant temperature sensors

**Natural Language Query:**
```
"Compare readings from all temperature sensors on Kiln 6"
```

**MCP Tool Calls:**
```
1. search_tags(search_pattern="Kiln6*Temperature")
2. For each tag found:
   read_timeseries(
     tag_name=<tag>,
     start_time="past 1 hour",
     end_time="now"
   )
```

**Use Case**: Identify sensor drift or failures

---

### 3. Validate Data Quality

**Scenario**: Check for missing or invalid data

**Natural Language Query:**
```
"Are there any quality issues with Kiln 6 data from yesterday?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="yesterday",
     end_time="now"
   )
2. Analyze quality flags in response
```

**Key Fields to Check:**
- `quality: "good"` - Valid data
- `quality: "bad"` - Sensor failure
- `quality: "uncertain"` - Questionable reading

---

## Troubleshooting Use Cases

### 4. Diagnose Production Anomaly

**Scenario**: Cement quality dropped at 10 AM, investigate cause

**Natural Language Query:**
```
"What happened to Kiln 6 between 9:00 and 11:00 today?"
```

**MCP Tool Calls:**
```
1. search_tags(search_pattern="Kiln6*")
2. For key process tags:
   read_timeseries(
     tag_name=<tag>,
     start_time="2024-01-15T09:00:00Z",
     end_time="2024-01-15T11:00:00Z"
   )
```

**Analysis Pattern:**
- Look for sudden changes in temperature
- Check fuel flow rates
- Verify oxygen levels
- Correlate with quality drop timestamp

---

### 5. Identify Recurring Issue Pattern

**Scenario**: Temperature spikes happen every 6 hours

**Natural Language Query:**
```
"Show me Kiln 6 temperature for the past week to find patterns"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="last week",
     end_time="now"
   )
```

**Analysis**: Look for periodic spikes indicating potential root cause

---

### 6. Compare Historical vs Recent Performance

**Scenario**: Is current efficiency lower than last month?

**Natural Language Query:**
```
"Compare Kiln 6 temperature: last week average vs last minute value"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="last week",
     end_time="now"
   )
2. Calculate:
   - Last week average
   - Last minute current value
   - Percentage difference
```

**Example Response:**
```json
{
  "last_week_average": 855.2,
  "current_value": 892.1,
  "difference_percent": 4.3,
  "assessment": "Current temperature 4.3% higher than last week average"
}
```

---

## Optimization Use Cases

### 7. Find Optimal Operating Setpoint

**Scenario**: Determine best temperature for energy efficiency

**Natural Language Query:**
```
"When was Kiln 6 most efficient in the past month?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="last 30 days",
     end_time="now"
   )
2. read_timeseries(
     tag_name="Kiln6.EnergyConsumption",
     start_time="last 30 days",
     end_time="now"
   )
3. Correlate temperature with energy usage
```

**Analysis**: Identify temperature range with lowest energy/ton

---

### 8. Detect Energy Waste

**Scenario**: Find periods of excessive energy consumption

**Natural Language Query:**
```
"Show me when Kiln 6 energy usage was above 1000 kW today"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.PowerConsumption",
     start_time="today",
     end_time="now"
   )
2. Filter for values > 1000
```

**Actionable Insight**: Identify improvement opportunities

---

### 9. Process Stability Analysis

**Scenario**: Measure temperature variability

**Natural Language Query:**
```
"How stable was Kiln 6 temperature over the past 24 hours?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="past 24 hours",
     end_time="now"
   )
2. Calculate:
   - Standard deviation
   - Min/max range
   - Number of excursions outside normal range
```

---

## Reporting Use Cases

### 10. Daily Production Report

**Scenario**: Generate morning report for plant manager

**Natural Language Query:**
```
"Summarize Kiln 6 performance from yesterday"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="yesterday",
     end_time="yesterday 23:59"
   )
2. read_timeseries(
     tag_name="Kiln6.Production",
     start_time="yesterday",
     end_time="yesterday 23:59"
   )
3. Calculate:
   - Average temperature
   - Total production
   - Uptime percentage
   - Quality metrics
```

---

### 11. Compliance Reporting

**Scenario**: Generate emissions report for regulators

**Natural Language Query:**
```
"What were the average emissions from Kiln 6 last month?"
```

**MCP Tool Calls:**
```
1. search_tags(search_pattern="Kiln6*Emissions*")
2. For each emissions tag:
   read_timeseries(
     tag_name=<tag>,
     start_time="last month",
     end_time="now"
   )
```

---

### 12. Shift Handover Report

**Scenario**: Summarize 8-hour shift for next operator

**Natural Language Query:**
```
"What should the next shift know about Kiln 6?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.*",
     start_time="8 hours ago",
     end_time="now"
   )
2. Identify:
   - Any alarms or events
   - Current operating conditions
   - Trends (increasing/decreasing)
```

---

## Integration Examples

### 13. Trigger Maintenance Alert

**Scenario**: Bearing temperature exceeds threshold

**Natural Language Query:**
```
"Is the Kiln 6 bearing temperature above 80°C?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Bearing.Temperature",
     start_time="past 1 hour",
     end_time="now"
   )
2. If any value > 80°C:
   - Alert maintenance team
   - Log incident
   - Recommend action
```

**Integration**: Connect to ticketing system

---

### 14. Predictive Maintenance

**Scenario**: Detect early signs of equipment degradation

**Natural Language Query:**
```
"Show me vibration trends for Kiln 6 motor over the past month"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Motor.Vibration",
     start_time="last 30 days",
     end_time="now"
   )
2. Trend analysis:
   - Increasing trend → Schedule inspection
   - Stable → Continue monitoring
   - Spikes → Immediate investigation
```

---

### 15. Energy Management Integration

**Scenario**: Coordinate with energy management system

**Natural Language Query:**
```
"Can we reduce Kiln 6 power during peak demand hours?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.PowerDemand",
     start_time="past 24 hours",
     end_time="now"
   )
2. Identify:
   - Baseline power requirement
   - Flexible load potential
   - Impact on production
```

---

## Advanced Query Patterns

### 16. Multi-Tag Correlation

**Natural Language Query:**
```
"How does feed rate affect Kiln 6 temperature?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.FeedRate",
     start_time="last week",
     end_time="now"
   )
2. read_timeseries(
     tag_name="Kiln6.Temperature",
     start_time="last week",
     end_time="now"
   )
3. Statistical correlation analysis
```

---

### 17. Batch Comparison

**Natural Language Query:**
```
"Compare this batch to the last 10 batches"
```

**MCP Tool Calls:**
```
1. search_tags(search_pattern="Kiln6.Batch*")
2. For current and last 10 batches:
   read_timeseries(tag_name=<batch_id>, ...)
3. Compare:
   - Cycle time
   - Energy consumption
   - Quality metrics
```

---

### 18. Root Cause Analysis

**Natural Language Query:**
```
"What caused the quality issue at 14:30 today?"
```

**MCP Tool Calls:**
```
1. Get all process variables at 14:30 ± 15 minutes
2. Identify which variables were outside normal range
3. Check if any alarms were active
4. Review operator actions
```

---

### 19. Site-Wide Dashboard Data

**Natural Language Query:**
```
"Show me current status of all kilns at Maceira plant"
```

**MCP Tool Calls:**
```
1. list_namespaces() → Get all kilns
2. For each kiln:
   get_tag_metadata(<kiln>.Status)
   read_timeseries(<kiln>.*, start="now", end="now")
```

---

### 20. Historical Baseline Comparison

**Natural Language Query:**
```
"Is today's performance normal compared to the last 30 days?"
```

**MCP Tool Calls:**
```
1. read_timeseries(
     tag_name="Kiln6.Efficiency",
     start_time="last 30 days",
     end_time="yesterday"
   ) → Calculate baseline
2. read_timeseries(
     tag_name="Kiln6.Efficiency",
     start_time="today",
     end_time="now"
   ) → Current performance
3. Statistical comparison
```

---

## Best Practices for Query Construction

### DO:
✅ Use natural language time expressions ("past 24 hours")
✅ Start with search_tags to discover available data
✅ Get metadata before querying timeseries
✅ Leverage caching for repeated queries
✅ Check quality flags in timeseries data

### DON'T:
❌ Query years of data without pagination
❌ Bypass cache unnecessarily
❌ Ignore error messages
❌ Use ambiguous time ranges
❌ Query tags that don't exist (search first!)

---

## Query Templates

### Template: Sensor Validation
```
1. get_tag_metadata(<tag>) → Verify units, ranges
2. read_timeseries(<tag>, "past 1 hour", "now") → Check current behavior
3. Compare to expected range → Validate
```

### Template: Performance Analysis
```
1. search_tags(<pattern>) → Find relevant metrics
2. read_timeseries(<metric>, "last week", "now") → Get historical data
3. Calculate statistics → Analyze performance
```

### Template: Anomaly Investigation
```
1. read_timeseries(<tag>, <anomaly_time - 1h>, <anomaly_time + 1h>)
2. Identify deviations from normal
3. Check correlated tags
4. Generate report
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Too Much Data
**Problem**: Querying years of data crashes the system
**Solution**: Use appropriate time ranges, implement pagination

### Pitfall 2: Wrong Tag Names
**Problem**: Querying non-existent tags
**Solution**: Always search_tags first to verify names

### Pitfall 3: Ignoring Cache
**Problem**: Slow queries for repeated data
**Solution**: Let cache work, only bypass when fresh data needed

### Pitfall 4: Missing Context
**Problem**: Data without units or description
**Solution**: Use get_tag_metadata to understand data

---

## Next Steps

1. **Start Simple**: Try examples 1-5 (Validation use cases)
2. **Progress to Troubleshooting**: Examples 6-9
3. **Advanced Analytics**: Examples 13-20
4. **Build Custom Queries**: Adapt templates to your needs

---

*For more information, see:*
- [API Documentation](./API.md)
- [Troubleshooting Guide](./troubleshooting/CANARY_API_DIAGNOSIS.md)
- [Multi-Site Configuration](./multi-site-config.md)

*Last Updated: Story 2.7 Implementation*
