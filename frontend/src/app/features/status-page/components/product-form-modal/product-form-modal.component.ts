import { Component, computed, effect, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

import { ProductCreateDto, ProductUpdateDto } from '../../../../core/models/status.models';
import { ModalShellComponent } from '../modal-shell/modal-shell.component';

export type ProductFormMode = 'create' | 'edit';

export interface ProductFormInitialValue {
  name: string;
  description: string | null;
}

@Component({
  selector: 'app-product-form-modal',
  standalone: true,
  imports: [ReactiveFormsModule, ModalShellComponent],
  templateUrl: './product-form-modal.component.html',
})
export class ProductFormModalComponent {
  readonly mode = input<ProductFormMode>('create');
  readonly initialValue = input<ProductFormInitialValue | null>(null);
  readonly saving = input(false);
  readonly errorMessage = input<string | null>(null);

  readonly submitted = output<ProductCreateDto | ProductUpdateDto>();
  readonly cancelled = output<void>();

  readonly modalTitle = computed(() => (this.mode() === 'create' ? 'Add Product' : 'Edit Product'));

  readonly submitLabel = computed(() => {
    if (this.saving()) {
      return this.mode() === 'create' ? 'Creating...' : 'Saving...';
    }

    return this.mode() === 'create' ? 'Create product' : 'Save changes';
  });

  readonly form = new FormGroup({
    name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(120)],
    }),
    description: new FormControl('', {
      nonNullable: true,
      validators: [Validators.maxLength(3000)],
    }),
  });

  constructor() {
    effect(() => {
      const mode = this.mode();
      const initial = this.initialValue();

      if (mode === 'edit' && initial) {
        this.form.reset({
          name: initial.name ?? '',
          description: initial.description ?? '',
        });
      } else {
        this.form.reset({
          name: '',
          description: '',
        });
      }

      this.form.markAsPristine();
      this.form.markAsUntouched();
    });
  }

  onCancel(): void {
    if (this.saving()) {
      return;
    }

    this.cancelled.emit();
  }

  onSubmit(): void {
    if (this.saving()) {
      return;
    }

    this.form.markAllAsTouched();

    if (this.form.invalid) {
      return;
    }

    const name = this.form.controls.name.value.trim();

    if (!name) {
      this.form.controls.name.setErrors({ required: true });
      return;
    }

    const descriptionValue = this.form.controls.description.value.trim();
    const description = descriptionValue ? descriptionValue : null;

    if (this.mode() === 'create') {
      const payload: ProductCreateDto = {
        name,
        description,
      };

      this.submitted.emit(payload);
      return;
    }

    const payload: ProductUpdateDto = {
      name,
      description,
    };
    this.submitted.emit(payload);
  }
}
