import { Component, computed, input, output } from '@angular/core';

import { ModalShellComponent } from '../modal-shell/modal-shell.component';

@Component({
  selector: 'app-confirm-action-modal',
  standalone: true,
  imports: [ModalShellComponent],
  templateUrl: './confirm-action-modal.component.html',
})
export class ConfirmActionModalComponent {
  readonly title = input.required<string>();
  readonly message = input.required<string>();
  readonly confirmLabel = input.required<string>();
  readonly saving = input(false);
  readonly confirmEnabled = input(true);
  readonly errorMessage = input<string | null>(null);

  readonly confirmed = output<void>();
  readonly cancelled = output<void>();

  readonly confirmButtonLabel = computed(() => (this.saving() ? 'Removing...' : this.confirmLabel()));

  onCancel(): void {
    if (this.saving()) {
      return;
    }

    this.cancelled.emit();
  }

  onConfirm(): void {
    if (this.saving() || !this.confirmEnabled()) {
      return;
    }

    this.confirmed.emit();
  }
}
