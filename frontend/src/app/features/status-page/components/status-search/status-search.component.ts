import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-status-search',
  standalone: true,
  templateUrl: './status-search.component.html',
})
export class StatusSearchComponent {
  readonly value = input('');
  readonly valueChange = output<string>();

  onInput(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.valueChange.emit(target.value);
  }

  clear(): void {
    this.valueChange.emit('');
  }
}
