# MCP Weather Tool Definition

## Tool: get_weather

### Description

Get current weather and forecast for a location.

### Parameters

```json
{
  "location": "string (required)",
  "unit": "celsius | fahrenheit (default: celsius)",
  "forecast_days": "1-7 (default: 1)"
}
```

### Returns

```json
{
  "location": "string",
  "temperature": 22.5,
  "condition": "sunny | cloudy | rainy | snowy",
  "humidity": 65,
  "forecast": [
    {"day": 1, "high": 25, "low": 18, "condition": "sunny"}
  ]
}
```

### Example

```
Input: {"location": "北京", "forecast_days": 3}
Output: {"location": "北京", "temperature": 22, "condition": "sunny", "forecast": [...]}
```
