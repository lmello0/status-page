import { TestBed } from '@angular/core/testing';

import { ProductFormModalComponent } from './product-form-modal.component';

describe('ProductFormModalComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductFormModalComponent],
    }).compileComponents();
  });

  it('starts with empty defaults in create mode', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    fixture.componentRef.setInput('mode', 'create');
    fixture.detectChanges();

    expect(fixture.componentInstance.form.controls.name.value).toBe('');
    expect(fixture.componentInstance.form.controls.description.value).toBe('');
  });

  it('prefills values in edit mode', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    fixture.componentRef.setInput('mode', 'edit');
    fixture.componentRef.setInput('initialValue', {
      name: 'Payments',
      description: 'Payment stack',
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.form.controls.name.value).toBe('Payments');
    expect(fixture.componentInstance.form.controls.description.value).toBe('Payment stack');
  });

  it('blocks submit when name is empty', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.submitted, 'emit');

    fixture.componentRef.setInput('mode', 'create');
    fixture.detectChanges();

    const formElement: HTMLFormElement = fixture.nativeElement.querySelector('form');
    formElement.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(emitSpy).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Name is required.');
  });

  it('emits normalized payload on submit', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.submitted, 'emit');
    fixture.componentRef.setInput('mode', 'create');
    fixture.detectChanges();

    fixture.componentInstance.form.setValue({
      name: '  Payments  ',
      description: '  Payment stack  ',
    });
    fixture.detectChanges();

    const formElement: HTMLFormElement = fixture.nativeElement.querySelector('form');
    formElement.dispatchEvent(new Event('submit'));

    expect(emitSpy).toHaveBeenCalledWith({
      name: 'Payments',
      description: 'Payment stack',
    });
  });

  it('emits cancelled on cancel click', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    const cancelSpy = vi.spyOn(fixture.componentInstance.cancelled, 'emit');
    fixture.detectChanges();

    const cancelButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'button[type="button"]',
    );
    cancelButton.click();

    expect(cancelSpy).toHaveBeenCalledTimes(1);
  });

  it('shows inline error message when provided', () => {
    const fixture = TestBed.createComponent(ProductFormModalComponent);
    fixture.componentRef.setInput('errorMessage', 'API validation failed');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('API validation failed');
  });
});
