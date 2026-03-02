import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { ToastService } from '../../../core/services/toast.service';

@Component({
    selector: 'app-register',
    standalone: true,
    imports: [FormsModule, RouterLink],
    template: `
    <div class="auth-page">
      <div class="auth-bg">
        <div class="auth-mesh"></div>
      </div>

      <div class="auth-container">
        <div class="auth-card animate-fade-in-up">
          <div class="auth-brand">
            <div class="auth-logo">
              <svg width="36" height="36" viewBox="0 0 28 28" fill="none">
                <rect width="28" height="28" rx="8" fill="url(#gr)"/>
                <path d="M7 18L11 13L15 16L21 9" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <defs>
                  <linearGradient id="gr" x1="0" y1="0" x2="28" y2="28">
                    <stop stop-color="#4f8ef7"/><stop offset="1" stop-color="#7b5ea7"/>
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <div>
              <h1 class="auth-title">Create Account</h1>
              <p class="auth-subtitle">Join the AI Financial Platform</p>
            </div>
          </div>

          <form (ngSubmit)="register()" class="auth-form">
            <div class="form-group">
              <label class="form-label">Full name (optional)</label>
              <input type="text" class="form-control" [(ngModel)]="fullName" name="fullName"
                placeholder="John Smith" autocomplete="name" />
            </div>

            <div class="form-group">
              <label class="form-label">Email address</label>
              <input type="email" class="form-control" [(ngModel)]="email" name="email"
                placeholder="analyst@company.com" required autocomplete="email" />
            </div>

            <div class="form-group">
              <label class="form-label">Password</label>
              <input type="password" class="form-control" [(ngModel)]="password" name="password"
                placeholder="Min. 8 characters" required autocomplete="new-password" minlength="8" />
            </div>

            @if (error()) {
              <div class="alert-error animate-fade-in">{{ error() }}</div>
            }

            <button type="submit" class="btn-primary w-full" [disabled]="loading()">
              @if (loading()) {
                <span class="spinner-sm"></span> Creating account...
              } @else {
                Create account
              }
            </button>
          </form>

          <p class="auth-footer">
            Already have an account?
            <a routerLink="/auth/login" class="auth-link">Sign in</a>
          </p>
        </div>
      </div>
    </div>
  `,
    styles: [`
    .auth-page {
      min-height: 100vh;
      display: flex;
      align-items: stretch;
      background: var(--bg-base);
      overflow: hidden;
    }
    .auth-bg {
      flex: 1;
      background: var(--gradient-mesh);
      position: relative;
      @media (max-width: 768px) { display: none; }
    }
    .auth-mesh {
      position: absolute; inset: 0;
      background: radial-gradient(at 40% 40%, rgba(79,142,247,0.12) 0%, transparent 50%);
    }
    .auth-container {
      width: 480px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px 32px;
      @media (max-width: 768px) { width: 100%; }
    }
    .auth-card {
      width: 100%;
      background: var(--bg-surface);
      border: 1px solid var(--border-default);
      border-radius: var(--radius-xl);
      padding: 40px;
      box-shadow: var(--shadow-lg);
    }
    .auth-brand { display: flex; align-items: center; gap: 14px; margin-bottom: 32px; }
    .auth-logo { width: 52px; height: 52px; display: flex; align-items: center; justify-content: center; }
    .auth-title {
      font-size: 22px; font-weight: 700;
      background: var(--gradient-brand);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
    }
    .auth-subtitle { font-size: 13px; color: var(--text-secondary); margin-top: 2px; }
    .auth-form { display: flex; flex-direction: column; gap: 16px; }
    .alert-error {
      background: rgba(244,63,94,0.1); border: 1px solid rgba(244,63,94,0.2);
      border-radius: var(--radius-md); padding: 10px 14px;
      font-size: 13px; color: var(--status-error);
    }
    .w-full { width: 100%; justify-content: center; margin-top: 8px; }
    .spinner-sm {
      width: 16px; height: 16px;
      border: 2px solid rgba(255,255,255,0.3); border-top-color: white;
      border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .auth-footer { text-align: center; margin-top: 24px; font-size: 13px; color: var(--text-secondary); }
    .auth-link { color: var(--accent-primary); font-weight: 500; margin-left: 4px; }
  `]
})
export class RegisterComponent {
    private auth = inject(AuthService);
    private router = inject(Router);
    private toast = inject(ToastService);

    fullName = '';
    email = '';
    password = '';
    loading = signal(false);
    error = signal('');

    register() {
        if (!this.email || !this.password) {
            this.error.set('Please fill in all required fields.'); return;
        }
        if (this.password.length < 8) {
            this.error.set('Password must be at least 8 characters.'); return;
        }
        this.loading.set(true);
        this.error.set('');

        this.auth.register({
            email: this.email,
            password: this.password,
            full_name: this.fullName || undefined
        }).subscribe({
            next: () => {
                this.toast.success('Account created! Please sign in.');
                this.router.navigate(['/auth/login']);
            },
            error: (err) => {
                this.loading.set(false);
                this.error.set(err?.error?.detail ?? 'Registration failed. Please try again.');
            }
        });
    }
}
