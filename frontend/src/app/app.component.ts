import { Component } from '@angular/core';

import { StatusPageComponent } from './features/status-page/status-page.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [StatusPageComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class App {}
