# MCP Traffic Tool Definition

## Tool: get_traffic

### Description

Get real-time traffic conditions and route analysis.

### Parameters

```json
{
  "origin": "string (required)",
  "destination": "string (required)",
  "departure_time": "ISO datetime (optional)"
}
```

### Returns

```json
{
  "route": {
    "distance_km": 25.5,
    "duration_minutes": 45,
    "traffic_level": "light | moderate | heavy"
  },
  "incidents": [
    {"type": "accident | construction | closure", "location": "string", "delay_minutes": 10}
  ],
  "alternatives": [
    {"route_id": "alt1", "distance_km": 28, "duration_minutes": 50, "traffic_level": "light"}
  ]
}
```
