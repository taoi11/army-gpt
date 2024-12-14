## Usage

### Basic
```python
import requests
import json

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
  },
  data=json.dumps({
    "model": "openai/gpt-3.5-turbo", # Optional
    "messages": [
      {
        "role": "user",
        "content": "What is the meaning of life?"
      }
    ]
    
  })
)
```

### Error Handling

```typescript
type ErrorResponse = {
  error: {
    code: number;
    message: string;
    metadata?: Record<string, unknown>;
  };
};
```
```
Error Codes
400: Bad Request (invalid or missing params, CORS)
401: Invalid credentials (OAuth session expired, disabled/invalid API key)
402: Your account or API key has insufficient credits. Add more credits and retry the request.
403: Your chosen model requires moderation and your input was flagged
408: Your request timed out
429: You are being rate limited
502: Your chosen model is down or we received an invalid response from it
503: There is no available model provider that meets your routing requirements
```
### Structured Output
```typescript
const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    Authorization: 'Bearer YOUR_API_KEY',
    'HTTP-Referer': 'https://your-app.com',
  },
  body: JSON.stringify({
    model: 'openai/gpt-4',
    messages: [
      { role: 'user', content: 'What is the weather like in London?' },
    ],
    response_format: {
      type: 'json_schema',
      json_schema: {
        name: 'weather',
        strict: true,
        schema: {
          type: 'object',
          properties: {
            location: {
              type: 'string',
              description: 'City or location name',
            },
            temperature: {
              type: 'number',
              description: 'Temperature in Celsius',
            },
            conditions: {
              type: 'string',
              description: 'Weather conditions description',
            },
          },
          required: ['location', 'temperature', 'conditions'],
          additionalProperties: false,
        },
      },
    },
  }),
});

const data = await response.json();
const weatherInfo = data.choices[0].message.content;
```

### Get Generation
```
https://openrouter.ai/api/v1/generation?id=gen-######
{"data":
  {"id":
    "gen-#####",
    "upstream_id":"chatcmpl-#####",
    "total_cost":0.0001525,
    "cache_discount":null,
    "provider_name":"OpenAI",
    "created_at":"2024-12-13T23:07:14.87033+00:00",
    "model":"openai/gpt-3.5-turbo",
    "app_id":null,"streamed":true,
    "cancelled":false,"latency":280,
    "moderation_latency":246,
    "generation_time":786,
    "finish_reason":"stop",
    "tokens_prompt":14,
    "tokens_completion":97,
    "native_tokens_prompt":14,
    "native_tokens_completion":97,
    "native_tokens_reasoning":null,
    "num_media_prompt":null,
    "num_media_completion":null,
    "origin":"",
    "usage":0.0001525
  }
}

```