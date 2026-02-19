import { Component, computed, effect, input, output } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';

import {
  ComponentCreateDto,
  ComponentType,
  ComponentUpdateDto,
  MonitoringConfigCreateDto,
} from '../../../../core/models/status.models';
import { ModalShellComponent } from '../modal-shell/modal-shell.component';

export type ComponentFormMode = 'create' | 'edit';

export interface ComponentFormInitialValue {
  name: string;
  type: ComponentType;
  monitoringConfig: MonitoringConfigCreateDto;
}

function integerValidator(control: AbstractControl): ValidationErrors | null {
  const value = control.value;

  if (value === null || value === undefined || value === '') {
    return null;
  }

  return Number.isInteger(Number(value)) ? null : { integer: true };
}

@Component({
  selector: 'app-component-form-modal',
  standalone: true,
  imports: [ReactiveFormsModule, ModalShellComponent],
  templateUrl: './component-form-modal.component.html',
})
export class ComponentFormModalComponent {
  readonly mode = input<ComponentFormMode>('create');
  readonly productId = input<number | null>(null);
  readonly initialValue = input<ComponentFormInitialValue | null>(null);
  readonly saving = input(false);
  readonly errorMessage = input<string | null>(null);

  readonly submitted = output<ComponentCreateDto | ComponentUpdateDto>();
  readonly cancelled = output<void>();

  readonly modalTitle = computed(() =>
    this.mode() === 'create' ? 'Add Component' : 'Edit Component',
  );

  readonly submitLabel = computed(() => {
    if (this.saving()) {
      return this.mode() === 'create' ? 'Creating...' : 'Saving...';
    }

    return this.mode() === 'create' ? 'Create component' : 'Save changes';
  });

  readonly form = new FormGroup({
    name: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(120)],
    }),
    type: new FormControl<ComponentType>('BACKEND', {
      nonNullable: true,
      validators: [Validators.required],
    }),
    healthUrl: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(2000)],
    }),
    checkIntervalSeconds: new FormControl(60, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(1), integerValidator],
    }),
    timeoutSeconds: new FormControl(30, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(1), integerValidator],
    }),
    expectedStatusCode: new FormControl(200, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(100), Validators.max(599), integerValidator],
    }),
    maxResponseTimeMs: new FormControl(5000, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(1), integerValidator],
    }),
    failuresBeforeOutage: new FormControl(3, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(1), integerValidator],
    }),
  });

  constructor() {
    effect(() => {
      const mode = this.mode();
      const initial = this.initialValue();

      if (mode === 'edit' && initial) {
        this.form.reset({
          name: initial.name,
          type: initial.type,
          healthUrl: initial.monitoringConfig.healthUrl,
          checkIntervalSeconds: initial.monitoringConfig.checkIntervalSeconds,
          timeoutSeconds: initial.monitoringConfig.timeoutSeconds,
          expectedStatusCode: initial.monitoringConfig.expectedStatusCode,
          maxResponseTimeMs: initial.monitoringConfig.maxResponseTimeMs,
          failuresBeforeOutage: initial.monitoringConfig.failuresBeforeOutage,
        });
      } else {
        this.form.reset({
          name: '',
          type: 'BACKEND',
          healthUrl: '',
          checkIntervalSeconds: 60,
          timeoutSeconds: 30,
          expectedStatusCode: 200,
          maxResponseTimeMs: 5000,
          failuresBeforeOutage: 3,
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
    const healthUrl = this.form.controls.healthUrl.value.trim();

    if (!name) {
      this.form.controls.name.setErrors({ required: true });
      return;
    }

    if (!healthUrl) {
      this.form.controls.healthUrl.setErrors({ required: true });
      return;
    }

    const monitoringConfig: MonitoringConfigCreateDto = {
      healthUrl,
      checkIntervalSeconds: this.form.controls.checkIntervalSeconds.value,
      timeoutSeconds: this.form.controls.timeoutSeconds.value,
      expectedStatusCode: this.form.controls.expectedStatusCode.value,
      maxResponseTimeMs: this.form.controls.maxResponseTimeMs.value,
      failuresBeforeOutage: this.form.controls.failuresBeforeOutage.value,
    };

    if (this.mode() === 'create') {
      const targetProductId = this.productId();

      if (targetProductId === null) {
        return;
      }

      const payload: ComponentCreateDto = {
        productId: targetProductId,
        name,
        type: this.form.controls.type.value,
        monitoringConfig,
      };
      this.submitted.emit(payload);
      return;
    }

    const payload: ComponentUpdateDto = {
      name,
      type: this.form.controls.type.value,
      monitoringConfig,
    };
    this.submitted.emit(payload);
  }
}
