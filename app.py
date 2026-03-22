"""
LLM Arena - Compare and compete different LLMs
Enhanced version with rating system, templates, export, and more
"""
import os
import json
import time
import asyncio
import aiohttp
import csv
import io
import uuid
import hashlib
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, send_file
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import sqlite3
from contextlib import contextmanager
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Database setup
DATABASE = 'llm_arena.db'

@contextmanager
def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database tables"""
    with get_db() as conn:
        # API Keys table (encrypted storage placeholder)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                provider TEXT PRIMARY KEY,
                api_key TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Competitions table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS competitions (
                id TEXT PRIMARY KEY,
                prompt TEXT NOT NULL,
                template_id TEXT,
                blind_mode BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Results table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS results (
                id TEXT PRIMARY KEY,
                competition_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                model TEXT NOT NULL,
                response TEXT,
                elapsed REAL,
                tokens TEXT,
                success BOOLEAN,
                error TEXT,
                rank INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (competition_id) REFERENCES competitions(id)
            )
        ''')
        
        # Ratings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id TEXT PRIMARY KEY,
                result_id TEXT NOT NULL,
                competition_id TEXT NOT NULL,
                criterion TEXT NOT NULL,
                score INTEGER NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (result_id) REFERENCES results(id),
                FOREIGN KEY (competition_id) REFERENCES competitions(id)
            )
        ''')
        
        # Custom rating criteria table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS rating_criteria (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                weight REAL DEFAULT 1.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Templates table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                prompt TEXT NOT NULL,
                description TEXT,
                variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

# Initialize database on startup
init_db()

# Default rating criteria
DEFAULT_CRITERIA = [
    {'id': 'accuracy', 'name': 'Accuracy', 'description': 'How accurate and correct is the response?', 'weight': 1.0},
    {'id': 'clarity', 'name': 'Clarity', 'description': 'How clear and easy to understand is the response?', 'weight': 0.8},
    {'id': 'completeness', 'name': 'Completeness', 'description': 'Does it fully address the prompt?', 'weight': 0.9},
    {'id': 'usefulness', 'name': 'Usefulness', 'description': 'How useful is this for your specific task?', 'weight': 1.0},
    {'id': 'speed', 'name': 'Speed', 'description': 'Response time (auto-rated)', 'weight': 0.5}
]

# Default templates
DEFAULT_TEMPLATES = [
    {
        'id': 'trading-analysis',
        'name': 'Trading Analysis',
        'category': 'Finance',
        'prompt': 'Analyze the following market data and provide trading recommendations:\n\n{input}\n\nConsider:\n1. Current trend analysis\n2. Support and resistance levels\n3. Risk assessment\n4. Entry/exit points\n5. Position sizing recommendations',
        'description': 'Analyze market data for trading decisions'
    },
    {
        'id': 'code-review',
        'name': 'Code Review',
        'category': 'Programming',
        'prompt': 'Review the following code and provide:\n\n```\n{input}\n```\n\nPlease analyze:\n1. Code quality and readability\n2. Potential bugs or issues\n3. Performance considerations\n4. Security vulnerabilities\n5. Suggested improvements',
        'description': 'Review code for quality and issues'
    },
    {
        'id': 'code-generation',
        'name': 'Code Generation',
        'category': 'Programming',
        'prompt': 'Write a {language} function that:\n\n{input}\n\nRequirements:\n- Clean, readable code\n- Proper error handling\n- Include docstrings\n- Follow best practices',
        'description': 'Generate code from requirements',
        'variables': ['language', 'input']
    },
    {
        'id': 'math-problem',
        'name': 'Math Problem',
        'category': 'Mathematics',
        'prompt': 'Solve the following math problem step by step:\n\n{input}\n\nShow all work and explain your reasoning.',
        'description': 'Solve mathematical problems with steps'
    },
    {
        'id': 'data-analysis',
        'name': 'Data Analysis',
        'category': 'Data Science',
        'prompt': 'Analyze the following data and provide insights:\n\n{input}\n\nPlease include:\n1. Key statistics\n2. Trends and patterns\n3. Anomalies or outliers\n4. Recommendations\n5. Visualization suggestions',
        'description': 'Analyze data and extract insights'
    },
    {
        'id': 'writing-task',
        'name': 'Writing Task',
        'category': 'Writing',
        'prompt': 'Write a {style} piece about:\n\n{input}\n\nRequirements:\n- {length} words approximately\n- Target audience: {audience}\n- Tone: {tone}',
        'description': 'Generate written content',
        'variables': ['style', 'input', 'length', 'audience', 'tone']
    },
    {
        'id': 'debugging',
        'name': 'Debug Code',
        'category': 'Programming',
        'prompt': 'Debug the following code that has an issue:\n\n```\n{input}\n```\n\nError message or unexpected behavior:\n{error}\n\nPlease:\n1. Identify the bug\n2. Explain why it happens\n3. Provide the fixed code\n4. Suggest how to prevent similar issues',
        'description': 'Debug code with error messages',
        'variables': ['input', 'error']
    },
    {
        'id': 'api-design',
        'name': 'API Design',
        'category': 'Programming',
        'prompt': 'Design an API for the following requirements:\n\n{input}\n\nProvide:\n1. Endpoint structure\n2. Request/Response schemas\n3. Authentication method\n4. Error handling\n5. Example requests',
        'description': 'Design RESTful APIs'
    },
    {
        'id': 'sql-query',
        'name': 'SQL Query',
        'category': 'Data',
        'prompt': 'Write a SQL query for the following requirement:\n\n{input}\n\nSchema:\n{schema}\n\nProvide:\n1. The SQL query\n2. Explanation of how it works\n3. Performance considerations',
        'description': 'Generate SQL queries',
        'variables': ['input', 'schema']
    },
    {
        'id': 'explanation',
        'name': 'Concept Explanation',
        'category': 'Education',
        'prompt': 'Explain the following concept in simple terms:\n\n{input}\n\nTarget audience: {audience}\n\nInclude:\n1. Simple definition\n2. Real-world examples\n3. Common misconceptions\n4. Practical applications',
        'description': 'Explain complex concepts simply',
        'variables': ['input', 'audience']
    }
]

def seed_default_data():
    """Seed default criteria and templates"""
    with get_db() as conn:
        # Check if criteria exist
        existing = conn.execute('SELECT COUNT(*) FROM rating_criteria').fetchone()[0]
        if existing == 0:
            for criterion in DEFAULT_CRITERIA:
                conn.execute(
                    'INSERT INTO rating_criteria (id, name, description, weight) VALUES (?, ?, ?, ?)',
                    (criterion['id'], criterion['name'], criterion['description'], criterion['weight'])
                )
        
        # Check if templates exist
        existing = conn.execute('SELECT COUNT(*) FROM templates').fetchone()[0]
        if existing == 0:
            for template in DEFAULT_TEMPLATES:
                conn.execute(
                    'INSERT INTO templates (id, name, category, prompt, description, variables) VALUES (?, ?, ?, ?, ?, ?)',
                    (template['id'], template['name'], template['category'], template['prompt'], 
                     template.get('description', ''), json.dumps(template.get('variables', [])))
                )
        conn.commit()

seed_default_data()

# Available LLM providers (updated with more models)
LLM_PROVIDERS = {
    'openai': {
        'name': 'OpenAI',
        'models': ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo', 'o1-preview', 'o1-mini'],
        'default_model': 'gpt-4o'
    },
    'anthropic': {
        'name': 'Anthropic',
        'models': ['claude-3-5-sonnet-20241022', 'claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
        'default_model': 'claude-3-5-sonnet-20241022'
    },
    'google': {
        'name': 'Google',
        'models': ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro'],
        'default_model': 'gemini-1.5-pro'
    },
    'mistral': {
        'name': 'Mistral AI',
        'models': ['mistral-large-latest', 'mistral-small-latest', 'open-mixtral-8x22b', 'open-mistral-nemo'],
        'default_model': 'mistral-large-latest'
    },
    'cohere': {
        'name': 'Cohere',
        'models': ['command-r-plus-08-2024', 'command-r-08-2024', 'command'],
        'default_model': 'command-r-plus-08-2024'
    },
    'groq': {
        'name': 'Groq',
        'models': ['llama-3.3-70b-versatile', 'llama-3.1-70b-versatile', 'llama-3.1-8b-instant', 'mixtral-8x7b-32768'],
        'default_model': 'llama-3.3-70b-versatile'
    },
    'deepseek': {
        'name': 'DeepSeek',
        'models': ['deepseek-chat', 'deepseek-coder', 'deepseek-reasoner'],
        'default_model': 'deepseek-chat'
    },
    'xai': {
        'name': 'xAI',
        'models': ['grok-2-1212', 'grok-2-vision-1212', 'grok-beta'],
        'default_model': 'grok-2-1212'
    },
    'perplexity': {
        'name': 'Perplexity',
        'models': ['llama-3.1-sonar-large-128k-online', 'llama-3.1-sonar-small-128k-online'],
        'default_model': 'llama-3.1-sonar-large-128k-online'
    },
    'together': {
        'name': 'Together AI',
        'models': ['meta-llama/Llama-3.3-70B-Instruct-Turbo', 'mistralai/Mixtral-8x7B-Instruct-v0.1', 'Qwen/Qwen2.5-72B-Instruct-Turbo'],
        'default_model': 'meta-llama/Llama-3.3-70B-Instruct-Turbo'
    }
}

# Store competition history
competition_history = []

# API Key management
def load_api_keys():
    """Load API keys from database"""
    with get_db() as conn:
        rows = conn.execute('SELECT provider, api_key FROM api_keys').fetchall()
        return {row['provider']: row['api_key'] for row in rows}

def save_api_key(provider, api_key):
    """Save or update an API key"""
    with get_db() as conn:
        conn.execute('''
            INSERT INTO api_keys (provider, api_key, updated_at) 
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(provider) DO UPDATE SET api_key = ?, updated_at = CURRENT_TIMESTAMP
        ''', (provider, api_key, api_key))
        conn.commit()

def delete_api_key(provider):
    """Delete an API key"""
    with get_db() as conn:
        conn.execute('DELETE FROM api_keys WHERE provider = ?', (provider,))
        conn.commit()

# API call functions for each provider
async def call_openai(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call OpenAI API"""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_anthropic(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Anthropic API"""
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                content = result['content'][0]['text'] if result.get('content') else ''
                return {
                    'success': True,
                    'response': content,
                    'elapsed': elapsed,
                    'tokens': {'input': result.get('usage', {}).get('input_tokens', 0),
                              'output': result.get('usage', {}).get('output_tokens', 0)}
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_google(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Google Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 4096}
    }
    
    start_time = time.time()
    try:
        async with session.post(url, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return {'success': True, 'response': text, 'elapsed': elapsed}
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_mistral(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Mistral API"""
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_cohere(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Cohere API"""
    url = "https://api.cohere.ai/v2/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                content = result.get('message', {}).get('content', [{}])[0].get('text', '')
                return {
                    'success': True,
                    'response': content,
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_groq(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Groq API"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_deepseek(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call DeepSeek API"""
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_xai(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call xAI (Grok) API"""
    url = "https://api.x.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_perplexity(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Perplexity API"""
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

async def call_together(session, api_key: str, prompt: str, model: str) -> Dict[str, Any]:
    """Call Together AI API"""
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 4096
    }
    
    start_time = time.time()
    try:
        async with session.post(url, headers=headers, json=data, timeout=120) as response:
            result = await response.json()
            elapsed = time.time() - start_time
            
            if response.status == 200:
                return {
                    'success': True,
                    'response': result['choices'][0]['message']['content'],
                    'elapsed': elapsed,
                    'tokens': result.get('usage', {})
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', {}).get('message', 'Unknown error'),
                    'elapsed': elapsed
                }
    except asyncio.TimeoutError:
        return {'success': False, 'error': 'Request timeout', 'elapsed': time.time() - start_time}
    except Exception as e:
        return {'success': False, 'error': str(e), 'elapsed': time.time() - start_time}

# Provider call mapping
PROVIDER_CALLS = {
    'openai': call_openai,
    'anthropic': call_anthropic,
    'google': call_google,
    'mistral': call_mistral,
    'cohere': call_cohere,
    'groq': call_groq,
    'deepseek': call_deepseek,
    'xai': call_xai,
    'perplexity': call_perplexity,
    'together': call_together
}

async def run_competition(prompt: str, selected_providers: List[Dict], competition_id: str) -> List[Dict]:
    """Run competition between selected LLMs"""
    api_keys = load_api_keys()
    results = []
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for provider_config in selected_providers:
            provider = provider_config['provider']
            model = provider_config.get('model', LLM_PROVIDERS[provider]['default_model'])
            api_key = api_keys.get(provider, '')
            
            if api_key and provider in PROVIDER_CALLS:
                call_func = PROVIDER_CALLS[provider]
                tasks.append({
                    'provider': provider,
                    'model': model,
                    'task': call_func(session, api_key, prompt, model)
                })
        
        # Run all tasks concurrently
        for task_info in tasks:
            result = await task_info['task']
            result_id = str(uuid.uuid4())
            result_data = {
                'id': result_id,
                'competition_id': competition_id,
                'provider': task_info['provider'],
                'provider_name': LLM_PROVIDERS[task_info['provider']]['name'],
                'model': task_info['model'],
                **result
            }
            results.append(result_data)
            
            # Save result to database
            with get_db() as conn:
                conn.execute('''
                    INSERT INTO results (id, competition_id, provider, provider_name, model, 
                                        response, elapsed, tokens, success, error, rank)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                ''', (result_id, competition_id, task_info['provider'], 
                      LLM_PROVIDERS[task_info['provider']]['name'], task_info['model'],
                      result.get('response', ''), result.get('elapsed', 0),
                      json.dumps(result.get('tokens', {})), result.get('success', False),
                      result.get('error', '')))
                conn.commit()
    
    # Sort by elapsed time
    results.sort(key=lambda x: x.get('elapsed', float('inf')))
    
    # Assign ranks
    for i, result in enumerate(results):
        if result.get('success'):
            result['rank'] = i + 1
        else:
            result['rank'] = None
        
        # Update rank in database
        with get_db() as conn:
            conn.execute('UPDATE results SET rank = ? WHERE id = ?', 
                        (result['rank'], result['id']))
            conn.commit()
    
    return results

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', providers=LLM_PROVIDERS)

# ---------- Provider Routes ----------
@app.route('/api/providers', methods=['GET'])
def get_providers():
    """Get available LLM providers"""
    return jsonify(LLM_PROVIDERS)

# ---------- API Key Routes ----------
@app.route('/api/keys', methods=['GET'])
def get_keys():
    """Get configured API keys (masked)"""
    keys = load_api_keys()
    masked = {k: v[:8] + '...' + v[-4:] if len(v) > 12 else '****' for k, v in keys.items()}
    return jsonify(masked)

@app.route('/api/keys', methods=['POST'])
def set_keys():
    """Set API keys"""
    data = request.json
    for provider, api_key in data.items():
        if api_key and api_key.strip():
            save_api_key(provider, api_key.strip())
    return jsonify({'success': True, 'message': 'API keys saved'})

@app.route('/api/keys/<provider>', methods=['DELETE'])
def delete_key(provider):
    """Delete an API key"""
    delete_api_key(provider)
    return jsonify({'success': True})

# ---------- Competition Routes ----------
@app.route('/api/compete', methods=['POST'])
def compete():
    """Run a competition"""
    data = request.json
    prompt = data.get('prompt', '')
    selected_providers = data.get('providers', [])
    template_id = data.get('template_id')
    blind_mode = data.get('blind_mode', False)
    
    if not prompt:
        return jsonify({'error': 'Prompt is required'}), 400
    
    if not selected_providers:
        return jsonify({'error': 'At least one provider must be selected'}), 400
    
    # Create competition record
    competition_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute('''
            INSERT INTO competitions (id, prompt, template_id, blind_mode)
            VALUES (?, ?, ?, ?)
        ''', (competition_id, prompt, template_id, blind_mode))
        conn.commit()
    
    # Run competition
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(run_competition(prompt, selected_providers, competition_id))
    loop.close()
    
    # For blind mode, hide provider names
    if blind_mode:
        for result in results:
            result['provider_name_hidden'] = f'Model {chr(65 + results.index(result))}'
            result['provider_hidden'] = result['provider']
            result['model_hidden'] = result['model']
            del result['provider']
            del result['model']
            del result['provider_name']
    
    return jsonify({
        'competition_id': competition_id,
        'prompt': prompt,
        'results': results,
        'blind_mode': blind_mode,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/competitions', methods=['GET'])
def get_competitions():
    """Get all competitions"""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT c.id, c.prompt, c.template_id, c.blind_mode, c.created_at,
                   COUNT(r.id) as result_count
            FROM competitions c
            LEFT JOIN results r ON c.id = r.competition_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT 100
        ''').fetchall()
        
        competitions = []
        for row in rows:
            comp = dict(row)
            # Get results for this competition
            results = conn.execute('''
                SELECT id, provider, provider_name, model, elapsed, success, error, rank
                FROM results WHERE competition_id = ?
                ORDER BY rank NULLS LAST, elapsed
            ''', (row['id'],)).fetchall()
            comp['results'] = [dict(r) for r in results]
            competitions.append(comp)
        
        return jsonify(competitions)

@app.route('/api/competitions/<competition_id>', methods=['GET'])
def get_competition(competition_id):
    """Get a specific competition with full results"""
    with get_db() as conn:
        comp = conn.execute('SELECT * FROM competitions WHERE id = ?', (competition_id,)).fetchone()
        if not comp:
            return jsonify({'error': 'Competition not found'}), 404
        
        results = conn.execute('''
            SELECT r.*, 
                   GROUP_CONCAT(
                       json_object('criterion', rat.criterion, 'score', rat.score, 'notes', rat.notes)
                   ) as ratings
            FROM results r
            LEFT JOIN ratings rat ON r.id = rat.result_id
            WHERE r.competition_id = ?
            GROUP BY r.id
            ORDER BY r.rank NULLS LAST, r.elapsed
        ''', (competition_id,)).fetchall()
        
        comp_dict = dict(comp)
        comp_dict['results'] = []
        for r in results:
            result = dict(r)
            if result.get('ratings'):
                try:
                    result['ratings'] = [json.loads(rat) for rat in result['ratings'].split(',')]
                except:
                    result['ratings'] = []
            else:
                result['ratings'] = []
            comp_dict['results'].append(result)
        
        return jsonify(comp_dict)

@app.route('/api/competitions/<competition_id>', methods=['DELETE'])
def delete_competition(competition_id):
    """Delete a competition and its results"""
    with get_db() as conn:
        conn.execute('DELETE FROM ratings WHERE competition_id = ?', (competition_id,))
        conn.execute('DELETE FROM results WHERE competition_id = ?', (competition_id,))
        conn.execute('DELETE FROM competitions WHERE id = ?', (competition_id,))
        conn.commit()
    return jsonify({'success': True})

# ---------- Rating Routes ----------
@app.route('/api/ratings', methods=['POST'])
def save_rating():
    """Save a rating for a result"""
    data = request.json
    result_id = data.get('result_id')
    competition_id = data.get('competition_id')
    criterion = data.get('criterion')
    score = data.get('score')
    notes = data.get('notes', '')
    
    if not all([result_id, competition_id, criterion, score is not None]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    rating_id = str(uuid.uuid4())
    with get_db() as conn:
        conn.execute('''
            INSERT INTO ratings (id, result_id, competition_id, criterion, score, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (rating_id, result_id, competition_id, criterion, score, notes))
        conn.commit()
    
    return jsonify({'success': True, 'rating_id': rating_id})

@app.route('/api/ratings/bulk', methods=['POST'])
def save_ratings_bulk():
    """Save multiple ratings at once"""
    data = request.json
    ratings = data.get('ratings', [])
    
    with get_db() as conn:
        for rating in ratings:
            rating_id = str(uuid.uuid4())
            conn.execute('''
                INSERT INTO ratings (id, result_id, competition_id, criterion, score, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (rating_id, rating.get('result_id'), rating.get('competition_id'),
                  rating.get('criterion'), rating.get('score'), rating.get('notes', '')))
        conn.commit()
    
    return jsonify({'success': True, 'count': len(ratings)})

@app.route('/api/criteria', methods=['GET'])
def get_criteria():
    """Get all rating criteria"""
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM rating_criteria ORDER BY weight DESC').fetchall()
        return jsonify([dict(row) for row in rows])

@app.route('/api/criteria', methods=['POST'])
def add_criterion():
    """Add a new rating criterion"""
    data = request.json
    criterion_id = data.get('id') or str(uuid.uuid4())
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO rating_criteria (id, name, description, weight)
            VALUES (?, ?, ?, ?)
        ''', (criterion_id, data.get('name'), data.get('description', ''), data.get('weight', 1.0)))
        conn.commit()
    
    return jsonify({'success': True, 'id': criterion_id})

@app.route('/api/criteria/<criterion_id>', methods=['DELETE'])
def delete_criterion(criterion_id):
    """Delete a rating criterion"""
    with get_db() as conn:
        conn.execute('DELETE FROM rating_criteria WHERE id = ?', (criterion_id,))
        conn.execute('DELETE FROM ratings WHERE criterion = ?', (criterion_id,))
        conn.commit()
    return jsonify({'success': True})

# ---------- Template Routes ----------
@app.route('/api/templates', methods=['GET'])
def get_templates():
    """Get all templates"""
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM templates ORDER BY category, name').fetchall()
        templates = []
        for row in rows:
            t = dict(row)
            t['variables'] = json.loads(t['variables']) if t['variables'] else []
            templates.append(t)
        return jsonify(templates)

@app.route('/api/templates/categories', methods=['GET'])
def get_template_categories():
    """Get template categories"""
    with get_db() as conn:
        rows = conn.execute('SELECT DISTINCT category FROM templates ORDER BY category').fetchall()
        return jsonify([row['category'] for row in rows])

@app.route('/api/templates', methods=['POST'])
def add_template():
    """Add a new template"""
    data = request.json
    template_id = data.get('id') or str(uuid.uuid4())
    
    with get_db() as conn:
        conn.execute('''
            INSERT INTO templates (id, name, category, prompt, description, variables)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (template_id, data.get('name'), data.get('category'), data.get('prompt'),
              data.get('description', ''), json.dumps(data.get('variables', []))))
        conn.commit()
    
    return jsonify({'success': True, 'id': template_id})

@app.route('/api/templates/<template_id>', methods=['PUT'])
def update_template(template_id):
    """Update a template"""
    data = request.json
    with get_db() as conn:
        conn.execute('''
            UPDATE templates SET name = ?, category = ?, prompt = ?, description = ?, variables = ?
            WHERE id = ?
        ''', (data.get('name'), data.get('category'), data.get('prompt'),
              data.get('description', ''), json.dumps(data.get('variables', [])), template_id))
        conn.commit()
    return jsonify({'success': True})

@app.route('/api/templates/<template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a template"""
    with get_db() as conn:
        conn.execute('DELETE FROM templates WHERE id = ?', (template_id,))
        conn.commit()
    return jsonify({'success': True})

# ---------- Export Routes ----------
@app.route('/api/export/csv', methods=['POST'])
def export_csv():
    """Export competition results to CSV"""
    data = request.json
    competition_ids = data.get('competition_ids', [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Competition ID', 'Timestamp', 'Prompt', 'Provider', 'Model', 
                     'Success', 'Elapsed (s)', 'Rank', 'Response', 'Error'])
    
    with get_db() as conn:
        if competition_ids:
            placeholders = ','.join(['?' for _ in competition_ids])
            competitions = conn.execute(f'''
                SELECT c.id, c.prompt, c.created_at, r.provider, r.provider_name, r.model,
                       r.success, r.elapsed, r.rank, r.response, r.error
                FROM competitions c
                JOIN results r ON c.id = r.competition_id
                WHERE c.id IN ({placeholders})
                ORDER BY c.created_at DESC, r.rank
            ''', competition_ids).fetchall()
        else:
            competitions = conn.execute('''
                SELECT c.id, c.prompt, c.created_at, r.provider, r.provider_name, r.model,
                       r.success, r.elapsed, r.rank, r.response, r.error
                FROM competitions c
                JOIN results r ON c.id = r.competition_id
                ORDER BY c.created_at DESC, r.rank
            ''').fetchall()
        
        for row in competitions:
            writer.writerow([
                row['id'], row['created_at'], row['prompt'][:200],
                row['provider_name'], row['model'], row['success'],
                f"{row['elapsed']:.2f}" if row['elapsed'] else '',
                row['rank'] or '',
                row['response'][:500] if row['response'] else '',
                row['error'] or ''
            ])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment;filename=llm_arena_results.csv'}
    )

@app.route('/api/export/json', methods=['POST'])
def export_json():
    """Export competition results to JSON"""
    data = request.json
    competition_ids = data.get('competition_ids', [])
    
    with get_db() as conn:
        if competition_ids:
            placeholders = ','.join(['?' for _ in competition_ids])
            competitions = conn.execute(f'''
                SELECT * FROM competitions WHERE id IN ({placeholders})
                ORDER BY created_at DESC
            ''', competition_ids).fetchall()
        else:
            competitions = conn.execute('SELECT * FROM competitions ORDER BY created_at DESC LIMIT 100').fetchall()
        
        result = []
        for comp in competitions:
            comp_dict = dict(comp)
            results = conn.execute('SELECT * FROM results WHERE competition_id = ? ORDER BY rank', 
                                  (comp['id'],)).fetchall()
            comp_dict['results'] = [dict(r) for r in results]
            
            # Get ratings for each result
            for r in comp_dict['results']:
                ratings = conn.execute('SELECT * FROM ratings WHERE result_id = ?', (r['id'],)).fetchall()
                r['ratings'] = [dict(rat) for rat in ratings]
            
            result.append(comp_dict)
    
    return Response(
        json.dumps(result, indent=2),
        mimetype='application/json',
        headers={'Content-Disposition': 'attachment;filename=llm_arena_results.json'}
    )

# ---------- Leaderboard Routes ----------
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get overall leaderboard with ratings"""
    with get_db() as conn:
        # Get stats per provider/model
        rows = conn.execute('''
            SELECT 
                provider,
                provider_name,
                model,
                COUNT(*) as total_competitions,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) as wins,
                AVG(CASE WHEN success = 1 THEN elapsed END) as avg_time,
                MIN(CASE WHEN success = 1 THEN elapsed END) as best_time
            FROM results
            GROUP BY provider, model
            ORDER BY wins DESC, avg_time ASC
        ''').fetchall()
        
        leaderboard = []
        for row in rows:
            entry = dict(row)
            
            # Get average ratings for this provider/model
            ratings = conn.execute('''
                SELECT rat.criterion, AVG(rat.score) as avg_score, rc.weight
                FROM ratings rat
                JOIN results r ON rat.result_id = r.id
                JOIN rating_criteria rc ON rat.criterion = rc.id
                WHERE r.provider = ? AND r.model = ?
                GROUP BY rat.criterion
            ''', (row['provider'], row['model'])).fetchall()
            
            entry['avg_ratings'] = {r['criterion']: round(r['avg_score'], 2) for r in ratings}
            
            # Calculate weighted score
            total_weight = sum(r['weight'] for r in ratings) or 1
            weighted_score = sum(r['avg_score'] * r['weight'] for r in ratings) / total_weight
            entry['weighted_score'] = round(weighted_score, 2) if ratings else None
            
            leaderboard.append(entry)
        
        return jsonify(leaderboard)

@app.route('/api/leaderboard/by-criterion/<criterion>', methods=['GET'])
def get_leaderboard_by_criterion(criterion):
    """Get leaderboard for a specific criterion"""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT 
                r.provider,
                r.provider_name,
                r.model,
                AVG(rat.score) as avg_score,
                COUNT(rat.id) as rating_count
            FROM ratings rat
            JOIN results r ON rat.result_id = r.id
            WHERE rat.criterion = ?
            GROUP BY r.provider, r.model
            HAVING rating_count > 0
            ORDER BY avg_score DESC
        ''', (criterion,)).fetchall()
        
        return jsonify([dict(row) for row in rows])

# ---------- History Route ----------
@app.route('/api/history', methods=['GET'])
def get_history():
    """Get competition history (for backwards compatibility)"""
    with get_db() as conn:
        rows = conn.execute('''
            SELECT c.id, c.prompt, c.created_at as timestamp,
                   json_group_array(
                       json_object('provider', r.provider, 'provider_name', r.provider_name,
                                  'model', r.model, 'success', r.success, 'elapsed', r.elapsed,
                                  'rank', r.rank)
                   ) as results
            FROM competitions c
            LEFT JOIN results r ON c.id = r.competition_id
            GROUP BY c.id
            ORDER BY c.created_at DESC
            LIMIT 100
        ''').fetchall()
        
        history = []
        for row in rows:
            item = {'id': row['id'], 'prompt': row['prompt'], 'timestamp': row['timestamp']}
            try:
                item['results'] = json.loads(row['results'])
            except:
                item['results'] = []
            history.append(item)
        
        return jsonify(history)

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear all history"""
    with get_db() as conn:
        conn.execute('DELETE FROM ratings')
        conn.execute('DELETE FROM results')
        conn.execute('DELETE FROM competitions')
        conn.commit()
    return jsonify({'success': True})

# ---------- Reveal Blind Mode ----------
@app.route('/api/competitions/<competition_id>/reveal', methods=['POST'])
def reveal_blind(competition_id):
    """Reveal provider names in blind mode"""
    with get_db() as conn:
        comp = conn.execute('SELECT blind_mode FROM competitions WHERE id = ?', (competition_id,)).fetchone()
        if not comp:
            return jsonify({'error': 'Competition not found'}), 404
        
        conn.execute('UPDATE competitions SET blind_mode = 0 WHERE id = ?', (competition_id,))
        conn.commit()
        
        results = conn.execute('''
            SELECT id, provider, provider_name, model, elapsed, success, rank
            FROM results WHERE competition_id = ?
            ORDER BY rank NULLS LAST, elapsed
        ''', (competition_id,)).fetchall()
        
        return jsonify({
            'success': True,
            'results': [dict(r) for r in results]
        })

# ---------- Stats Routes ----------
@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    with get_db() as conn:
        stats = {
            'total_competitions': conn.execute('SELECT COUNT(*) FROM competitions').fetchone()[0],
            'total_results': conn.execute('SELECT COUNT(*) FROM results').fetchone()[0],
            'successful_results': conn.execute('SELECT COUNT(*) FROM results WHERE success = 1').fetchone()[0],
            'total_ratings': conn.execute('SELECT COUNT(*) FROM ratings').fetchone()[0],
            'providers_configured': conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0],
            'templates_available': conn.execute('SELECT COUNT(*) FROM templates').fetchone()[0],
        }
        
        # Top performers
        stats['top_by_wins'] = [
            dict(row) for row in conn.execute('''
                SELECT provider_name, model, COUNT(*) as wins
                FROM results WHERE rank = 1
                GROUP BY provider, model
                ORDER BY wins DESC LIMIT 5
            ''').fetchall()
        ]
        
        stats['top_by_speed'] = [
            dict(row) for row in conn.execute('''
                SELECT provider_name, model, MIN(elapsed) as best_time
                FROM results WHERE success = 1
                GROUP BY provider, model
                ORDER BY best_time ASC LIMIT 5
            ''').fetchall()
        ]
        
        return jsonify(stats)

if __name__ == '__main__':
    app.run(debug=True, port=5001, host='0.0.0.0')
