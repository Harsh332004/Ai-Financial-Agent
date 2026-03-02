import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';

interface NavItem {
    label: string;
    icon: string;
    route: string;
    badge?: string;
}

@Component({
    selector: 'app-sidebar',
    standalone: true,
    imports: [RouterLink, RouterLinkActive],
    template: `
    <aside class="sidebar">
      <!-- Brand -->
      <div class="sidebar-brand">
        <div class="brand-logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#grad)"/>
            <path d="M7 18L11 13L15 16L21 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="28" y2="28">
                <stop stop-color="#4f8ef7"/>
                <stop offset="1" stop-color="#7b5ea7"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-name">FinanceAI</span>
          <span class="brand-tag">Agent Platform</span>
        </div>
      </div>

      <!-- Nav -->
      <nav class="sidebar-nav">
        @for (item of navItems; track item.route) {
          <a [routerLink]="item.route" routerLinkActive="active" class="nav-item">
            <span class="nav-icon" [innerHTML]="item.icon"></span>
            <span class="nav-label">{{ item.label }}</span>
          </a>
        }
      </nav>

      <!-- Spacer -->
      <div class="sidebar-spacer"></div>

      <!-- User -->
      <div class="sidebar-footer">
        <div class="user-info">
          <div class="user-avatar">
            {{ userInitial() }}
          </div>
          <div class="user-details">
            <span class="user-name truncate">{{ auth.currentUser()?.email }}</span>
            <span class="user-role">Analyst</span>
          </div>
        </div>
        <button class="logout-btn" (click)="auth.logout()" title="Sign out">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
          </svg>
        </button>
      </div>
    </aside>
  `,
    styles: [`
    .sidebar {
      width: var(--sidebar-width);
      height: 100vh;
      background: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      position: relative;
      z-index: 10;
    }

    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 20px 16px;
      border-bottom: 1px solid var(--border-subtle);
    }

    .brand-logo {
      flex-shrink: 0;
    }

    .brand-text {
      display: flex;
      flex-direction: column;
    }

    .brand-name {
      font-size: 15px;
      font-weight: 700;
      color: var(--text-primary);
      letter-spacing: -0.3px;
    }

    .brand-tag {
      font-size: 10px;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.8px;
    }

    .sidebar-nav {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 16px 10px;
      flex: 1;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      border-radius: var(--radius-md);
      color: var(--text-secondary);
      font-size: 13px;
      font-weight: 500;
      text-decoration: none;
      transition: all var(--transition-fast);
      position: relative;

      &:hover {
        background: rgba(79, 142, 247, 0.06);
        color: var(--text-primary);
      }

      &.active {
        background: rgba(79, 142, 247, 0.12);
        color: var(--accent-primary);

        &::before {
          content: '';
          position: absolute;
          left: 0;
          top: 50%;
          transform: translateY(-50%);
          width: 3px;
          height: 60%;
          background: var(--accent-primary);
          border-radius: 0 2px 2px 0;
        }
      }
    }

    .nav-icon {
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .nav-label { flex: 1; }

    .sidebar-spacer { flex: 1; }

    .sidebar-footer {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px;
      border-top: 1px solid var(--border-subtle);
    }

    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;
      flex: 1;
      min-width: 0;
    }

    .user-avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      background: var(--gradient-brand);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 13px;
      font-weight: 700;
      color: white;
      flex-shrink: 0;
    }

    .user-details {
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    .user-name {
      font-size: 12px;
      font-weight: 500;
      color: var(--text-primary);
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 130px;
    }

    .user-role {
      font-size: 11px;
      color: var(--text-muted);
    }

    .logout-btn {
      width: 32px;
      height: 32px;
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-sm);
      background: transparent;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all var(--transition-fast);
      flex-shrink: 0;

      &:hover {
        background: rgba(244, 63, 94, 0.1);
        border-color: rgba(244, 63, 94, 0.3);
        color: var(--status-error);
      }
    }
  `]
})
export class SidebarComponent {
    auth = inject(AuthService);

    navItems: NavItem[] = [
        {
            label: 'Dashboard',
            route: '/dashboard',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>`
        },
        {
            label: 'Companies',
            route: '/companies',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M9 21V7l6-4v18"/><path d="M15 7h3v14h-3"/></svg>`
        },
        {
            label: 'Documents',
            route: '/documents',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`
        },
        {
            label: 'AI Agent',
            route: '/agent',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83"/></svg>`
        },
        {
            label: 'Reports',
            route: '/reports',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>`
        },
        {
            label: 'Alerts',
            route: '/alerts',
            icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 01-3.46 0"/></svg>`
        }
    ];

    userInitial = () => {
        const email = this.auth.currentUser()?.email;
        return email ? email[0].toUpperCase() : 'U';
    };
}
