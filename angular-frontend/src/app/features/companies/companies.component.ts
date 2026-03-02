import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { ToastService } from '../../core/services/toast.service';
import { Company } from '../../core/models';

@Component({
  selector: 'app-companies',
  standalone: true,
  imports: [FormsModule, SlicePipe],
  template: `
    <div class="page-container">
      <!-- Header -->
      <div class="page-header animate-fade-in">
        <div>
          <div class="page-title">
            <div class="title-icon">🏢</div>
            <div>
              Companies
              <div class="page-subtitle">Manage the companies you track and analyze</div>
            </div>
          </div>
        </div>
        <button class="btn-primary" (click)="showForm.set(!showForm())">
          @if (showForm()) { Cancel } @else {
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Add Company
          }
        </button>
      </div>

      <!-- Add Company Form -->
      @if (showForm()) {
        <div class="card animate-fade-in-up">
          <h3 style="margin-bottom:20px;font-size:15px">New Company</h3>
          <form (ngSubmit)="createCompany()" class="company-form">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Company Name *</label>
                <input type="text" class="form-control" [(ngModel)]="form.name" name="name"
                  placeholder="Apple Inc." required />
              </div>
              <div class="form-group">
                <label class="form-label">Ticker</label>
                <input type="text" class="form-control" [(ngModel)]="form.ticker" name="ticker"
                  placeholder="AAPL" style="text-transform:uppercase" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Sector</label>
                <select class="form-control" [(ngModel)]="form.sector" name="sector">
                  <option value="">Select sector…</option>
                  @for (s of sectors; track s) {
                    <option [value]="s">{{ s }}</option>
                  }
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Exchange</label>
                <select class="form-control" [(ngModel)]="form.exchange" name="exchange">
                  <option value="">Select exchange…</option>
                  @for (e of exchanges; track e) {
                    <option [value]="e">{{ e }}</option>
                  }
                </select>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">Description</label>
              <textarea class="form-control" [(ngModel)]="form.description" name="description"
                placeholder="Brief company overview…" rows="2"></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn-secondary" (click)="showForm.set(false)">Cancel</button>
              <button type="submit" class="btn-primary" [disabled]="saving()">
                @if (saving()) { <span class="spinner-sm"></span> Creating… } @else { Create Company }
              </button>
            </div>
          </form>
        </div>
      }

      <!-- Companies Table -->
      <div class="card animate-fade-in-up">
        @if (loading()) {
          <div class="loading-overlay"><div class="spinner"></div><span>Loading companies…</span></div>
        } @else if (companies().length === 0) {
          <div class="empty-state">
            <div class="empty-icon">🏢</div>
            <div class="empty-title">No companies yet</div>
            <div class="empty-desc">Add your first company to start tracking financial documents and analyses</div>
          </div>
        } @else {
          <table class="data-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Ticker</th>
                <th>Sector</th>
                <th>Exchange</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (c of companies(); track c.id) {
                <tr>
                  <td>
                    <div class="company-name-cell">
                      <div class="company-avatar">{{ c.name[0].toUpperCase() }}</div>
                      <span class="company-name">{{ c.name }}</span>
                    </div>
                  </td>
                  <td>
                    @if (c.ticker) {
                      <span class="badge badge-info monospace">{{ c.ticker }}</span>
                    } @else {
                      <span class="text-muted">—</span>
                    }
                  </td>
                  <td>{{ c.sector || '—' }}</td>
                  <td>{{ c.exchange || '—' }}</td>
                  <td class="text-muted monospace">{{ c.created_at | slice:0:10 }}</td>
                  <td>
                    <button class="btn-danger btn-sm" (click)="deleteCompany(c)" [disabled]="deleting() === c.id">
                      @if (deleting() === c.id) { … } @else { Delete }
                    </button>
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
    .company-form { display: flex; flex-direction: column; gap: 16px; }

    .form-row {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 16px;
      @media (max-width: 600px) { grid-template-columns: 1fr; }
    }

    .form-actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      padding-top: 8px;
    }

    .company-name-cell {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .company-avatar {
      width: 32px; height: 32px;
      background: var(--gradient-brand);
      border-radius: var(--radius-sm);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
    }

    .company-name { font-weight: 500; }

    .spinner-sm {
      width: 14px; height: 14px;
      border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
      border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class CompaniesComponent implements OnInit {
  private api = inject(ApiService);
  private toast = inject(ToastService);

  companies = signal<Company[]>([]);
  loading = signal(true);
  saving = signal(false);
  deleting = signal<string | null>(null);
  showForm = signal(false);

  form = { name: '', ticker: '', sector: '', exchange: '', description: '' };

  sectors = ['Technology', 'Finance', 'Healthcare', 'Energy', 'Consumer', 'Industrial', 'Real Estate', 'Materials', 'Utilities', 'Telecommunications'];
  exchanges = ['NYSE', 'NASDAQ', 'NSE', 'BSE', 'LSE', 'TSX', 'ASX', 'HKEx', 'Other'];

  ngOnInit() { this.loadCompanies(); }

  loadCompanies() {
    this.loading.set(true);
    this.api.getCompanies().subscribe({
      next: cs => { this.companies.set(cs); this.loading.set(false); },
      error: () => { this.toast.error('Failed to load companies'); this.loading.set(false); }
    });
  }

  createCompany() {
    if (!this.form.name.trim()) { this.toast.warning('Company name is required'); return; }
    this.saving.set(true);
    this.api.createCompany({
      name: this.form.name,
      ticker: this.form.ticker || undefined,
      sector: this.form.sector || undefined,
      exchange: this.form.exchange || undefined,
      description: this.form.description || undefined
    }).subscribe({
      next: c => {
        this.companies.update(cs => [c, ...cs]);
        this.form = { name: '', ticker: '', sector: '', exchange: '', description: '' };
        this.showForm.set(false);
        this.saving.set(false);
        this.toast.success(`${c.name} added successfully`);
      },
      error: err => {
        this.saving.set(false);
        this.toast.error(err?.error?.detail ?? 'Failed to create company');
      }
    });
  }

  deleteCompany(company: Company) {
    if (!confirm(`Delete "${company.name}"? This action cannot be undone.`)) return;
    this.deleting.set(company.id);
    this.api.deleteCompany(company.id).subscribe({
      next: () => {
        this.companies.update(cs => cs.filter(c => c.id !== company.id));
        this.deleting.set(null);
        this.toast.success(`${company.name} deleted`);
      },
      error: () => {
        this.deleting.set(null);
        this.toast.error('Failed to delete company');
      }
    });
  }
}
