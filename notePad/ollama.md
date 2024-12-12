# Ollama Python Library

## Prerequisites
- Install and run [Ollama](https://ollama.com/download)
- Pull a model: `ollama pull <model>` e.g., `ollama pull llama3.2`

## Install
```sh
pip install ollama
```

## Usage
### Basic Chat
```python
from ollama import chat

response = chat(model='llama3.2', messages=[
  {'role': 'user', 'content': 'Why is the sky blue?'}
])
print(response.message.content)
```

### Streaming Responses
```python
from ollama import chat

stream = chat(
    model='llama3.2',
    messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
    stream=True,
)

for chunk in stream:
  print(chunk['message']['content'], end='', flush=True)
```

### Custom Client
```python
from ollama import Client

client = Client(
  host='http://localhost:11434',
  headers={'x-some-header': 'some-value'}
)

response = client.chat(model='llama3.2', messages=[
  {'role': 'user', 'content': 'Why is the sky blue?'}
])
```

### Async Client
```python
import asyncio
from ollama import AsyncClient

async def chat():
    message = {'role': 'user', 'content': 'Why is the sky blue?'}
    response = await AsyncClient().chat(model='llama3.2', messages=[message])
    print(response.message.content)

asyncio.run(chat())
```

### Async Streaming
```python
import asyncio
from ollama import AsyncClient

async def chat():
    message = {'role': 'user', 'content': 'Why is the sky blue?'}
    async for part in await AsyncClient().chat(model='llama3.2', messages=[message], stream=True):
        print(part['message']['content'], end='', flush=True)

asyncio.run(chat())
```

## API
### Chat
```python
chat(model='llama3.2', messages=[{'role': 'user', 'content': 'Why is the sky blue?'}])
```

### Generate
```python
generate(model='llama3.2', prompt='Why is the sky blue?')
```

### List Models
```python
list()
```

### Show Model Info
```python
show('llama3.2')
```

### Create Model
```python
modelfile='''
FROM llama3.2
SYSTEM You are mario from super mario bros.
'''

create(model='example', modelfile=modelfile)
```

### Copy Model
```python
copy('llama3.2', 'user/llama3.2')
```

### Delete Model
```python
delete('llama3.2')
```

### Pull Model
```python
pull('llama3.2')
```

### Push Model
```python
push('user/llama3.2')
```

### Embed Text
```python
embed(model='llama3.2', input='The sky is blue because of rayleigh scattering')
```

### Embed Batch
```python
embed(model='llama3.2', input=['The sky is blue because of rayleigh scattering', 'Grass is green because of chlorophyll'])
```

### List Running Models
```python
ps()
```

## Error Handling
```python
from ollama import ResponseError

try:
    chat(model='does-not-yet-exist')
except ResponseError as e:
    print('Error:', e.error)
    if e.status_code == 404:
        pull(model)
```