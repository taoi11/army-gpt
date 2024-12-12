# Army-GPT

Collection of AI tools and agents for army personnel.

## Features

- **Pace Notes Generator**: AI-powered tool for creating and managing military pace notes
- **OpenRouter Integration**: Leverages OpenRouter API for LLM capabilities
- **Rate Limited API**: Built-in rate limiting for API protection
- **Docker Support**: Containerized for easy deployment

## Quick Start

### Prerequisites

- Docker
- Python 3.11+
- OpenRouter API key

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/army-gpt.git
cd army-gpt
```

2. Create `.env` file:
```bash
OPENROUTER_API_KEY=your_api_key_here
LLM_BASE_URL=https://openrouter.ai/api/v1
```

### Running with Docker

Build and run the container:
```bash
docker compose up --build
```

The application will be available at `http://localhost:8000`

### Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
uvicorn src.backend.main:app --reload
```

## Project Structure

```
army-gpt/
├── src/
│   ├── backend/
│   │   ├── llm/          # LLM integration
│   │   ├── pacenote/     # Pace notes logic
│   │   └── utils/        # Utilities
│   └── frontend/
│       └── templates/    # HTML templates
├── .appLogic/           # Project structure definitions
└── docker-compose.yml   # Docker configuration
```

## Contributing
Open a Pull Request

## License
