import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';
import { ReplacePipe } from '../../shared/pipes/replace.pipe';
import { ApiService } from '../../core/services/api.service';
import { ToastService } from '../../core/services/toast.service';
import { Company, AgentRun } from '../../core/models';

@Component({
    selector: 'app-agent',
    standalone: true,
    imports: [FormsModule, SlicePipe, ReplacePipe],
    template: `
    <div class="page-container">
      <div class="page-header animate-fade-in">
        <div>
          <div class="page-title">
            <div class="title-icon" style="background:rgba(79,142,247,0.12)">⚡</div>
            <div>
              AI Agent
              <div class="page-subtitle">Run financial analysis tasks powered by LLM + RAG</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Run Form -->
      <div class="card animate-fade-in-up">
        <h3 style="margin-bottom:20px;font-size:15px;font-weight:600">New Analysis</h3>
        <div class="run-form">
          <div class="form-group">
            <label class="form-label">Select Company *</label>
            <select class="form-control" [(ngModel)]="task.companyId">
              <option value="">Select a company…</option>
              @for (c of companies(); track c.id) {
                <option [value]="c.id">{{ c.name }}{{ c.ticker ? ' (' + c.ticker + ')' : '' }}</option>
              }
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">Analysis Task *</label>
            <textarea class="form-control" [(ngModel)]="task.prompt" rows="3"
              placeholder="e.g. Analyze Apple's financial health, calculate key ratios, identify risks, and provide investment insights."></textarea>
          </div>

          <!-- Quick Prompts -->
          <div class="quick-prompts-row">
            <span class="quick-label">Quick prompts:</span>
            @for (p of quickPrompts; track p) {
              <button class="quick-chip" (click)="task.prompt = p">{{ p | slice:0:50 }}…</button>
            }
          </div>

          <button class="btn-primary" (click)="runAgent()" [disabled]="running() || !task.companyId || !task.prompt.trim()">
            @if (running()) {
              <span class="anim-dots"></span> Running analysis…
            } @else {
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
              Run Analysis
            }
          </button>
        </div>
      </div>

      <!-- Active Run Result -->
      @if (activeRun()) {
        <div class="card animate-fade-in-up run-result">
          <div class="run-header">
            <div class="run-title-row">
              <h3 class="run-title">Analysis Result</h3>
              <span class="badge" [class]="'badge-' + statusBadge(activeRun()!.status)">
                @if (activeRun()!.status === 'running') {
                  <span class="anim-dot-sm"></span>
                }
                {{ activeRun()!.status }}
              </span>
            </div>
            <div class="run-meta-row">
              <span class="run-task-text">{{ activeRun()!.task | slice:0:80 }}</span>
              @if (activeRun()!.finished_at) {
                <span class="run-duration">{{ formatDuration(activeRun()!.started_at, activeRun()!.finished_at) }}</span>
              }
            </div>
          </div>

          <!-- Tool Calls -->
          @if (activeRun()!.tool_calls && activeRun()!.tool_calls!.length > 0) {
            <div class="tool-calls-section">
              <div class="section-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"></path></svg>
                Tool Calls ({{ activeRun()!.tool_calls!.length }})
              </div>
              <div class="tool-list">
                @for (tc of activeRun()!.tool_calls; track tc.id) {
                  <div class="tool-item">
                    <div class="tool-name">
                      <span class="tool-icon">🔧</span>
                      {{ tc.tool_name }}
                      @if (tc.duration_ms) {
                        <span class="tool-duration">{{ tc.duration_ms }}ms</span>
                      }
                    </div>
                    @if (tc.tool_output) {
                      <div class="tool-output">{{ tc.tool_output | slice:0:300 }}{{ tc.tool_output.length > 300 ? '…' : '' }}</div>
                    }
                  </div>
                }
              </div>
            </div>
          }

          <!-- Final Answer -->
          @if (activeRun()!.final_answer) {
            <div class="answer-section">
              <div class="section-label">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 12l2 2 4-4"/><path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9c2.39 0 4.57.93 6.18 2.44"/></svg>
                Analysis Result
              </div>
              <div class="answer-text">{{ activeRun()!.final_answer }}</div>
            </div>
          }

          @if (activeRun()!.error_message) {
            <div class="error-box">
              <strong>Error:</strong> {{ activeRun()!.error_message }}
            </div>
          }

          @if (activeRun()!.status === 'running') {
            <div class="polling-indicator">
              <div class="spinner" style="width:20px;height:20px"></div>
              <span>Agent is running… polling for updates every 3s</span>
            </div>
          }
        </div>
      }

      <!-- Run History -->
      <div class="card animate-fade-in-up">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
          <h3 style="font-size:14px;font-weight:600">Run History</h3>
          <button class="btn-ghost btn-sm" (click)="loadRuns()">↻ Refresh</button>
        </div>

        @if (runsLoading()) {
          <div class="loading-overlay" style="height:120px"><div class="spinner"></div></div>
        } @else if (runs().length === 0) {
          <div class="empty-state" style="padding:32px">
            <div class="empty-icon">🤖</div>
            <div class="empty-title">No runs yet</div>
            <div class="empty-desc">Submit your first analysis task above</div>
          </div>
        } @else {
          <table class="data-table">
            <thead>
              <tr><th>Task</th><th>Status</th><th>Started</th><th>Duration</th><th>Actions</th></tr>
            </thead>
            <tbody>
              @for (run of runs(); track run.id) {
                <tr>
                  <td><div class="truncate" style="max-width:300px;" title="{{ run.task }}">{{ run.task }}</div></td>
                  <td>
                    <span class="badge" [class]="'badge-' + statusBadge(run.status)">{{ run.status }}</span>
                  </td>
                  <td class="text-muted monospace">{{ run.started_at | slice:0:16 | replace:'T':' ' }}</td>
                  <td class="text-muted monospace">{{ formatDuration(run.started_at, run.finished_at) }}</td>
                  <td>
                    <button class="btn-secondary btn-sm" (click)="viewRun(run.id)">Details</button>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        }
      </div>
    </div>
  `,
    styles: [`
    .run-form { display: flex; flex-direction: column; gap: 16px; }

    .quick-prompts-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .quick-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }

    .quick-chip {
      font-size: 11px;
      padding: 4px 10px;
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      background: var(--bg-elevated);
      color: var(--text-secondary);
      cursor: pointer;
      transition: all var(--transition-fast);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 200px;

      &:hover { border-color: var(--accent-primary); color: var(--accent-primary); }
    }

    .anim-dots::after {
      content: '●●●';
      animation: blink 1.2s infinite;
    }

    .anim-dot-sm {
      width: 6px; height: 6px; border-radius: 50%; background: currentColor;
      animation: pulse 1.5s ease-in-out infinite; display: inline-block; margin-right: 4px;
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .run-result { display: flex; flex-direction: column; gap: 20px; }

    .run-header { border-bottom: 1px solid var(--border-subtle); padding-bottom: 16px; }
    .run-title-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
    .run-title { font-size: 15px; font-weight: 600; }
    .run-meta-row { display: flex; align-items: center; gap: 16px; }
    .run-task-text { font-size: 12px; color: var(--text-secondary); }
    .run-duration { font-size: 12px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }

    .section-label {
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 12px;
    }

    .tool-calls-section, .answer-section { display: flex; flex-direction: column; }

    .tool-list { display: flex; flex-direction: column; gap: 6px; }

    .tool-item {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .tool-name {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      font-weight: 600;
      color: var(--accent-primary);
    }

    .tool-icon { font-size: 14px; }

    .tool-duration {
      margin-left: auto;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      color: var(--text-muted);
    }

    .tool-output {
      font-size: 12px;
      color: var(--text-secondary);
      font-family: 'JetBrains Mono', monospace;
      line-height: 1.5;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .answer-text {
      background: var(--bg-surface);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-md);
      padding: 16px;
      font-size: 13px;
      color: var(--text-primary);
      line-height: 1.7;
      white-space: pre-wrap;
      word-break: break-word;
      border-left: 3px solid var(--accent-primary);
    }

    .error-box {
      background: rgba(244,63,94,0.1);
      border: 1px solid rgba(244,63,94,0.2);
      border-radius: var(--radius-md);
      padding: 12px 16px;
      font-size: 13px;
      color: var(--status-error);
    }

    .polling-indicator {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 13px;
      color: var(--text-muted);
    }
  `]
})
export class AgentComponent implements OnInit, OnDestroy {
    private api = inject(ApiService);
    private toast = inject(ToastService);
    private pollSub?: Subscription;

    companies = signal<Company[]>([]);
    runs = signal<AgentRun[]>([]);
    activeRun = signal<AgentRun | null>(null);
    running = signal(false);
    runsLoading = signal(true);

    task = { companyId: '', prompt: '' };

    quickPrompts = [
        'Analyze financial health, calculate key ratios, and identify major risks.',
        'Compare revenue growth vs industry benchmarks and flag concerns.',
        'Perform DCF analysis and provide a fair value estimate.',
        'Identify top 5 risk factors and generate a risk report.'
    ];

    ngOnInit() {
        this.api.getCompanies().subscribe(cs => this.companies.set(cs));
        this.loadRuns();
    }

    loadRuns() {
        this.runsLoading.set(true);
        this.api.getAgentRuns().subscribe({
            next: rs => { this.runs.set(rs); this.runsLoading.set(false); },
            error: () => this.runsLoading.set(false)
        });
    }

    runAgent() {
        if (!this.task.companyId || !this.task.prompt.trim()) return;
        this.running.set(true);
        this.activeRun.set(null);

        this.api.runAgent({ company_id: this.task.companyId, task: this.task.prompt }).subscribe({
            next: run => {
                this.runs.update(rs => [run, ...rs]);
                this.activeRun.set(run);
                this.toast.info('Agent started — polling for results…');
                this.startPolling(run.id);
            },
            error: err => {
                this.running.set(false);
                this.toast.error(err?.error?.detail ?? 'Failed to start agent');
            }
        });
    }

    viewRun(runId: string) {
        this.api.getAgentRun(runId).subscribe({
            next: run => this.activeRun.set(run),
            error: () => this.toast.error('Failed to load run details')
        });
    }

    startPolling(runId: string) {
        this.pollSub?.unsubscribe();
        this.pollSub = interval(3000).pipe(
            switchMap(() => this.api.getAgentRunStatus(runId)),
            takeWhile(s => s.status === 'running', true)
        ).subscribe(status => {
            if (status.status !== 'running') {
                this.running.set(false);
                this.api.getAgentRun(runId).subscribe(run => {
                    this.activeRun.set(run);
                    this.runs.update(rs => rs.map(r => r.id === runId ? run : r));
                    if (run.status === 'done') this.toast.success('Analysis complete!');
                    else this.toast.error('Analysis failed');
                });
            }
        });
    }

    statusBadge = (s: string) => s === 'done' ? 'success' : s === 'failed' ? 'danger' : 'warning';

    formatDuration = (start: string, end?: string) => {
        if (!end) return '—';
        const ms = new Date(end).getTime() - new Date(start).getTime();
        const s = Math.floor(ms / 1000);
        if (s < 60) return `${s}s`;
        return `${Math.floor(s / 60)}m ${s % 60}s`;
    };

    ngOnDestroy() { this.pollSub?.unsubscribe(); }
}
