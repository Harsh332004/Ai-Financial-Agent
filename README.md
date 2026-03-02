# 🏦 AI Financial Agent Platform

> **Think of this like a smart financial analyst that lives inside your computer.**
> You upload company documents (like annual reports), and an AI reads them, fetches live market data, calculates financial ratios, spots risks, and writes a PDF report — all automatically.

---

## 🧭 What Is This? (For Complete Beginners)

Imagine you're a financial analyst. Your job is to:
1. Read a company's annual report (100+ pages of PDF)
2. Look up the company's stock price and financial data online
3. Calculate ratios like P/E ratio, Debt-to-Equity, etc.
4. Find recent news about the company
5. Flag any risks you spotted
6. Write a summary report

This platform does **all of that automatically** using AI. You just upload the PDF and ask a question.

---

## 🏗️ How the System Is Built (Big Picture)

The app has **three major parts** that talk to each other:

```
┌─────────────────────────────────────────────────────────────┐
│  YOUR BROWSER (what you see)                                │
│  Angular App → http://localhost:4200                        │
│  Pages: Login, Dashboard, Companies, Documents,             │
│         AI Agent, Reports, Alerts                           │
└────────────────────────┬────────────────────────────────────┘
                         │  sends requests (HTTP/REST)
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND SERVER (the brain)                                 │
│  FastAPI App → http://localhost:8000                        │
│  Handles: auth, file uploads, AI agent, reports, alerts     │
└───────────────┬─────────────────────────────────────────────┘
                │  reads/writes data
                ▼
┌─────────────────────────────────────────────────────────────┐
│  DATABASE + STORAGE                                         │
│  PostgreSQL → stores users, companies, runs, alerts         │
│  File System → stores uploaded PDFs, AI indexes, reports    │
│  External APIs → Groq (AI), yfinance (markets), NewsAPI     │
└─────────────────────────────────────────────────────────────┘
```

> **Analogy:** The browser is the restaurant's customer menu. The backend is the kitchen. The database is the pantry. You (the user) order food (request analysis), the kitchen (backend) processes it, and brings you the meal (results).

---

## 📁 Complete File-by-File Guide

### Root Level Files

```
financial-agent/
├── .env                    ← Secret settings (API keys, DB password). NEVER share this.
├── .env.example            ← A template showing what .env should look like (safe to share)
├── requirements.txt        ← List of all Python packages to install (like a shopping list)
├── alembic.ini             ← Config for database migrations tool
├── docker-compose.yml      ← Starts everything (DB + backend) with one command using Docker
├── Dockerfile              ← Instructions to package the backend into a Docker container
├── evaluate.py             ← Script to test how good the AI's answers are (using RAGAS)
├── README.md               ← This file!
└── ARCHITECTURE.md         ← Technical diagrams for the system design
```

---

### 🔙 Backend (`backend/`)

The backend is a **FastAPI** application. FastAPI is a Python framework that creates a web server with REST API endpoints. Think of each endpoint as a function the frontend can call remotely.

```
backend/
├── main.py                 ← THE ENTRY POINT. Starts the server, connects all routers, sets up CORS
├── config.py               ← Reads settings from .env file (API keys, ports, etc.)
├── database.py             ← Connects to PostgreSQL database
```

#### `main.py` — The Server Entry Point
This is where the app starts. It:
- Creates the FastAPI application
- Attaches all the route groups (auth, companies, documents, etc.)
- Configures **CORS** (a security rule that says "only allow requests from port 4200")
- Starts the `/health` check endpoint

#### `config.py` — Settings Manager
Reads all the values from your `.env` file and makes them available as Python variables. Instead of hardcoding `"my-secret-key"` in code, you write `settings.SECRET_KEY`.

#### `database.py` — Database Connection
Sets up the connection to PostgreSQL using **SQLAlchemy** (an ORM — Object-Relational Mapper). An ORM lets you write Python code instead of raw SQL queries.

---

#### `backend/models/` — Database Tables (as Python Classes)

Each file here defines a **database table**. SQLAlchemy uses these Python classes to automatically create and manage tables in PostgreSQL.

```
models/
├── user.py        ← "users" table — stores email, hashed password, name, role
├── company.py     ← "companies" table — stores company name, ticker, exchange
├── document.py    ← "documents" table — stores uploaded file info + processing status
├── chunk.py       ← "chunks" table — stores text pieces extracted from documents
├── agent_run.py   ← "agent_runs" table — records each AI analysis job
├── tool_call.py   ← "tool_calls" table — records each AI tool the agent used
├── report.py      ← "reports" table — records generated PDF reports
└── alert.py       ← "alerts" table — stores risk alerts the agent raised
```

> **Analogy:** If the database is an Excel spreadsheet, each model file is one tab/sheet. The Python class defines what columns that sheet has.

---

#### `backend/schemas/` — Request & Response Shapes

When the frontend sends data to the backend (or receives data), it needs to be in a specific format. **Pydantic schemas** define and validate these formats.

```
schemas/
├── user.py       ← Defines: what a login request looks like, what a user response looks like
├── company.py    ← Defines: fields needed to create a company, fields returned when listing companies
├── document.py   ← Defines: document upload structure, document response
├── agent.py      ← Defines: agent run request, run status response
├── report.py     ← Defines: report response structure
└── alert.py      ← Defines: alert response, acknowledge request
```

> **Analogy:** Schemas are like form templates. If you want to hire someone, the HR form requires: Name, Email, Resume. Similarly, `UserCreate` schema requires: email, password.

---

#### `backend/routers/` — API Endpoints

Each file handles a group of related URL routes. These are the "functions" the frontend calls.

```
routers/
├── auth.py        ← POST /auth/register, POST /auth/login, GET /auth/me
├── companies.py   ← GET /companies, POST /companies, DELETE /companies/{id}
├── documents.py   ← POST /documents/upload, GET /documents, DELETE /documents/{id}
├── agent.py       ← POST /agent/run, GET /agent/runs/{id}, GET /agent/runs/{id}/status
├── reports.py     ← GET /reports, GET /reports/{id}/download
└── alerts.py      ← GET /alerts, POST /alerts/{id}/acknowledge
```

**How a request flows through a router:**
1. Frontend sends: `POST http://localhost:8000/auth/login` with `{email, password}`
2. `auth.py` receives it, validates the schema
3. Checks the database for that user
4. If password matches, creates a JWT token
5. Returns `{access_token: "eyJ..."}` to frontend

---

#### `backend/services/` — Business Logic

Complex logic that's reused across multiple routers lives here.

```
services/
├── auth_service.py      ← Creates JWT tokens, verifies them, hashes passwords with bcrypt
└── document_service.py  ← OCR pipeline: reads PDF → extracts text → chunks → indexes
```

**What is JWT?** JSON Web Token — a string like `eyJhbGciOiJIUzI1NiJ9...` that proves you're logged in. The frontend stores it and sends it with every request as `Authorization: Bearer <token>`.

**What is bcrypt?** A one-way hashing algorithm. Your password `"secret123"` becomes `"$2b$12$..."`. The original password can never be recovered from the hash.

---

#### `backend/rag/` — Document Reading Pipeline (RAG)

**RAG = Retrieval-Augmented Generation.** Instead of the AI hallucinating answers, it first *retrieves* relevant text from your uploaded documents, then *generates* an answer based on that text.

```
rag/
├── ocr.py        ← Reads text from PDFs and images
│                    (PyMuPDF for digital PDFs, EasyOCR for scanned images)
├── chunker.py    ← Splits long documents into small pieces (300 words each)
├── indexer.py    ← Creates a searchable index from document chunks (FAISS + BM25)
└── retriever.py  ← Given a question, finds the most relevant chunks
```

**Step-by-step when you upload a PDF:**
```
PDF upload
  → OCR reads all pages
  → Text split into 300-word chunks
  → Each chunk converted to a number vector (embedding)
  → Vectors stored in FAISS index (for semantic search)
  → Words stored in BM25 index (for keyword search)
  → Document status updated to "ready"
```

**Step-by-step when agent asks a question:**
```
Question: "What was Apple's revenue in 2023?"
  → Question converted to vector
  → FAISS finds top-10 similar chunks (semantic)
  → BM25 finds top-10 matching chunks (keyword)
  → Combine both lists using RRF algorithm
  → Cross-encoder scores each chunk for relevance
  → Top 3 most relevant chunks returned to agent
```

---

#### `backend/agent/` — The AI Brain

```
agent/
├── orchestrator.py  ← The main agent loop — controls the AI thinking process
├── prompts.py       ← The instructions given to the AI ("You are a financial analyst...")
└── tools/
    ├── rag_tool.py      ← Searches uploaded documents
    ├── market_tool.py   ← Gets live stock data from yfinance (P/E, price, etc.)
    ├── news_tool.py     ← Fetches recent news from NewsAPI or yfinance
    ├── calc_tool.py     ← Calculates financial ratios (Debt/Equity, ROE, margins...)
    ├── alert_tool.py    ← Creates risk alerts and saves them to database
    └── report_tool.py   ← Generates a PDF report using ReportLab
```

**How the ReAct Agent Loop Works:**

ReAct = **Re**asoning + **Act**ing. The AI thinks, then acts, then thinks about what it found, then acts again.

```
YOU ask: "Analyze Apple's financial health"

STEP 1 — AI thinks: "I need to read their documents first"
         AI acts:  calls rag_tool("revenue growth 2023")
         Gets back: text chunks from uploaded annual report

STEP 2 — AI thinks: "Now I need live market data"
         AI acts:  calls market_tool("AAPL")
         Gets back: price=$189, P/E=28.5, D/E=1.8

STEP 3 — AI thinks: "Calculate the key ratios"
         AI acts:  calls calc_tool(market_data)
         Gets back: PE: neutral ✓, D/E: elevated ⚠️, ROE: strong ✓

STEP 4 — AI thinks: "That D/E is worrying, I should raise an alert"
         AI acts:  calls alert_tool("warning", "High debt-to-equity ratio of 1.8")
         Gets back: Alert saved to database

STEP 5 — AI thinks: "Get recent news to complete the picture"
         AI acts:  calls news_tool("Apple", "AAPL")
         Gets back: 5 recent news headlines

STEP 6 — AI thinks: "Ready to write the report"
         AI acts:  calls report_tool(all_findings)
         Gets back: PDF saved at reports/report_abc123.pdf

STEP 7 — AI thinks: "I have everything, let me write the final answer"
         AI says:  "Apple shows strong revenue growth of 8% YoY..."
         DONE ✅
```

---

### 🌐 Frontend (`angular-frontend/`)

The frontend is an **Angular 21** application. Angular is a TypeScript framework for building web UIs. It runs entirely in the browser (no server needed after you start `npm start`).

```
angular-frontend/
├── src/
│   ├── index.html           ← The single HTML file. Angular controls everything inside <app-root>
│   ├── main.ts              ← Entry point — bootstraps (starts) the Angular app
│   ├── styles.scss          ← Global dark theme styles, design tokens, utility classes
│   └── environments/
│       ├── environment.ts       ← Dev config: apiUrl = 'http://localhost:8000'
│       └── environment.prod.ts  ← Prod config: apiUrl = your production server URL
```

#### Angular Core Concepts (for beginners)

| Concept | What it is | Real example in this project |
|---|---|---|
| **Component** | A UI building block (HTML + logic) | Login page, Dashboard page, Sidebar |
| **Service** | Shared logic used by many components | AuthService, ApiService |
| **Router** | Manages which component shows for each URL | `/dashboard` → DashboardComponent |
| **Signal** | A reactive variable that updates the UI | `loading = signal(true)` |
| **HTTP Client** | Makes network requests to the backend | `http.post('/auth/login', body)` |
| **Interceptor** | Runs before every HTTP request | Adds `Authorization: Bearer token` |
| **Guard** | Blocks navigation if condition not met | Redirects to login if not logged in |

---

#### `src/app/core/` — Foundation Services

```
core/
├── models/index.ts           ← TypeScript interfaces matching backend response shapes
│                                (Company, Document, AgentRun, Alert, Report, User)
├── services/
│   ├── auth.service.ts       ← Login, register, logout, stores JWT in localStorage
│   ├── api.service.ts        ← All HTTP calls to the backend (getCompanies, runAgent, etc.)
│   └── toast.service.ts      ← Shows popup notifications (success, error, warning)
├── guards/
│   └── auth.guard.ts         ← If user not logged in → redirect to /auth/login
└── interceptors/
    └── auth.interceptor.ts   ← Attaches JWT token to every outgoing HTTP request
```

**`auth.service.ts` — how login works:**
```typescript
login(email, password)
  → sends POST to http://localhost:8000/auth/login
  → gets back { access_token: "eyJ..." }
  → saves token in localStorage (browser storage)
  → fetches user profile from /auth/me
  → stores user in signal (currentUser)
  → redirects browser to /dashboard
```

**`auth.interceptor.ts` — automatic JWT attachment:**
```
Every time you call an API endpoint, this interceptor runs first:
  → reads token from localStorage
  → adds header: "Authorization: Bearer eyJ..."
  → sends the modified request
```

**`api.service.ts` — the HTTP client:**
All backend calls go through here. For example:
```typescript
getCompanies() → GET http://localhost:8000/companies → returns Company[]
runAgent(body) → POST http://localhost:8000/agent/run → returns { run_id }
downloadReport(id) → GET http://localhost:8000/reports/{id}/download → returns PDF blob
```

---

#### `src/app/shared/` — Reusable Layout Components

```
shared/
├── layout/layout.component.ts         ← The page shell (sidebar + header + content area)
├── sidebar/sidebar.component.ts       ← Left navigation: logo + menu items + logout
├── header/header.component.ts         ← Top bar: page title + "API Connected" status + user
├── toast-container/                   ← Renders pop-up notifications from ToastService
└── pipes/replace.pipe.ts              ← String utility pipe (replaces "T" in dates with space)
```

**Layout structure:**
```
┌─────────┬──────────────────────────────────┐
│         │  Header (Dashboard | API ● | User)│
│ Sidebar ├──────────────────────────────────┤
│  (nav)  │                                  │
│         │      <router-outlet>             │
│         │   (feature page goes here)       │
│         │                                  │
└─────────┴──────────────────────────────────┘
```

---

#### `src/app/features/` — The Pages

Each page is one Angular component. Angular uses the router to swap these in and out of the `<router-outlet>` in the layout.

```
features/
├── auth/
│   ├── login/login.component.ts       ← Login form page (dark theme, animated background)
│   ├── register/register.component.ts ← Registration form page
│   └── auth.routes.ts                 ← Routes: /auth/login, /auth/register
│
├── dashboard/dashboard.component.ts   ← Home page after login
│                                         Shows: stats (companies/docs/runs/alerts)
│                                         Recent runs, recent alerts, quick action buttons
│
├── companies/companies.component.ts   ← Company management
│                                         List table + Add form (name, ticker, sector)
│                                         Delete button with confirmation
│
├── documents/documents.component.ts   ← Document management
│                                         Drag-and-drop file upload
│                                         Status: processing → ready/failed
│                                         Filter by company
│
├── agent/agent.component.ts           ← AI analysis runner
│                                         Task input + company selector
│                                         Quick prompt chips
│                                         Real-time polling every 3 seconds
│                                         Shows tool call trace and final answer
│
├── reports/reports.component.ts       ← PDF report download
│                                         Grid of generated reports
│                                         Download button triggers browser download
│
└── alerts/alerts.component.ts         ← Risk alerts dashboard
                                          Stats: Critical / Warning / Info counts
                                          Multi-filter (by level, status, company)
                                          Acknowledge button
```

---

#### `src/app/app.routes.ts` — URL Routing

Defines which component loads for each URL:

```
/                     → redirect to /dashboard
/auth/login           → LoginComponent
/auth/register        → RegisterComponent
/dashboard            → DashboardComponent  (protected by AuthGuard)
/companies            → CompaniesComponent  (protected by AuthGuard)
/documents            → DocumentsComponent  (protected by AuthGuard)
/agent                → AgentComponent      (protected by AuthGuard)
/reports              → ReportsComponent    (protected by AuthGuard)
/alerts               → AlertsComponent     (protected by AuthGuard)
```

"Protected by AuthGuard" means: if you're not logged in and try to visit `/dashboard`, you get automatically redirected to `/auth/login`.

---

#### `src/app/app.config.ts` — App Configuration

Wires everything together at startup:
- `provideRouter(routes)` — enables URL routing
- `provideHttpClient(withInterceptors([authInterceptor]))` — enables HTTP + JWT auto-attachment
- `provideAnimations()` — enables Angular Material animations

---

### 🗄️ Database Migrations (`alembic/`)

When you change a database model (like adding a column), you don't manually edit the database. Instead:

```bash
alembic revision --autogenerate -m "add column X"  # creates migration file
alembic upgrade head                                # applies it to the DB
```

Alembic tracks what version the database is at and only runs new migrations.

---

### 🧪 Evaluation (`evaluate.py`)

Used to measure how good the AI's answers are. It runs test questions through the whole RAG pipeline and scores:
- **Faithfulness** — does the answer come from the documents?
- **Relevancy** — does the answer actually answer the question?
- **Precision/Recall** — were the right document chunks retrieved?

---

## ⚡ Quick Start (How to Run the Project)

### Step 1: Prerequisites

Make sure you have these installed:
- **Python 3.11+** — for the backend (`python --version`)
- **Node.js 18+** — for the Angular frontend (`node --version`)
- **PostgreSQL** — the database (or use Docker)

### Step 2: Configure Environment

```bash
cd financial-agent
cp .env.example .env
```

Open `.env` and fill in:
```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/financial_agent
GROQ_API_KEY=gsk_your_groq_key_here        # Get free at console.groq.com
SECRET_KEY=any_random_long_string_here
NEWS_API_KEY=your_newsapi_key              # Optional
```

### Step 3: Set Up the Database

```bash
# Option A: Use Docker (easiest)
docker run -d --name pg -e POSTGRES_PASSWORD=yourpassword -e POSTGRES_DB=financial_agent -p 5432:5432 postgres:15

# Run database migrations (creates all tables)
.\venv\Scripts\activate          # Windows
alembic upgrade head
```

### Step 4: Install Python Dependencies

```bash
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

### Step 5: Start the Backend

```bash
# From the financial-agent/ directory
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

You'll see: `Uvicorn running on http://0.0.0.0:8000`

Test it: open `http://localhost:8000/health` → should show `{"status":"ok"}`

### Step 6: Start the Angular Frontend

```bash
# Open a NEW terminal
cd angular-frontend
npm install          # Only needed first time
npm start            # Starts at http://localhost:4200
```

### Step 7: Use the App

Open **http://localhost:4200** in your browser.

1. Click **Create account** → Register with your email
2. Login with your credentials
3. Go to **Companies** → Add a company (e.g. "Apple Inc.", ticker "AAPL")
4. Go to **Documents** → Upload an annual report PDF
5. Wait for status to change from "processing" → "ready"
6. Go to **AI Agent** → Select your company, type a task, click Run
7. Watch the AI think (tool calls update in real time)
8. View your **Reports** and **Alerts**

---

## 🔄 The Complete Request Flow (End to End)

Let's trace what happens when you click **"Run Analysis"**:

```
1. You click "Run Analysis" in the browser (Angular)
   ↓
2. AgentComponent calls ApiService.runAgent({ company_id, task })
   ↓
3. ApiService sends: POST http://localhost:8000/agent/run
   Headers: { Authorization: "Bearer eyJ..." }
   Body: { company_id: "abc-123", task: "Analyze financials" }
   ↓
4. authInterceptor ran BEFORE step 3 and added the Authorization header
   ↓
5. FastAPI backend receives the request
   → auth middleware verifies the JWT token
   → extracts user ID from token
   ↓
6. agent.py router creates a new AgentRun record in PostgreSQL (status="running")
   → starts the AI loop in a background task
   → immediately returns { run_id: "xyz-789" } to frontend (HTTP 202)
   ↓
7. Angular receives run_id and starts polling every 3 seconds:
   GET http://localhost:8000/agent/runs/xyz-789/status
   ↓
8. Meanwhile, backend is running the ReAct loop:
   → AI calls rag_tool → reads your uploaded documents
   → AI calls market_tool → fetches live stock data
   → AI calls calc_tool → computes financial ratios
   → AI calls alert_tool → saves a warning alert to DB
   → AI calls report_tool → generates PDF, saves to reports/
   → AI writes final answer
   → AgentRun status updated to "done"
   ↓
9. Next poll from Angular gets status="done"
   → Angular calls GET /agent/runs/xyz-789 for full details
   → Shows tool call trace and final answer
   → Shows "Analysis complete!" toast notification
   ↓
10. PDF Report appears in /reports page
    Alerts appear in /alerts page
```

---

## 🌐 API Endpoints Reference

| Method | URL | What it does | Login required? |
|---|---|---|---|
| POST | `/auth/register` | Create new account | No |
| POST | `/auth/login` | Login → get JWT token | No |
| GET | `/auth/me` | Get your profile | Yes |
| GET | `/companies` | List all companies | Yes |
| POST | `/companies` | Add a new company | Yes |
| DELETE | `/companies/{id}` | Delete a company | Yes |
| POST | `/documents/upload` | Upload PDF/image | Yes |
| GET | `/documents` | List all documents | Yes |
| DELETE | `/documents/{id}` | Delete a document | Yes |
| POST | `/agent/run` | Start AI analysis | Yes |
| GET | `/agent/runs/{id}` | Get full run result | Yes |
| GET | `/agent/runs/{id}/status` | Quick status check | Yes |
| GET | `/agent/runs` | List all runs | Yes |
| GET | `/reports` | List generated reports | Yes |
| GET | `/reports/{id}/download` | Download PDF | Yes |
| GET | `/alerts` | List alerts (filterable) | Yes |
| POST | `/alerts/{id}/acknowledge` | Mark alert as read | Yes |
| GET | `/health` | Health check | No |

**Interactive docs:** Open `http://localhost:8000/docs` when the backend is running.

---

## 🔑 Environment Variables Explained

| Variable | Example | What it's for |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:pass@localhost:5432/financial_agent` | How to connect to PostgreSQL |
| `GROQ_API_KEY` | `gsk_abc123...` | API key for the Groq AI service (the LLM) |
| `SECRET_KEY` | `my-super-random-secret` | Used to sign JWT tokens — keep this private! |
| `NEWS_API_KEY` | `abc123...` | Optional: newsapi.org key for news articles |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Which AI model to use |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Model that converts text to vectors for searching |
| `CHUNK_SIZE` | `300` | How many words per document chunk |
| `FRONTEND_ORIGIN` | `http://localhost:4200` | Which URL is allowed to call the backend |

---

## 🔒 Security Concepts Used

| Concept | Where | Explanation |
|---|---|---|
| **JWT** | auth.service.ts + auth.interceptor.ts | Stateless login token — proves who you are without server storing sessions |
| **bcrypt** | auth_service.py | Password hashing — passwords never stored in plain text |
| **CORS** | main.py | Prevents random websites from calling your API |
| **Auth Guard** | auth.guard.ts | Client-side route protection |
| **Auth Interceptor** | auth.interceptor.ts | Auto-attaches token to every request |

---

## 📦 Key Technologies Used

### Backend
| Technology | What it does | Like... |
|---|---|---|
| **FastAPI** | Web framework | Django/Flask but faster |
| **PostgreSQL** | Database | Excel spreadsheets but powerful |
| **SQLAlchemy** | Talks to PostgreSQL using Python | A translator |
| **Alembic** | Manages database changes | Git for your database |
| **Groq** | AI/LLM provider | Like OpenAI but free tier |
| **FAISS** | Vector similarity search | Google search for text chunks |
| **BM25** | Keyword search | Ctrl+F for documents |
| **PyMuPDF** | Read PDF files | Like opening a PDF |
| **EasyOCR** | Read text from images | Like scanning a document |
| **yfinance** | Get stock market data | Bloomberg terminal, free |
| **ReportLab** | Create PDF files | Like Word but in Python |

### Frontend
| Technology | What it does |
|---|---|
| **Angular 21** | The web framework (TypeScript) |
| **Angular Router** | Switches pages without reload |
| **RxJS** | Handles async events (HTTP, timers) |
| **Angular Signals** | Reactive variables (auto-update UI) |
| **SCSS** | Enhanced CSS with variables and nesting |

---

## 🐳 Docker Compose (All-in-One)

```bash
cp .env.example .env
# Edit .env with your keys
docker-compose up --build
```

| Service | URL |
|---|---|
| Angular Frontend | http://localhost:4200 |
| FastAPI Backend | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

---

## 🧪 RAGAS Evaluation (Testing AI Quality)

```bash
# Basic run
python evaluate.py

# Specific metrics
python evaluate.py --metrics faithfulness answer_relevancy

# Custom data
python evaluate.py --input_file my_questions.csv
```

---

## 📋 API Docs

Visit **http://localhost:8000/docs** when the backend is running to see an interactive UI where you can test every API endpoint.

---

## 📄 License

MIT License — see [LICENSE](./LICENSE) for details.

See **[ARCHITECTURE.md](./ARCHITECTURE.md)** for detailed system diagrams.
