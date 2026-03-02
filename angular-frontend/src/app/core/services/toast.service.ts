import { Injectable, signal } from '@angular/core';

export interface Toast {
    id: string;
    message: string;
    type: 'success' | 'error' | 'warning' | 'info';
    duration?: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
    readonly toasts = signal<Toast[]>([]);

    private add(toast: Omit<Toast, 'id'>) {
        const id = Math.random().toString(36).slice(2);
        const duration = toast.duration ?? 4000;
        this.toasts.update(ts => [...ts, { ...toast, id }]);
        setTimeout(() => this.remove(id), duration);
    }

    success(message: string) { this.add({ message, type: 'success' }); }
    error(message: string) { this.add({ message, type: 'error', duration: 6000 }); }
    warning(message: string) { this.add({ message, type: 'warning' }); }
    info(message: string) { this.add({ message, type: 'info' }); }

    remove(id: string) {
        this.toasts.update(ts => ts.filter(t => t.id !== id));
    }
}
