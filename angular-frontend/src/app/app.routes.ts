import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
    {
        path: 'auth',
        loadChildren: () => import('./features/auth/auth.routes').then(m => m.AUTH_ROUTES)
    },
    {
        path: '',
        canActivate: [authGuard],
        loadComponent: () => import('./shared/layout/layout.component').then(m => m.LayoutComponent),
        children: [
            {
                path: '',
                pathMatch: 'full',
                redirectTo: 'dashboard'
            },
            {
                path: 'dashboard',
                loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent)
            },
            {
                path: 'companies',
                loadComponent: () => import('./features/companies/companies.component').then(m => m.CompaniesComponent)
            },
            {
                path: 'documents',
                loadComponent: () => import('./features/documents/documents.component').then(m => m.DocumentsComponent)
            },
            {
                path: 'agent',
                loadComponent: () => import('./features/agent/agent.component').then(m => m.AgentComponent)
            },
            {
                path: 'reports',
                loadComponent: () => import('./features/reports/reports.component').then(m => m.ReportsComponent)
            },
            {
                path: 'alerts',
                loadComponent: () => import('./features/alerts/alerts.component').then(m => m.AlertsComponent)
            }
        ]
    },
    { path: '**', redirectTo: '' }
];
