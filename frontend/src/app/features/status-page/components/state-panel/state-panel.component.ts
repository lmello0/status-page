import { Component, computed, input, output } from '@angular/core';

export type StatePanelKind = 'loading' | 'error' | 'empty';

@Component({
  selector: 'app-state-panel',
  standalone: true,
  templateUrl: './state-panel.component.html',
})
export class StatePanelComponent {
  readonly kind = input.required<StatePanelKind>();
  readonly title = input<string | null>(null);
  readonly message = input<string | null>(null);
  readonly actionLabel = input<string | null>(null);
  readonly action = output<void>();

  readonly resolvedTitle = computed(() => {
    if (this.title()) {
      return this.title();
    }

    switch (this.kind()) {
      case 'loading':
        return 'Loading status overview';
      case 'error':
        return 'Could not load status data';
      default:
        return 'No products found';
    }
  });

  readonly resolvedMessage = computed(() => {
    if (this.message()) {
      return this.message();
    }

    switch (this.kind()) {
      case 'loading':
        return 'Fetching products and component health...';
      case 'error':
        return 'Please try again. If the issue persists, verify API availability.';
      default:
        return 'Try a different search term to locate products or components.';
    }
  });

  readonly resolvedActionLabel = computed(() => {
    if (this.actionLabel()) {
      return this.actionLabel();
    }

    return this.kind() === 'error' ? 'Retry' : null;
  });

  onAction(): void {
    this.action.emit();
  }
}
