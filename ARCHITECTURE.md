# 🏗️ AI Financial Agent — System Architecture

> A visual, diagram-heavy guide to every layer of the platform.
> Designed to be understandable even if you're new to software architecture.

---

## What Is "Architecture"?

Architecture is like a blueprint of a building. It shows:
- **What parts** the system has (frontend, backend, database, AI)
- **How they connect** to each other (HTTP, SQL, file system)
- **What flows through** each connection (JSON data, files, tokens)

---

## 1. 🌐 High-Level System Overview

```mermaid
graph TB
    subgraph USER["👤 You (the user)"]
        Browser["Your Browser\nhttp://localhost:4200"]
    end

    subgraph FRONTEND["🖥️ Angular Frontend (port 4200)"]
        Login["Login / Register Page"]
        Dashboard["Dashboard Page"]
        Companies["Companies Page"]
        Documents["Documents Page"]
        Agent["AI Agent Page"]
        Reports["Reports Page"]
        Alerts["Alerts Page"]
        AuthSvc["AuthService\n(stores JWT token)"]
        ApiSvc["ApiService\n(all HTTP calls)"]
        Sidebar["Sidebar + Header\n(shared layout)"]
    end

    subgraph BACKEND["⚙️ FastAPI Backend (port 8000)"]
        FastAPI["main.py\n(app entry point + CORS)"]
        AuthR["auth.py router\n/auth/register\n/auth/login"]
        CompR["companies.py router"]
        DocR["documents.py router"]
        AgentR["agent.py router"]
        ReportR["reports.py router"]
        AlertR["alerts.py router"]
    end

    subgraph AI["🤖 AI Agent Layer"]
        Orch["orchestrator.py\n(ReAct loop)"]
        RAGTool["rag_tool\n(search documents)"]
        MktTool["market_tool\n(stock data)"]
        NewsTool["news_tool\n(headlines)"]
        CalcTool["calc_tool\n(financial ratios)"]
        AlertTool["alert_tool\n(create alerts)"]
        RptTool["report_tool\n(generate PDF)"]
    end

    subgraph RAG["📚 RAG Pipeline"]
        OCR["ocr.py\n(read PDF/image text)"]
        Chunker["chunker.py\n(split into pieces)"]
        Indexer["indexer.py\n(FAISS + BM25)"]
        Retriever["retriever.py\n(find relevant chunks)"]
    end

    subgraph STORAGE["🗄️ Storage Layer"]
        PG[("PostgreSQL\n(port 5432)\nusers, companies,\ndocuments, runs,\nalerts, reports")]
        FS["File System\nuploads/ → PDFs\nindexes/ → AI vectors\nreports/ → PDFs"]
    end

    subgraph EXTERNAL["☁️ External APIs"]
        Groq["Groq API\n(Llama 3.3 70B LLM)"]
        YF["yfinance\n(live stock data)"]
        News["NewsAPI\n(news headlines)"]
    end

    Browser --> Login
    Browser --> Dashboard & Companies & Documents & Agent & Reports & Alerts
    Login --> AuthSvc
    AuthSvc --> ApiSvc
    Companies & Documents & Agent & Reports & Alerts --> ApiSvc
    ApiSvc -->|"HTTP requests\n+ JWT token"| FastAPI
    FastAPI --> AuthR & CompR & DocR & AgentR & ReportR & AlertR
    AgentR --> Orch
    Orch --> RAGTool & MktTool & NewsTool & CalcTool & AlertTool & RptTool
    RAGTool --> Retriever --> Indexer
    DocR -->|"upload → background"| OCR --> Chunker --> Indexer
    Indexer --> FS
    MktTool --> YF
    NewsTool --> News
    NewsTool -.->|fallback| YF
    RptTool --> FS
    Orch --> Groq
    AuthR & CompR & DocR & AgentR & ReportR & AlertR --> PG
```

---

## 2. 🔐 Authentication Flow

How login works from your click to getting a JWT:

```mermaid
sequenceDiagram
    participant U as Browser (Angular)
    participant AS as AuthService
    participant INT as authInterceptor
    participant BE as FastAPI /auth/login
    participant DB as PostgreSQL

    U->>AS: login("email", "password")
    AS->>BE: POST /auth/login { email, password }
    BE->>DB: SELECT user WHERE email = ?
    DB-->>BE: User row
    BE->>BE: bcrypt.verify(password, hashed_password)
    BE-->>AS: { access_token: "eyJ..." }
    AS->>AS: localStorage.setItem("token", "eyJ...")
    AS->>BE: GET /auth/me (with token)
    BE-->>AS: { id, email, full_name, role }
    AS->>AS: currentUser.set(user) [Signal]
    AS-->>U: navigate to /dashboard

    Note over INT: Every future request:
    U->>INT: any HTTP call
    INT->>INT: read token from localStorage
    INT->>BE: adds "Authorization: Bearer eyJ..." header
```

---

## 3. 📤 Document Upload & Processing Pipeline

What happens from the moment you click "Upload" to status = "ready":

```mermaid
flowchart TD
    A([You click Upload\nin Angular]) --> B[Angular sends\nPOST /documents/upload\nwith file + company_id]
    B --> C[FastAPI receives file]
    C --> D[Saves file to uploads/]
    C --> E[Creates Document record\nin PostgreSQL\nstatus = 'processing']
    C --> F[Returns immediately\nto Angular]
    C --> G[Background task starts\nasync processing]

    G --> H{File type?}
    H -->|.pdf| I[PyMuPDF\nreads each page]
    H -->|.png .jpg .tiff| J[EasyOCR\nreads image text]
    I --> K{Page has\nenough text?}
    K -->|yes| L[Use digital text]
    K -->|no - scanned page| M[EasyOCR fallback\non rendered image]
    J & L & M --> N[Clean & normalize text]

    N --> O[chunker.py\nSplit into 300-word pieces\nwith 50-word overlap]
    O --> P[SentenceTransformer\nConvert each chunk\nto a number vector\nall-MiniLM-L6-v2]
    P --> Q[FAISS IndexFlatIP\nSave dense vectors\nfor semantic search]
    P --> R[BM25Okapi\nSave word frequencies\nfor keyword search]
    Q & R --> S[Save index files\nto indexes/company_id.*]
    S --> T[Update Document\nstatus = 'ready' in DB]
    T --> U([Angular polling\nshows status: ready ✅])
```

---

## 4. 🔍 RAG Retrieval Pipeline

When the AI agent needs to search your documents:

```mermaid
flowchart LR
    Q(["Agent asks:\n'What was revenue\nin 2023?'"]) --> E1

    E1["Encode query\nto vector\nall-MiniLM-L6-v2"] --> FAISS
    Q --> BM25

    FAISS["FAISS search\nfinds top-10\nsemanticaly similar\nchunks"]
    BM25["BM25 search\nfinds top-10\nkeyword matching\nchunks"]

    FAISS --> RRF
    BM25 --> RRF

    RRF["Reciprocal Rank Fusion\nCombines both lists\nsmarتly — chunks that\nappear in both get\nhigher score"]

    RRF --> CE

    CE["Cross-Encoder\nScores each\nchunk vs query\nfor true relevance"]

    CE --> TOP["Top 3 chunks\nreturned to agent"]

    TOP --> ANS(["AI reads the chunks\nand answers the question\nwithout hallucinating"])
```

> **Why two search methods?**
> - **FAISS (semantic)** understands meaning — "profit" matches "earnings" even without the same word
> - **BM25 (keyword)** finds exact matches — great for specific numbers, dates, names
> - **Together** they catch more relevant text than either alone

---

## 5. 🤖 ReAct Agent Loop

The AI "thinks" in steps, calling tools between each thought:

```mermaid
sequenceDiagram
    participant U as Angular Frontend
    participant AG as agent.py router
    participant DB as PostgreSQL
    participant O as orchestrator.py
    participant G as Groq LLM API
    participant T as Tools

    U->>AG: POST /agent/run { company_id, task }
    AG->>DB: INSERT AgentRun (status="running")
    AG-->>U: 202 Accepted { run_id }

    Note over U: Frontend polls every 3s

    loop ReAct Loop (up to 10 steps)
        O->>G: "Here are your tools. Task: Analyze Apple. What do you want to do?"
        G-->>O: "I'll search the documents first"
        O->>T: call rag_tool("Apple revenue 2023")
        T-->>O: "Revenue was $383B, up 8% YoY..."
        O->>DB: Save ToolCall record

        O->>G: "Got doc data. What next?"
        G-->>O: "Get live market data"
        O->>T: call market_tool("AAPL")
        T-->>O: { price: 189, PE: 28.5, DE: 1.8 }
        O->>DB: Save ToolCall record

        O->>G: "Got market data. What next?"
        G-->>O: "The D/E is high, create an alert"
        O->>T: call alert_tool("warning", "High D/E ratio of 1.8")
        T-->>O: Alert saved successfully
        O->>DB: Save ToolCall record

        O->>G: "Alert created. Generate the PDF report?"
        G-->>O: "Yes, generate report"
        O->>T: call report_tool(all_findings)
        T-->>O: Report saved at reports/abc.pdf
        O->>DB: Save Report record

        O->>G: "Report done. Write final answer."
        G-->>O: "Apple shows strong revenue growth of 8%..."
        O->>DB: UPDATE AgentRun (status="done", final_answer=...)
    end

    U->>AG: GET /agent/runs/{id}/status
    AG-->>U: { status: "done" }
    U->>AG: GET /agent/runs/{id}
    AG-->>U: Full run with tool calls + final answer
```

---

## 6. 🗄️ Database Schema (Entity Relationship)

How all the tables relate to each other:

```mermaid
erDiagram
    USER {
        UUID id PK
        string email UK "must be unique"
        string hashed_password "bcrypt hash, never plain text"
        string full_name
        string role "analyst | manager | admin"
        datetime created_at
    }

    COMPANY {
        UUID id PK
        string name
        string ticker "e.g. AAPL"
        string sector
        string exchange "NYSE, NASDAQ..."
        UUID created_by FK
        datetime created_at
    }

    DOCUMENT {
        UUID id PK
        UUID company_id FK
        string original_filename
        string file_path "path in uploads/"
        string doc_type "annual_report, earnings..."
        string status "processing | ready | failed"
        UUID uploaded_by FK
        datetime uploaded_at
    }

    CHUNK {
        UUID id PK
        UUID document_id FK
        int chunk_index "position in document"
        text text "the actual text content"
        datetime created_at
    }

    AGENT_RUN {
        UUID id PK
        UUID company_id FK
        UUID user_id FK
        string task "the user's question"
        string status "running | done | failed"
        text final_answer
        text error_message
        datetime started_at
        datetime finished_at
    }

    TOOL_CALL {
        UUID id PK
        UUID run_id FK
        int step "which iteration (1,2,3...)"
        string tool_name "rag_search, market_tool..."
        json tool_input "what was sent to the tool"
        json tool_output "what the tool returned"
        int duration_ms "how long it took"
        datetime called_at
    }

    REPORT {
        UUID id PK
        UUID run_id FK
        UUID company_id FK
        string file_path "path in reports/"
        UUID created_by FK
        datetime created_at
    }

    ALERT {
        UUID id PK
        UUID company_id FK
        UUID run_id FK
        string level "info | warning | critical"
        string message
        bool acknowledged "false by default"
        datetime created_at
    }

    USER ||--o{ COMPANY : "creates"
    USER ||--o{ DOCUMENT : "uploads"
    USER ||--o{ AGENT_RUN : "triggers"
    COMPANY ||--o{ DOCUMENT : "has many"
    COMPANY ||--o{ AGENT_RUN : "analyzed by"
    COMPANY ||--o{ ALERT : "receives"
    COMPANY ||--o{ REPORT : "has reports"
    DOCUMENT ||--o{ CHUNK : "split into"
    AGENT_RUN ||--o{ TOOL_CALL : "records steps"
    AGENT_RUN ||--o| REPORT : "generates one"
    AGENT_RUN ||--o{ ALERT : "raises"
```

---

## 7. 🖥️ Angular Frontend Architecture

How the Angular app is structured:

```mermaid
graph TD
    subgraph BOOT["Bootstrap"]
        main["main.ts\n(entry point)"]
        config["app.config.ts\n(providers: HTTP, Router, Animations)"]
        root["App component\n(just a router-outlet)"]
    end

    subgraph CORE["core/ — Services & Guards"]
        AuthSvc["AuthService\n• login / register / logout\n• stores JWT in localStorage\n• currentUser Signal"]
        ApiSvc["ApiService\n• all HTTP calls\n• companies, docs, agent,\n  reports, alerts"]
        ToastSvc["ToastService\n• success / error / warning\n• Signal-based toasts"]
        Guard["AuthGuard\n• checks if logged in\n• redirects to /login if not"]
        Intercept["authInterceptor\n• adds Bearer token\n• to every HTTP request"]
    end

    subgraph SHARED["shared/ — Layout"]
        Layout["LayoutComponent\n• shell: sidebar + header + content"]
        Sidebar["SidebarComponent\n• nav links\n• logout button"]
        Header["HeaderComponent\n• page title\n• API status dot\n• user chip"]
        Toast["ToastContainer\n• renders notifications"]
    end

    subgraph FEATURES["features/ — Pages"]
        Auth["auth/\n• LoginComponent\n• RegisterComponent"]
        Dash["dashboard/\n• DashboardComponent\n• stats + recent activity"]
        Comp["companies/\n• CompaniesComponent\n• CRUD table"]
        Doc["documents/\n• DocumentsComponent\n• drag-drop upload"]
        Ag["agent/\n• AgentComponent\n• run + polling + trace"]
        Rep["reports/\n• ReportsComponent\n• PDF download"]
        Al["alerts/\n• AlertsComponent\n• filter + acknowledge"]
    end

    main --> config --> root
    root --> Auth
    root --> Layout
    Layout --> Sidebar & Header & Toast
    Layout --> Dash & Comp & Doc & Ag & Rep & Al
    Dash & Comp & Doc & Ag & Rep & Al --> ApiSvc
    Auth --> AuthSvc
    AuthSvc --> ApiSvc
    ApiSvc --> Intercept
    Dash & Comp & Doc & Ag & Rep & Al --> ToastSvc
    Guard -->|protects| Dash & Comp & Doc & Ag & Rep & Al
```

---

## 8. 🔒 Security Architecture

```mermaid
flowchart LR
    subgraph FRONTEND["Browser"]
        Form["Login Form"]
        LS["localStorage\nstores JWT token"]
        Guard["AuthGuard\nblocks pages\nif not logged in"]
        Intercept["authInterceptor\nadds Bearer header\nto every request"]
    end

    subgraph BACKEND["FastAPI Backend"]
        Pub["Public endpoints:\n/auth/login\n/auth/register\n/health"]
        Prot["Protected endpoints:\nall others\n(require valid JWT)"]
        Mid["JWT Middleware\nverify(token, SECRET_KEY)\nextract user_id"]
        Bcrypt["bcrypt verify\ncompares plain password\nwith hash in DB"]
    end

    subgraph DB["PostgreSQL"]
        Users["users table\nhashed_password stored\nNEVER plain text"]
    end

    Form -->|POST email+password| Pub
    Pub --> Bcrypt
    Bcrypt --> Users
    Users --> Bcrypt
    Bcrypt -->|match| Pub
    Pub -->|returns JWT| LS
    Guard -->|reads| LS
    Intercept -->|reads| LS
    Intercept -->|adds header| Prot
    Prot --> Mid
    Mid -->|valid| Prot
    Mid -->|invalid| ERR["401 Unauthorized"]
```

---

## 9. 🌐 API Endpoint Map

Every URL the backend exposes:

```mermaid
graph LR
    subgraph AUTH["/auth — No login required"]
        A1["POST /register\nCreate account"]
        A2["POST /login\nGet JWT token"]
        A3["GET /me\nGet your profile"]
    end

    subgraph COMP["/companies"]
        C1["GET /\nList all companies"]
        C2["POST /\nAdd new company"]
        C3["DELETE /{id}\nDelete company"]
    end

    subgraph DOCS["/documents"]
        D1["POST /upload\n→ background OCR+index"]
        D2["GET /\nList all documents"]
        D3["DELETE /{id}\nDelete document"]
    end

    subgraph AGT["/agent"]
        AG1["POST /run\n→ 202 + run_id"]
        AG2["GET /runs/{id}/status\nPolling endpoint"]
        AG3["GET /runs/{id}\nFull result + trace"]
        AG4["GET /runs\nAll runs list"]
    end

    subgraph RPT["/reports"]
        R1["GET /\nList reports"]
        R2["GET /{id}/download\n→ PDF file stream"]
    end

    subgraph ALRT["/alerts"]
        AL1["GET /\n?company_id=\n?level=\n?acknowledged="]
        AL2["POST /{id}/acknowledge\nMark as read"]
    end

    subgraph SYS["System"]
        S1["GET /health\n{status: ok}"]
        S2["GET /docs\nSwagger UI"]
    end
```

---

## 10. 📊 Data Flow: Adding a Company (Simple Example)

Tracing one simple operation end-to-end:

```mermaid
sequenceDiagram
    participant U as You (Browser)
    participant C as CompaniesComponent
    participant AS as ApiService
    participant INT as authInterceptor
    participant BE as companies.py (FastAPI)
    participant DB as PostgreSQL

    U->>C: Fill form: "Apple Inc., AAPL, Technology"
    U->>C: Click "Create Company"
    C->>AS: createCompany({ name, ticker, sector })
    AS->>INT: http.post('/companies', body)
    INT->>INT: read JWT from localStorage
    INT->>BE: POST /companies\nHeader: Authorization: Bearer eyJ...\nBody: { name: "Apple Inc.", ticker: "AAPL" }
    BE->>BE: Verify JWT → extract user_id
    BE->>DB: INSERT INTO companies\n(name, ticker, sector, created_by=user_id)
    DB-->>BE: New company row with UUID
    BE-->>AS: 201 Created { id, name, ticker, ... }
    AS-->>C: Observable<Company>
    C->>C: companies.update(cs => [new, ...cs])
    C->>C: showForm.set(false)
    C-->>U: Toast: "Apple Inc. added successfully" ✅
    C-->>U: Table updates with new row
```

---

## 11. 📁 Complete File Tree with Roles

```
financial-agent/
│
│  ← ROOT CONFIG FILES
├── .env                    ← Runtime secrets (NEVER commit to git)
├── .env.example            ← Template showing what .env needs
├── requirements.txt        ← Python package list
├── alembic.ini             ← Database migration config
├── docker-compose.yml      ← Multi-container startup config
├── Dockerfile              ← Backend container build instructions
├── evaluate.py             ← RAGAS quality evaluation script
│
│  ← BACKEND (Python/FastAPI)
├── backend/
│   ├── main.py             ← Server entry point + CORS + router mounting
│   ├── config.py           ← Reads .env into typed settings object
│   ├── database.py         ← PostgreSQL async connection setup
│   │
│   ├── models/             ← Database table definitions (SQLAlchemy ORM)
│   │   ├── user.py         ← users table
│   │   ├── company.py      ← companies table
│   │   ├── document.py     ← documents table
│   │   ├── chunk.py        ← chunks table (RAG text pieces)
│   │   ├── agent_run.py    ← agent_runs table
│   │   ├── tool_call.py    ← tool_calls table (AI step log)
│   │   ├── report.py       ← reports table
│   │   └── alert.py        ← alerts table
│   │
│   ├── schemas/            ← Request/response data shapes (Pydantic)
│   │   ├── user.py         ← LoginRequest, UserCreate, UserResponse, TokenResponse
│   │   ├── company.py      ← CompanyCreate, CompanyResponse
│   │   ├── document.py     ← DocumentResponse
│   │   ├── agent.py        ← AgentRunRequest, AgentRunResponse, RunStatus
│   │   ├── report.py       ← ReportResponse
│   │   └── alert.py        ← AlertResponse
│   │
│   ├── routers/            ← API endpoint handlers
│   │   ├── auth.py         ← /auth/register, /auth/login, /auth/me
│   │   ├── companies.py    ← GET/POST/DELETE /companies
│   │   ├── documents.py    ← POST /documents/upload, GET/DELETE /documents
│   │   ├── agent.py        ← POST /agent/run, GET /agent/runs/{id}
│   │   ├── reports.py      ← GET /reports, GET /reports/{id}/download
│   │   └── alerts.py       ← GET /alerts, POST /alerts/{id}/acknowledge
│   │
│   ├── services/           ← Reusable business logic
│   │   ├── auth_service.py     ← JWT create/verify, bcrypt hash/verify
│   │   └── document_service.py ← Full OCR→chunk→index pipeline
│   │
│   ├── agent/              ← AI agent implementation
│   │   ├── orchestrator.py ← ReAct loop (think → act → think → act...)
│   │   ├── prompts.py      ← System prompt for the AI
│   │   └── tools/
│   │       ├── rag_tool.py     ← Searches uploaded documents
│   │       ├── market_tool.py  ← Gets live stock data (yfinance)
│   │       ├── news_tool.py    ← Gets news articles (NewsAPI + yfinance)
│   │       ├── calc_tool.py    ← Calculates financial ratios
│   │       ├── alert_tool.py   ← Creates and saves risk alerts
│   │       └── report_tool.py  ← Generates PDF reports (ReportLab)
│   │
│   └── rag/                ← Document search pipeline
│       ├── ocr.py          ← Extracts text from PDFs and images
│       ├── chunker.py      ← Splits text into 300-word pieces
│       ├── indexer.py      ← Builds FAISS (dense) + BM25 (sparse) index
│       └── retriever.py    ← Finds most relevant chunks for a query
│
│  ← DATABASE MIGRATIONS
├── alembic/
│   └── versions/           ← Migration scripts (one per schema change)
│
│  ← ANGULAR FRONTEND (TypeScript)
├── angular-frontend/
│   ├── angular.json        ← Angular build configuration (zone.js, styles, etc.)
│   ├── package.json        ← Node.js dependencies list
│   ├── tsconfig.json       ← TypeScript compiler settings
│   └── src/
│       ├── index.html      ← Single HTML file (Angular renders inside <app-root>)
│       ├── main.ts         ← Angular bootstrap entry point
│       ├── styles.scss     ← Global dark theme styles and design tokens
│       ├── environments/
│       │   ├── environment.ts       ← Dev: apiUrl = localhost:8000
│       │   └── environment.prod.ts  ← Prod: apiUrl = your server URL
│       └── app/
│           ├── app.ts          ← Root component (just <router-outlet>)
│           ├── app.config.ts   ← Wires HTTP, Router, Interceptors, Animations
│           ├── app.routes.ts   ← URL-to-component mapping
│           │
│           ├── core/                ← Foundation (services, guards, interceptors)
│           │   ├── models/index.ts  ← TypeScript types matching backend JSON
│           │   ├── services/
│           │   │   ├── auth.service.ts   ← Login/logout/JWT/currentUser
│           │   │   ├── api.service.ts    ← All backend HTTP calls
│           │   │   └── toast.service.ts  ← Pop-up notifications
│           │   ├── guards/
│           │   │   └── auth.guard.ts     ← Redirect to login if not authenticated
│           │   └── interceptors/
│           │       └── auth.interceptor.ts ← Auto-adds JWT header
│           │
│           ├── shared/              ← Reusable layout components
│           │   ├── layout/layout.component.ts        ← Page shell
│           │   ├── sidebar/sidebar.component.ts       ← Left navigation
│           │   ├── header/header.component.ts         ← Top bar
│           │   ├── toast-container/                   ← Toast renderer
│           │   └── pipes/replace.pipe.ts              ← String helper pipe
│           │
│           └── features/            ← Page components (one per route)
│               ├── auth/
│               │   ├── auth.routes.ts             ← /auth/login & /auth/register routes
│               │   ├── login/login.component.ts   ← Login form
│               │   └── register/register.component.ts ← Register form
│               ├── dashboard/dashboard.component.ts   ← Home stats page
│               ├── companies/companies.component.ts   ← Company CRUD
│               ├── documents/documents.component.ts   ← Document upload
│               ├── agent/agent.component.ts           ← AI agent runner
│               ├── reports/reports.component.ts       ← PDF downloads
│               └── alerts/alerts.component.ts         ← Risk alerts
│
│  ← RUNTIME DATA (auto-created, ignored by git)
├── uploads/            ← Raw uploaded files (PDFs, images)
├── indexes/            ← FAISS vector files + BM25 pickle files per company
├── reports/            ← Generated PDF report files
└── evaluation_results/ ← RAGAS evaluation output (CSV, JSON, charts)
```

---

## 12. 🧪 RAGAS Evaluation Pipeline

How we measure AI answer quality:

```mermaid
flowchart TD
    CLI(["python evaluate.py\n--metrics faithfulness\n--model llama-3.1-8b"]) --> LOAD

    LOAD["Load test data\n8 built-in Q&A pairs\nor your own CSV/JSON"] --> BUILD

    BUILD["Build evaluation dataset\n{question, answer, context, ground_truth}"] --> BATCH

    BATCH["Process in batches of 4\n(avoids API rate limits)"] --> EVAL

    subgraph EVAL["RAGAS Metrics Calculated"]
        M1["faithfulness\n0→1\nAre claims supported by docs?"]
        M2["answer_relevancy\n0→1\nDoes answer address question?"]
        M3["context_precision\n0→1\nAre relevant chunks ranked first?"]
        M4["context_recall\n0→1\nDoes context cover ground truth?"]
        M5["answer_correctness\n0→1\nDoes answer match reference?"]
    end

    EVAL --> OUT

    subgraph OUT["evaluation_results/"]
        O1["results.csv\nScore per row"]
        O2["stats.json\nMean/median/min/max"]
        O3["report.txt\nHuman summary"]
        O4["bar.png\nChart of scores"]
        O5["dist.png\nScore distribution"]
    end
```

---

## 13. 🐳 Deployment Architecture

```mermaid
graph TB
    subgraph LOCAL["💻 Local Development (current setup)"]
        LNG["Angular Dev Server\nnpm start\nport 4200\nHot reload"]
        LBE["FastAPI + Uvicorn\nuvicorn backend.main:app --reload\nport 8000"]
        LDB["PostgreSQL\nlocal install or Docker\nport 5432"]
        LNG -->|"HTTP API calls"| LBE
        LBE -->|"SQL queries"| LDB
    end

    subgraph DOCKER["🐳 Docker Compose (all-in-one)"]
        DC_FE["angular service\nnginx serving built Angular\nport 4200"]
        DC_BE["backend service\nuvicorn backend.main:app\nport 8000"]
        DC_DB["postgres:15 service\nport 5432\nvolume: postgres_data"]
        DC_FE -->|depends_on| DC_BE
        DC_BE -->|depends_on| DC_DB
    end

    subgraph EXTERNAL_APIS["☁️ External Services"]
        Groq2["Groq Cloud\n(LLM inference)\nfree tier available"]
        YF2["Yahoo Finance\n(yfinance library)\nno API key needed"]
        News2["NewsAPI.org\nfree 100 req/day tier"]
    end

    LBE & DC_BE --> Groq2 & YF2 & News2

    Alembic["alembic upgrade head\nruns DB migrations\nbefore first start"]
    Alembic --> LDB & DC_DB
```

---

## 14. 🧩 Technology Choice Rationale

| Decision | Technology Chosen | Why |
|---|---|---|
| AI/LLM | Groq + Llama 3.3 70B | Very fast inference, free tier, tool-calling support |
| Web framework | FastAPI | Async, auto-docs, Pydantic integration |
| Database | PostgreSQL | ACID-compliant, UUID support, async drivers |
| Vector search | FAISS | Extremely fast, runs locally (no cloud needed) |
| OCR | PyMuPDF + EasyOCR | PyMuPDF for digital PDFs, EasyOCR for scanned |
| Frontend framework | Angular 21 | Production-grade, standalone components, signals |
| Embedding model | all-MiniLM-L6-v2 | Fast, good quality, runs on CPU |
| PDF generation | ReportLab | Full control over layout, pure Python |
| Market data | yfinance | Free, no API key, comprehensive |
