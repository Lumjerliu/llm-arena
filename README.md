# LLM Arena 🏆

A web application to compare and compete different Large Language Models (LLMs) for YOUR specific tasks. Find out which model works best for trading, coding, math, writing, and more!

![LLM Arena](https://img.shields.io/badge/LLM-Arena-blue)

## Features

- **Multi-LLM Competition**: Compare responses from 10+ LLM providers simultaneously
- **Real-time Racing**: All LLMs process your prompt concurrently
- **Blind Comparison Mode**: Hide model names until after you rate them to avoid bias
- **Custom Rating System**: Rate responses on Accuracy, Clarity, Completeness, Usefulness
- **Task Templates**: Pre-built prompts for trading, coding, math, writing, and more
- **Side-by-Side View**: Compare all responses in columns for easy comparison
- **Performance Metrics**: Track response time, token usage, and success rates
- **Leaderboard**: See which LLM performs best across all your competitions
- **Export Results**: Download results as CSV or JSON
- **History**: Review past competitions and their results
- **Persistent Storage**: All data saved in SQLite database

## Supported LLM Providers

| Provider | Models |
|----------|--------|
| **OpenAI** | GPT-4o, GPT-4o-mini, GPT-4 Turbo, GPT-4, GPT-3.5 Turbo, o1-preview, o1-mini |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku |
| **Google** | Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini Pro |
| **Mistral** | Mistral Large, Mistral Small, Mixtral 8x22B, Mistral Nemo |
| **Cohere** | Command R+, Command R |
| **Groq** | Llama 3.3 70B, Llama 3.1 70B/8B, Mixtral |
| **DeepSeek** | DeepSeek Chat, DeepSeek Coder, DeepSeek Reasoner |
| **xAI** | Grok 2, Grok 2 Vision |
| **Perplexity** | Sonar Large, Sonar Small |
| **Together AI** | Llama 3.3 70B, Mixtral, Qwen 2.5 72B |
| **Ollama (Free/Local)** | Llama 3.2, Phi-3, Mistral, Gemma2 (run locally, no API key) |

## Use Cases

### Trading & Finance
Test which model gives better trading analysis, market predictions, and risk assessments.

### Coding & Development
Compare code generation, debugging, and code review capabilities.

### Mathematics
Test problem-solving and step-by-step reasoning.

### Writing & Content
Compare creative writing, explanations, and content generation.

### Data Analysis
Test data interpretation and insight generation.

## Installation

1. Clone the repository:
```bash
cd llm-arena
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser to `http://localhost:5001`

## Configuration

### API Keys

1. Go to the **API Keys** tab (or Settings tab) in the application
2. Enter your API keys for the providers you want to use (Ollama does not require one)
3. Click **Save API Keys**

API keys are stored locally in SQLite database. For production, use environment variables.

**Free LLMs**: Ollama runs locally on your machine - no API key or payment required. See installation instructions below.

### Getting API Keys

- **OpenAI**: https://platform.openai.com/api-keys
- **Anthropic**: https://console.anthropic.com/
- **Google (Gemini)**: https://makersuite.google.com/app/apikey
- **Mistral**: https://console.mistral.ai/
- **Cohere**: https://dashboard.cohere.com/api-keys
- **Groq**: https://console.groq.com/keys
- **DeepSeek**: https://platform.deepseek.com/
- **xAI**: https://console.x.ai/
- **Perplexity**: https://www.perplexity.ai/settings/api
- **Together AI**: https://api.together.xyz/

### Ollama (Free Local)

1. Download from https://ollama.com
2. Run `ollama serve` in terminal
3. Pull a model: `ollama pull llama3.2`
4. Select Ollama in the Arena tab - no key needed!

## Usage

### Running a Competition

1. **Enter a Problem**: Type your question or problem in the text area
2. **Use a Template**: Click "Use Template" for pre-built prompts
3. **Enable Blind Mode**: Toggle to hide model names until you rate them
4. **Select Competitors**: Click on the LLM providers you want to compete
5. **Start Competition**: Click the "Start Competition" button
6. **View Results**: See which LLM responded fastest and compare their answers
7. **Rate Responses**: Give each response a score on different criteria
8. **Export**: Download results as CSV or JSON

### Blind Comparison Mode

Perfect for unbiased evaluation:
1. Enable "Blind Mode" toggle
2. Run competition - models are shown as "Model A", "Model B", etc.
3. Rate responses without knowing which model produced them
4. Click "Reveal Models" when done to see which was which

### Task Templates

Pre-built prompts for common tasks:
- **Trading Analysis**: Market data analysis and recommendations
- **Code Review**: Analyze code quality and issues
- **Code Generation**: Generate code from requirements
- **Math Problem**: Solve mathematical problems with steps
- **Data Analysis**: Extract insights from data
- **Debug Code**: Debug with error messages
- **API Design**: Design RESTful APIs
- **SQL Query**: Generate SQL queries
- **Concept Explanation**: Explain complex topics

### Leaderboard

The leaderboard tracks:
- **Wins**: Number of times an LLM was fastest
- **Avg Time**: Average response time
- **Success Rate**: Percentage of successful responses
- **Weighted Score**: Based on your ratings

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | Get available LLM providers |
| `/api/keys` | GET | Get configured API keys (masked) |
| `/api/keys` | POST | Save API keys |
| `/api/keys/<provider>` | DELETE | Delete an API key |
| `/api/compete` | POST | Run a competition |
| `/api/competitions` | GET | Get all competitions |
| `/api/competitions/<id>` | GET | Get specific competition |
| `/api/competitions/<id>/reveal` | POST | Reveal blind mode models |
| `/api/ratings` | POST | Save a rating |
| `/api/ratings/bulk` | POST | Save multiple ratings |
| `/api/criteria` | GET | Get rating criteria |
| `/api/templates` | GET | Get all templates |
| `/api/leaderboard` | GET | Get overall leaderboard |
| `/api/stats` | GET | Get statistics |
| `/api/export/csv` | POST | Export results as CSV |
| `/api/export/json` | POST | Export results as JSON |
| `/api/history` | GET | Get competition history |

## Project Structure

```
llm-arena/
├── app.py                 # Flask backend with LLM integrations
├── requirements.txt       # Python dependencies
├── render.yaml           # Render deployment config
├── Procfile              # Heroku/Render process file
├── runtime.txt           # Python version
├── llm_arena.db          # SQLite database (created on first run)
├── templates/
│   └── index.html        # Main HTML template
└── static/
    ├── css/
    │   └── style.css     # Application styles
    └── js/
        └── app.js        # Frontend JavaScript
```

## Security Notes

- API keys are stored locally. In production, use environment variables or a secure vault.
- Never commit the database file or API keys to version control.
- For production deployment, add authentication.

## Deployment

### Using Render

1. Push your code to GitHub
2. Connect your repository to Render
3. Render will automatically deploy using `render.yaml`

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["gunicorn", "app:app", "--host", "0.0.0.0", "--port", "5001"]
```

### Environment Variables

For production, set API keys via environment variables:

```bash
export OPENAI_API_KEY=your-key
export ANTHROPIC_API_KEY=your-key
# etc.
```

## Contributing

Feel free to submit issues and pull requests to add more LLM providers or improve the application!

## License

MIT License

## One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Lumjerliu/llm-arena)

Click the button above to deploy your own instance of LLM Arena!

