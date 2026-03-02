// ── Auth ────────────────────────────────────────────────────────────────────
export interface LoginRequest {
    email: string;
    password: string;
}

export interface RegisterRequest {
    email: string;
    password: string;
    full_name?: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface User {
    id: string;
    email: string;
    full_name?: string;
    is_active: boolean;
    created_at: string;
}

// ── Companies ───────────────────────────────────────────────────────────────
export interface Company {
    id: string;
    name: string;
    ticker?: string;
    sector?: string;
    exchange?: string;
    description?: string;
    created_at: string;
    created_by?: string;
}

export interface CompanyCreate {
    name: string;
    ticker?: string;
    sector?: string;
    exchange?: string;
    description?: string;
}

// ── Documents ───────────────────────────────────────────────────────────────
export interface Document {
    id: string;
    company_id: string;
    filename: string;
    original_filename: string;
    doc_type?: string;
    status: 'processing' | 'ready' | 'failed';
    uploaded_at: string;
    uploaded_by?: string;
}

// ── Agent ───────────────────────────────────────────────────────────────────
export interface AgentRunCreate {
    task: string;
    company_id: string;
}

export interface ToolCall {
    id: string;
    tool_name: string;
    tool_input: Record<string, unknown>;
    tool_output?: string;
    duration_ms?: number;
    created_at: string;
}

export interface AgentRun {
    id: string;
    company_id: string;
    task: string;
    status: 'running' | 'done' | 'failed';
    final_answer?: string;
    error_message?: string;
    started_at: string;
    finished_at?: string;
    tool_calls?: ToolCall[];
}

export interface AgentRunStatus {
    run_id: string;
    status: 'running' | 'done' | 'failed';
    finished_at?: string;
}

// ── Alerts ──────────────────────────────────────────────────────────────────
export interface Alert {
    id: string;
    company_id: string;
    run_id?: string;
    level: 'info' | 'warning' | 'critical';
    message: string;
    acknowledged: boolean;
    acknowledged_by?: string;
    acknowledged_at?: string;
    created_at: string;
}

// ── Reports ─────────────────────────────────────────────────────────────────
export interface Report {
    id: string;
    company_id: string;
    run_id: string;
    file_path: string;
    created_at: string;
}
