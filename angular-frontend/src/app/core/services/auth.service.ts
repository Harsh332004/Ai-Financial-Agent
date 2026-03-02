import { inject, Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { tap, catchError, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthResponse, LoginRequest, RegisterRequest, User } from '../models';

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

@Injectable({ providedIn: 'root' })
export class AuthService {
    private http = inject(HttpClient);
    private router = inject(Router);

    readonly token = signal<string | null>(localStorage.getItem(TOKEN_KEY));
    readonly currentUser = signal<User | null>(
        JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    );
    readonly isLoggedIn = signal<boolean>(!!localStorage.getItem(TOKEN_KEY));

    login(payload: LoginRequest) {
        return this.http.post<AuthResponse>(`${environment.apiUrl}/auth/login`, payload).pipe(
            tap(res => {
                localStorage.setItem(TOKEN_KEY, res.access_token);
                this.token.set(res.access_token);
                this.isLoggedIn.set(true);
                this.loadCurrentUser();
            })
        );
    }

    register(payload: RegisterRequest) {
        return this.http.post<User>(`${environment.apiUrl}/auth/register`, payload);
    }

    loadCurrentUser() {
        return this.http.get<User>(`${environment.apiUrl}/auth/me`).pipe(
            tap(user => {
                localStorage.setItem(USER_KEY, JSON.stringify(user));
                this.currentUser.set(user);
            }),
            catchError(err => {
                this.logout();
                return throwError(() => err);
            })
        ).subscribe();
    }

    logout() {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        this.token.set(null);
        this.currentUser.set(null);
        this.isLoggedIn.set(false);
        this.router.navigate(['/auth/login']);
    }

    getToken(): string | null {
        return localStorage.getItem(TOKEN_KEY);
    }
}
