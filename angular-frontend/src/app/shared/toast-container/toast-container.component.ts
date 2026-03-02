import { Component, inject } from '@angular/core';
import { NgClass } from '@angular/common';
import { ToastService } from '../../core/services/toast.service';

@Component({
    selector: 'app-toast-container',
    standalone: true,
    imports: [NgClass],
    template: `
    <div class="toast-container">
      @for (toast of toastSvc.toasts(); track toast.id) {
        <div class="toast" [ngClass]="'toast-' + toast.type" (click)="toastSvc.remove(toast.id)">
          <span class="toast-icon">{{ icons[toast.type] }}</span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close">✕</button>
        </div>
      }
    </div>
  `,
    styles: [`
    .toast-container {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 9999;
      display: flex;
      flex-direction: column;
      gap: 10px;
      pointer-events: none;
    }

    .toast {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 14px 16px;
      background: var(--bg-elevated);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-lg);
      font-size: 13px;
      color: var(--text-primary);
      animation: fadeInUp 0.3s ease both;
      min-width: 280px;
      max-width: 400px;
      cursor: pointer;
      pointer-events: all;
      transition: opacity 0.2s;

      &:hover { opacity: 0.9; }
    }

    .toast-success { border-left: 3px solid var(--status-success); }
    .toast-error   { border-left: 3px solid var(--status-error); }
    .toast-warning { border-left: 3px solid var(--status-warning); }
    .toast-info    { border-left: 3px solid var(--status-info); }

    .toast-icon { font-size: 16px; flex-shrink: 0; }
    .toast-message { flex: 1; line-height: 1.4; }
    .toast-close {
      background: none; border: none; color: var(--text-muted);
      cursor: pointer; font-size: 12px; padding: 2px 4px;
      &:hover { color: var(--text-primary); }
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translateY(12px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `]
})
export class ToastContainerComponent {
    toastSvc = inject(ToastService);

    icons: Record<string, string> = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
}
