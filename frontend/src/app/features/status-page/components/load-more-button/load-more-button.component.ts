import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-load-more-button',
  standalone: true,
  templateUrl: './load-more-button.component.html',
})
export class LoadMoreButtonComponent {
  readonly loading = input(false);
  readonly disabled = input(false);
  readonly clicked = output<void>();

  readonly isDisabled = computed(() => this.loading() || this.disabled());

  onClick(): void {
    if (this.isDisabled()) {
      return;
    }

    this.clicked.emit();
  }
}
