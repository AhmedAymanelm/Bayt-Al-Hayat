# Mental Health Assessment API

A FastAPI-based backend service for psychology and neuroscience assessments in mobile applications.

## Features

- Psychology assessment with 7 questions
- Neuroscience assessment with 9 questions (Fight/Flight/Freeze/Fawn patterns)
- No database required - all logic is server-side
- No AI dependencies
- Pydantic validation
- CORS enabled for mobile apps

## Project Structure

```
abrag/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── psychology.py          # Pydantic models
│   │   └── neuroscience.py        # Neuroscience models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── psychology.py          # Psychology endpoints
│   │   └── neuroscience.py        # Neuroscience endpoints
│   └── services/
│       ├── __init__.py
│       ├── psychology_service.py  # Psychology business logic
│       └── neuroscience_service.py # Neuroscience business logic
├── main.py                        # FastAPI main application
├── gradio_app.py                  # Gradio web interface
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
```

## Running

### FastAPI Server

```bash
uvicorn main:app --reload
```

Or:

```bash
python main.py
```

Server runs at: http://localhost:8000

### Gradio Interface

```bash
python gradio_app.py
```

### API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Endpoints

### Root

#### GET /
Returns API information and available endpoints.

#### GET /health
Health check endpoint.

---

### Psychology Assessment

#### GET /psychology

Returns the psychology questionnaire with 7 questions.

#### POST /psychology/submit

Submit answers and receive assessment result.

**Request Body:**
```json
{
  "answers": [1, 2, 3, 1, 2, 1, 2]
}
```

**Answer Requirements:**
- Must contain exactly 7 items
- Each value must be between 1 and 3

**Score Ranges:**

| Range | Level |
|-------|-------|
| 7-10 | Stable |
| 11-14 | Mild stress |
| 15-18 | Moderate disorder |
| 19-21 | High disorder |

---

### Neuroscience Assessment

#### GET /neuroscience/questions

Returns the neuroscience questionnaire with 9 questions.

#### POST /neuroscience/submit

Submit answers and receive neural pattern assessment.

**Request Body:**
```json
{
  "answers": ["A", "B", "A", "C", "D", "A", "B", "C", "A"]
}
```

**Answer Requirements:**
- Must contain exactly 9 items
- Each value must be "A", "B", "C", or "D"

**Pattern Mapping:**

| Option | Pattern |
|--------|---------|
| A | Fight |
| B | Flight |
| C | Freeze |
| D | Fawn |

**Special Cases:**

1. **Tie:** dominant becomes "Mixed Fight/Flight"
2. **Strong Secondary:** If difference <= 1, strong_secondary = true

---

## Usage Examples

### Get Psychology Questions

```bash
curl -X GET "http://localhost:8000/psychology"
```

### Submit Psychology Answers

```bash
curl -X POST "http://localhost:8000/psychology/submit" \
  -H "Content-Type: application/json" \
  -d '{"answers": [1, 1, 1, 1, 1, 1, 1]}'
```

### Get Neuroscience Questions

```bash
curl -X GET "http://localhost:8000/neuroscience/questions"
```

### Submit Neuroscience Answers

```bash
curl -X POST "http://localhost:8000/neuroscience/submit" \
  -H "Content-Type: application/json" \
  -d '{"answers": ["A", "B", "A", "C", "D", "A", "B", "C", "A"]}'
```

---

## Security Notes

- Use appropriate CORS for production
- Add authentication when needed
- Use HTTPS in production
- Implement rate limiting

---

## Railway Deployment

1. Push your code to GitHub
2. Go to [Railway](https://railway.app)
3. Click "New Project" > "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect and deploy

**Files included for Railway:**
- `Procfile` - Process configuration
- `railway.toml` - Railway configuration
- `runtime.txt` - Python version

---

## License

MIT

