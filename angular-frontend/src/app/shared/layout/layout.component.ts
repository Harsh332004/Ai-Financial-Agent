import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from '../sidebar/sidebar.component';
import { HeaderComponent } from '../header/header.component';
import { ToastContainerComponent } from '../toast-container/toast-container.component';

@Component({
    selector: 'app-layout',
    standalone: true,
    imports: [RouterOutlet, SidebarComponent, HeaderComponent, ToastContainerComponent],
    template: `
    <div class="app-shell">
      <app-sidebar />
      <div class="main-area">
        <app-header />
        <main class="content-area">
          <router-outlet />
        </main>
      </div>
    </div>
    <app-toast-container />
  `,
    styles: [`
    .app-shell {
      display: flex;
      height: 100vh;
      width: 100vw;
      overflow: hidden;
      background: var(--bg-base);
    }

    .main-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .content-area {
      flex: 1;
      overflow: hidden;
      background: var(--bg-base);
    }
  `]
})
export class LayoutComponent { }
