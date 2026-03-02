import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { SlicePipe } from '@angular/common';
import { forkJoin } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [RouterLink, SlicePipe],
  template: `
    <div class="page-container">
      <!-- Welcome Banner -->
      <div class="welcome-banner animate-fade-in-up">
        <div class="welcome-text">
          <h2 class="welcome-title">Good {{ greeting() }}, {{ firstName() }} 👋</h2>
          <p class="welcome-sub">Here's what's happening with your financial portfolio</p>
        </div>
        <a routerLink="/agent" class="btn-primary">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/>
          </svg>
          Run AI Analysis
        </a>
      </div>

      <!-- Stats Grid -->
      @if (loading()) {
        <div class="loading-overlay"><div class="spinner"></div><span>Loading dashboard…</span></div>
      } @else {
        <div class="section-grid cols-4 animate-fade-in-up">
          <div class="stat-card">
            <div class="stat-icon">🏢</div>
            <div class="stat-value">{{ stats().companies }}</div>
            <div class="stat-label">Companies</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">📄</div>
            <div class="stat-value">{{ stats().documents }}</div>
            <div class="stat-label">Documents</div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🤖</div>
            <div class="stat-value">{{ stats().runs }}</div>
            <div class="stat-label">Agent Runs</div>
          </div>
          <div class="stat-card" style="cursor:pointer" routerLink="/alerts">
            <div class="stat-icon" [style.color]="stats().alerts > 0 ? 'var(--status-warning)' : 'var(--accent-primary)'"
                 [style.background]="stats().alerts > 0 ? 'rgba(245,158,11,0.1)' : 'rgba(79,142,247,0.1)'">🚨</div>
            <div class="stat-value" [style.color]="stats().alerts > 0 ? 'var(--status-warning)' : ''">{{ stats().alerts }}</div>
            <div class="stat-label">Unacknowledged Alerts</div>
          </div>
        </div>

        <!-- Recent Activity -->
        <div class="section-grid cols-2 animate-fade-in-up" style="animation-delay:0.1s">
          <!-- Recent Runs -->
          <div class="card">
            <div class="card-header-section">
              <h3 class="section-title">Recent Agent Runs</h3>
              <a routerLink="/agent" class="view-all">View all →</a>
            </div>
            @if (recentRuns().length === 0) {
              <div class="empty-state" style="padding:32px">
                <div class="empty-icon">🤖</div>
                <div class="empty-title">No runs yet</div>
                <div class="empty-desc">Start your first AI analysis from the Agent page</div>
              </div>
            } @else {
              <div class="runs-list">
                @for (run of recentRuns(); track run.id) {
                  <div class="run-item">
                    <div class="run-indicator" [class]="'dot-' + statusColor(run.status)"></div>
                    <div class="run-info">
                      <div class="run-task truncate">{{ run.task }}</div>
                      <div class="run-meta">{{ run.started_at | slice:0:10 }} · {{ run.status }}</div>
                    </div>
                    <span class="badge" [class]="'badge-' + statusBadge(run.status)">{{ run.status }}</span>
                  </div>
                }
              </div>
            }
          </div>

          <!-- Recent Alerts -->
          <div class="card">
            <div class="card-header-section">
              <h3 class="section-title">Recent Alerts</h3>
              <a routerLink="/alerts" class="view-all">View all →</a>
            </div>
            @if (recentAlerts().length === 0) {
              <div class="empty-state" style="padding:32px">
                <div class="empty-icon">✅</div>
                <div class="empty-title">All clear</div>
                <div class="empty-desc">No alerts detected in your portfolio</div>
              </div>
            } @else {
              <div class="alerts-list">
                @for (alert of recentAlerts(); track alert.id) {
                  <div class="alert-item">
                    <span class="alert-dot" [class]="alertDotClass(alert.level)"></span>
                    <div class="alert-info">
                      <div class="alert-msg truncate">{{ alert.message }}</div>
                      <div class="alert-meta">{{ alert.created_at | slice:0:10 }} · {{ alert.level }}</div>
                    </div>
                    <span class="badge" [class]="'badge-' + alertBadge(alert.level)">{{ alert.level }}</span>
                  </div>
                }
              </div>
            }
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="card animate-fade-in-up" style="animation-delay:0.2s">
          <h3 class="section-title" style="margin-bottom:16px">Quick Actions</h3>
          <div class="quick-actions">
            <a routerLink="/companies" class="action-card">
              <div class="action-icon">🏢</div>
              <div class="action-label">Add Company</div>
            </a>
            <a routerLink="/documents" class="action-card">
              <div class="action-icon">📤</div>
              <div class="action-label">Upload Document</div>
            </a>
            <a routerLink="/agent" class="action-card">
              <div class="action-icon">⚡</div>
              <div class="action-label">Run Analysis</div>
            </a>
            <a routerLink="/reports" class="action-card">
              <div class="action-icon">📊</div>
              <div class="action-label">View Reports</div>
            </a>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .welcome-banner {
      background: linear-gradient(135deg, var(--bg-card) 0%, rgba(79,142,247,0.08) 100%);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-lg);
      padding: 28px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }

    .welcome-title {
      font-size: 20px;
      font-weight: 700;
      margin-bottom: 4px;
    }

    .welcome-sub { font-size: 13px; color: var(--text-secondary); }

    .card-header-section {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }

    .section-title { font-size: 14px; font-weight: 600; }

    .view-all { font-size: 12px; color: var(--accent-primary); }

    .runs-list, .alerts-list { display: flex; flex-direction: column; gap: 2px; }

    .run-item, .alert-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 10px 8px;
      border-radius: var(--radius-sm);
      transition: background var(--transition-fast);
      &:hover { background: rgba(79,142,247,0.04); }
    }

    .run-indicator, .alert-dot {
      width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    }

    .dot-success { background: var(--status-success); }
    .dot-warning { background: var(--status-warning); }
    .dot-error   { background: var(--status-error); }
    .dot-info    { background: var(--accent-primary); }

    .alert-dot.info     { background: var(--accent-primary); }
    .alert-dot.warning  { background: var(--status-warning); }
    .alert-dot.critical { background: var(--status-error); }

    .run-info, .alert-info { flex: 1; min-width: 0; }

    .run-task, .alert-msg { font-size: 13px; color: var(--text-primary); }

    .run-meta, .alert-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

    .quick-actions {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;

      @media (max-width: 900px) { grid-template-columns: repeat(2, 1fr); }
    }

    .action-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 10px;
      padding: 20px 16px;
      background: var(--bg-elevated);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      text-decoration: none;
      transition: all var(--transition-fast);
      cursor: pointer;

      &:hover {
        border-color: var(--accent-primary);
        background: rgba(79,142,247,0.06);
        transform: translateY(-2px);
      }
    }

    .action-icon { font-size: 24px; }
    .action-label { font-size: 12px; font-weight: 500; color: var(--text-secondary); text-align: center; }
  `]
})
export class DashboardComponent implements OnInit {
  private api = inject(ApiService);
  private auth = inject(AuthService);

  loading = signal(true);
  stats = signal({ companies: 0, documents: 0, runs: 0, alerts: 0 });
  recentRuns = signal<any[]>([]);
  recentAlerts = signal<any[]>([]);

  greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'morning';
    if (h < 18) return 'afternoon';
    return 'evening';
  };

  firstName = () => {
    const user = this.auth.currentUser();
    if (user?.full_name) return user.full_name.split(' ')[0];
    return user?.email?.split('@')[0] ?? 'Analyst';
  };

  statusColor = (s: string) => s === 'done' ? 'success' : s === 'failed' ? 'error' : 'warning';
  statusBadge = (s: string) => s === 'done' ? 'success' : s === 'failed' ? 'danger' : 'warning';
  alertBadge = (l: string) => l === 'critical' ? 'danger' : l === 'warning' ? 'warning' : 'info';
  alertDotClass = (l: string) => `alert-dot ${l}`;

  ngOnInit() {
    forkJoin({
      companies: this.api.getCompanies(),
      documents: this.api.getDocuments(),
      runs: this.api.getAgentRuns(),
      alerts: this.api.getAlerts(undefined, undefined, false)
    }).subscribe({
      next: data => {
        this.stats.set({
          companies: data.companies.length,
          documents: data.documents.length,
          runs: data.runs.length,
          alerts: data.alerts.length
        });
        this.recentRuns.set(data.runs.slice(0, 5));
        this.recentAlerts.set(data.alerts.slice(0, 5));
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }
}
