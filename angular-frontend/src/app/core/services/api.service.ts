import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { environment } from '../../../environments/environment';
import {
    Company, CompanyCreate,
    Document,
    AgentRun, AgentRunCreate, AgentRunStatus,
    Alert,
    Report
} from '../models';

@Injectable({ providedIn: 'root' })
export class ApiService {
    private http = inject(HttpClient);
    private base = environment.apiUrl;

    // ── Companies ─────────────────────────────────────────────────────────────
    getCompanies() {
        return this.http.get<Company[]>(`${this.base}/companies`);
    }

    getCompany(id: string) {
        return this.http.get<Company>(`${this.base}/companies/${id}`);
    }

    createCompany(payload: CompanyCreate) {
        return this.http.post<Company>(`${this.base}/companies`, payload);
    }

    updateCompany(id: string, payload: Partial<CompanyCreate>) {
        return this.http.put<Company>(`${this.base}/companies/${id}`, payload);
    }

    deleteCompany(id: string) {
        return this.http.delete<void>(`${this.base}/companies/${id}`);
    }

    // ── Documents ─────────────────────────────────────────────────────────────
    getDocuments(companyId?: string) {
        let params = new HttpParams();
        if (companyId) params = params.set('company_id', companyId);
        return this.http.get<Document[]>(`${this.base}/documents`, { params });
    }

    uploadDocument(file: File, companyId: string, docType?: string) {
        const form = new FormData();
        form.append('file', file);
        form.append('company_id', companyId);
        if (docType) form.append('doc_type', docType);
        return this.http.post<Document>(`${this.base}/documents/upload`, form);
    }

    deleteDocument(id: string) {
        return this.http.delete<void>(`${this.base}/documents/${id}`);
    }

    // ── Agent ─────────────────────────────────────────────────────────────────
    runAgent(payload: AgentRunCreate) {
        return this.http.post<AgentRun>(`${this.base}/agent/run`, payload);
    }

    getAgentRuns() {
        return this.http.get<AgentRun[]>(`${this.base}/agent/runs`);
    }

    getAgentRun(runId: string) {
        return this.http.get<AgentRun>(`${this.base}/agent/runs/${runId}`);
    }

    getAgentRunStatus(runId: string) {
        return this.http.get<AgentRunStatus>(`${this.base}/agent/runs/${runId}/status`);
    }

    // ── Reports ───────────────────────────────────────────────────────────────
    getReports(companyId?: string) {
        let params = new HttpParams();
        if (companyId) params = params.set('company_id', companyId);
        return this.http.get<Report[]>(`${this.base}/reports`, { params });
    }

    downloadReport(reportId: string) {
        return this.http.get(`${this.base}/reports/${reportId}/download`, {
            responseType: 'blob'
        });
    }

    // ── Alerts ────────────────────────────────────────────────────────────────
    getAlerts(companyId?: string, level?: string, acknowledged?: boolean) {
        let params = new HttpParams();
        if (companyId) params = params.set('company_id', companyId);
        if (level) params = params.set('level', level);
        if (acknowledged !== undefined) params = params.set('acknowledged', String(acknowledged));
        return this.http.get<Alert[]>(`${this.base}/alerts`, { params });
    }

    acknowledgeAlert(alertId: string) {
        return this.http.put<Alert>(`${this.base}/alerts/${alertId}/acknowledge`, {});
    }
}
