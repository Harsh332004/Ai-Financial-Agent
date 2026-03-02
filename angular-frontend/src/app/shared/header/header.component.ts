import { Component, inject, signal } from '@angular/core';
import { Router, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs/operators';
import { AuthService } from '../../core/services/auth.service';

@Component({
    selector: 'app-header',
    standalone: true,
    template: `
    <header class="header">
      <div class="header-left">
        <div class="breadcrumb">
          <span class="page-name">{{ pageName() }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="status-indicator">
          <span class="status-dot dot-success dot-pulse"></span>
          <span class="status-text">API Connected</span>
        </div>
        <div class="header-divider"></div>
        <div class="user-chip">
          <div class="chip-avatar">{{ userInitial() }}</div>
          <span class="chip-email">{{ auth.currentUser()?.email }}</span>
        </div>
      </div>
    </header>
  `,
    styles: [`
    .header {
      height: var(--header-height);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 24px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      flex-shrink: 0;
    }

    .header-left { display: flex; align-items: center; }

    .breadcrumb { display: flex; align-items: center; gap: 8px; }

    .page-name {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }

    .header-right {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--text-secondary);
    }

    .status-dot {
      width: 8px; height: 8px;
      border-radius: 50%;
    }

    .dot-success { background: var(--status-success); box-shadow: 0 0 6px var(--status-success); }
    .dot-pulse { animation: pulse 1.5s ease-in-out infinite; }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.4; }
    }

    .status-text { color: var(--status-success); font-weight: 500; }

    .header-divider {
      width: 1px;
      height: 24px;
      background: var(--border-subtle);
    }

    .user-chip {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 12px;
      border: 1px solid var(--border-subtle);
      border-radius: 20px;
      cursor: default;
    }

    .chip-avatar {
      width: 22px; height: 22px;
      border-radius: 50%;
      background: var(--gradient-brand);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 700;
      color: white;
    }

    .chip-email {
      font-size: 12px;
      color: var(--text-secondary);
      max-width: 180px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  `]
})
export class HeaderComponent {
    auth = inject(AuthService);
    private router = inject(Router);

    pageName = signal('Dashboard');

    private pageMap: Record<string, string> = {
        '/dashboard': 'Dashboard',
        '/companies': 'Companies',
        '/documents': 'Documents',
        '/agent': 'AI Agent',
        '/reports': 'Reports',
        '/alerts': 'Alerts'
    };

    constructor() {
        this.router.events.pipe(
            filter(e => e instanceof NavigationEnd)
        ).subscribe((e: any) => {
            const name = this.pageMap[e.urlAfterRedirects] ?? 'Page';
            this.pageName.set(name);
        });
        // Set initial
        const initial = this.pageMap[this.router.url] ?? 'Dashboard';
        this.pageName.set(initial);
    }

    userInitial = () => {
        const email = this.auth.currentUser()?.email;
        return email ? email[0].toUpperCase() : 'U';
    };
}
