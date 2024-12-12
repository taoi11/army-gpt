# Army-GPT

Collection of AI tools and agents for army personnel.

## Project Structure

```
.
├── src/
│   ├── frontend/      # Frontend static files
│   ├── backend/       # FastAPI backend
│   ├── data/          # Data storage
│   ├── policies/      # Policy documents
│   └── prompts/       # LLM prompts
├── tests/             # Test files
├── .env.example       # Environment variables template
├── Dockerfile         # Docker configuration
└── requirements.txt   # Python dependencies
```

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your values
3. Build and run with Docker:

```bash
docker build -t army-gpt .
docker run -p 8020:8020 --env-file .env army-gpt
```

## Development

To run locally for development:

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn src.backend.main:app --reload --port 8020
```

## Features

- Pace Notes Generator
- Policy Foo (Coming Soon)
- More tools coming soon...

## Security & Privacy

- User messages are not logged
- User identifiable data is not stored
- All sensitive data is handled client-side
- Basic metrics collection for service improvement

## License

All rights reserved.