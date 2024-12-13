curl https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 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" \
  -d '{
  "model": "openai/gpt-3.5-turbo",
  "messages": [
    {
      "role": "user",
      "content": "What is the meaning of life?"
    }
  ]
}'

         
{"id":
  "gen-1734131233-78GJv2r8OwSeHUSP6mEw",
  "provider":"OpenAI",
  model":"openai/gpt-3.5-turbo",
  "object":"chat.completion",
  "created":1734131233,
  "choices":[
    {
      "logprobs":null,
      "finish_reason":"stop",
      "index":0,
      "message":{
        "role":"assistant",
        "content":"The meaning of life is a deeply philosophical question that has been pondered by philosophers, theologians, and individuals throughout history. Different cultures, religions, and belief systems offer varying perspectives on the meaning of life. Some believe that the meaning of life is to seek happiness, fulfillment, or spiritual enlightenment, while others believe that it is to fulfill a divine purpose or destiny. Ultimately, the meaning of life may be a subjective and personal question that each individual must discover and interpret for themselves.",
        "refusal":""
      }
    }
  ],
  "system_fingerprint":null,
  "usage":{"prompt_tokens":14,"completion_tokens":97,"total_tokens":111}
}


