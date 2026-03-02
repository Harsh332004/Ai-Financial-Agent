import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { ToastService } from '../../core/services/toast.service';
import { Company, Document } from '../../core/models';

@Component({
  selector: 'app-documents',
  standalone: true,
  imports: [FormsModule, SlicePipe],
  template: `
    <div class="page-container">
      <div class="page-header animate-fade-in">
        <div>
          <div class="page-title">
            <div class="title-icon">📄</div>
            <div>
              Documents
              <div class="page-subtitle">Upload and manage financial documents for analysis</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Upload Card -->
      <div class="card animate-fade-in-up">
        <h3 style="margin-bottom:20px;font-size:15px;font-weight:600">Upload Document</h3>
        <div class="upload-layout">
          <!-- Drop Zone -->
          <div class="drop-zone" [class.drag-over]="dragOver()" [class.has-file]="selectedFile()"
            (click)="fileInput.click()"
            (dragover)="$event.preventDefault(); dragOver.set(true)"
            (dragleave)="dragOver.set(false)"
            (drop)="onDrop($event)">
            <input #fileInput type="file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp,.webp"
              style="display:none" (change)="onFileChange($event)" />
            @if (selectedFile()) {
              <div class="file-selected">
                <div class="file-icon">📄</div>
                <div class="file-name">{{ selectedFile()!.name }}</div>
                <div class="file-size">{{ formatSize(selectedFile()!.size) }}</div>
                <button type="button" class="btn-ghost btn-sm" (click)="$event.stopPropagation(); selectedFile.set(null)">Remove</button>
              </div>
            } @else {
              <div class="drop-prompt">
                <div class="drop-icon">📤</div>
                <div class="drop-title">Drop file here or click to browse</div>
                <div class="drop-sub">PDF, PNG, JPG, TIFF, BMP, WebP</div>
              </div>
            }
          </div>

          <!-- Upload Options -->
          <div class="upload-options">
            <div class="form-group">
              <label class="form-label">Company *</label>
              <select class="form-control" [(ngModel)]="upload.companyId" name="companyId">
                <option value="">Select company…</option>
                @for (c of companies(); track c.id) {
                  <option [value]="c.id">{{ c.name }}{{ c.ticker ? ' (' + c.ticker + ')' : '' }}</option>
                }
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">Document Type</label>
              <select class="form-control" [(ngModel)]="upload.docType" name="docType">
                <option value="">Select type…</option>
                @for (t of docTypes; track t.value) {
                  <option [value]="t.value">{{ t.label }}</option>
                }
              </select>
            </div>

            <button class="btn-primary" (click)="uploadDoc()" [disabled]="uploading() || !selectedFile() || !upload.companyId">
              @if (uploading()) {
                <span class="spinner-sm"></span> Uploading…
              } @else {
                Upload & Process
              }
            </button>
          </div>
        </div>
      </div>

      <!-- Filter Bar -->
      <div class="filter-bar animate-fade-in-up">
        <select class="form-control" [(ngModel)]="filterCompany" (ngModelChange)="applyFilter()" style="max-width:200px">
          <option value="">All Companies</option>
          @for (c of companies(); track c.id) {
            <option [value]="c.id">{{ c.name }}</option>
          }
        </select>
        <div class="doc-count">{{ filteredDocs().length }} document{{ filteredDocs().length !== 1 ? 's' : '' }}</div>
      </div>

      <!-- Documents Table -->
      <div class="card animate-fade-in-up">
        @if (loading()) {
          <div class="loading-overlay"><div class="spinner"></div><span>Loading documents…</span></div>
        } @else if (filteredDocs().length === 0) {
          <div class="empty-state">
            <div class="empty-icon">📁</div>
            <div class="empty-title">No documents</div>
            <div class="empty-desc">Upload PDF or image files to start analyzing financial data</div>
          </div>
        } @else {
          <table class="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Company</th>
                <th>Type</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (doc of filteredDocs(); track doc.id) {
                <tr>
                  <td>
                    <div class="doc-cell">
                      <span class="doc-ext">{{ getExt(doc.original_filename) }}</span>
                      <span class="doc-name truncate">{{ doc.original_filename }}</span>
                    </div>
                  </td>
                  <td>{{ companyName(doc.company_id) }}</td>
                  <td>{{ doc.doc_type || '—' }}</td>
                  <td>
                    <span class="badge" [class]="'badge-' + statusBadge(doc.status)">
                      <span class="status-dot-sm" [class]="'dot-' + statusBadge(doc.status)"></span>
                      {{ doc.status }}
                    </span>
                  </td>
                  <td class="text-muted monospace">{{ doc.uploaded_at | slice:0:10 }}</td>
                  <td>
                    <button class="btn-danger btn-sm" (click)="deleteDoc(doc)" [disabled]="deleting() === doc.id">
                      @if (deleting() === doc.id) { … } @else { Delete }
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
    .upload-layout {
      display: grid;
      grid-template-columns: 1fr 280px;
      gap: 24px;
      @media (max-width: 768px) { grid-template-columns: 1fr; }
    }

    .drop-zone {
      border: 2px dashed var(--border-default);
      border-radius: var(--radius-lg);
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 160px;
      cursor: pointer;
      transition: all var(--transition-fast);

      &:hover, &.drag-over {
        border-color: var(--accent-primary);
        background: rgba(79,142,247,0.04);
      }

      &.has-file {
        border-color: var(--status-success);
        background: rgba(16,217,160,0.04);
      }
    }

    .drop-prompt, .file-selected {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      text-align: center;
      padding: 20px;
    }

    .drop-icon, .file-icon { font-size: 36px; }

    .drop-title { font-size: 14px; font-weight: 500; color: var(--text-primary); }
    .drop-sub   { font-size: 12px; color: var(--text-muted); }

    .file-name { font-size: 13px; font-weight: 500; color: var(--text-primary); word-break: break-all; }
    .file-size { font-size: 12px; color: var(--text-muted); }

    .upload-options { display: flex; flex-direction: column; gap: 16px; }

    .filter-bar {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .doc-count { font-size: 13px; color: var(--text-secondary); }

    .doc-cell {
      display: flex;
      align-items: center;
      gap: 8px;
      max-width: 280px;
    }

    .doc-ext {
      font-size: 10px;
      font-weight: 600;
      background: rgba(79,142,247,0.1);
      color: var(--accent-primary);
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
      flex-shrink: 0;
    }

    .status-dot-sm {
      width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-right: 4px;
    }

    .dot-success { background: var(--status-success); }
    .dot-warning { background: var(--status-warning); }
    .dot-danger  { background: var(--status-error); }

    .spinner-sm {
      width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
      border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block;
    }

    @keyframes spin { to { transform: rotate(360deg); } }
  `]
})
export class DocumentsComponent implements OnInit {
  private api = inject(ApiService);
  private toast = inject(ToastService);

  companies = signal<Company[]>([]);
  documents = signal<Document[]>([]);
  filteredDocs = signal<Document[]>([]);
  loading = signal(true);
  uploading = signal(false);
  deleting = signal<string | null>(null);
  selectedFile = signal<File | null>(null);
  dragOver = signal(false);
  filterCompany = '';

  upload = { companyId: '', docType: '' };

  docTypes = [
    { value: 'annual_report', label: 'Annual Report' },
    { value: 'earnings', label: 'Earnings Report' },
    { value: 'balance_sheet', label: 'Balance Sheet' },
    { value: 'news', label: 'News Article' },
    { value: 'other', label: 'Other' }
  ];

  ngOnInit() {
    this.api.getCompanies().subscribe(cs => this.companies.set(cs));
    this.loadDocs();
  }

  loadDocs() {
    this.loading.set(true);
    this.api.getDocuments().subscribe({
      next: docs => {
        this.documents.set(docs);
        this.applyFilter();
        this.loading.set(false);
      },
      error: () => { this.toast.error('Failed to load documents'); this.loading.set(false); }
    });
  }

  applyFilter() {
    const docs = this.documents();
    this.filteredDocs.set(
      this.filterCompany ? docs.filter(d => d.company_id === this.filterCompany) : docs
    );
  }

  onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    if (input.files?.[0]) this.selectedFile.set(input.files[0]);
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.dragOver.set(false);
    if (event.dataTransfer?.files?.[0]) this.selectedFile.set(event.dataTransfer.files[0]);
  }

  uploadDoc() {
    const file = this.selectedFile();
    if (!file || !this.upload.companyId) return;

    this.uploading.set(true);
    this.api.uploadDocument(file, this.upload.companyId, this.upload.docType || undefined).subscribe({
      next: doc => {
        this.documents.update(ds => [doc, ...ds]);
        this.applyFilter();
        this.selectedFile.set(null);
        this.upload = { companyId: '', docType: '' };
        this.uploading.set(false);
        this.toast.success('Document uploaded — processing in background');
      },
      error: err => {
        this.uploading.set(false);
        this.toast.error(err?.error?.detail ?? 'Upload failed');
      }
    });
  }

  deleteDoc(doc: Document) {
    if (!confirm(`Delete "${doc.original_filename}"?`)) return;
    this.deleting.set(doc.id);
    this.api.deleteDocument(doc.id).subscribe({
      next: () => {
        this.documents.update(ds => ds.filter(d => d.id !== doc.id));
        this.applyFilter();
        this.deleting.set(null);
        this.toast.success('Document deleted');
      },
      error: () => { this.deleting.set(null); this.toast.error('Failed to delete'); }
    });
  }

  companyName = (id: string) => this.companies().find(c => c.id === id)?.name ?? '—';
  getExt = (fn: string) => fn.split('.').pop() ?? 'file';
  formatSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };
  statusBadge = (s: string) => s === 'ready' ? 'success' : s === 'failed' ? 'danger' : 'warning';
}
