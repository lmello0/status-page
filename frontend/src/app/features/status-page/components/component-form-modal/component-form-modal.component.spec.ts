import { TestBed } from '@angular/core/testing';

import { ComponentFormModalComponent } from './component-form-modal.component';

describe('ComponentFormModalComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ComponentFormModalComponent],
    }).compileComponents();
  });

  it('starts with create defaults', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    fixture.componentRef.setInput('mode', 'create');
    fixture.detectChanges();

    expect(fixture.componentInstance.form.controls.type.value).toBe('BACKEND');
    expect(fixture.componentInstance.form.controls.checkIntervalSeconds.value).toBe(60);
    expect(fixture.componentInstance.form.controls.timeoutSeconds.value).toBe(30);
    expect(fixture.componentInstance.form.controls.expectedStatusCode.value).toBe(200);
    expect(fixture.componentInstance.form.controls.maxResponseTimeMs.value).toBe(5000);
    expect(fixture.componentInstance.form.controls.failuresBeforeOutage.value).toBe(3);
  });

  it('prefills values in edit mode', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    fixture.componentRef.setInput('mode', 'edit');
    fixture.componentRef.setInput('initialValue', {
      name: 'Checkout API',
      type: 'FRONTEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/checkout',
        checkIntervalSeconds: 45,
        timeoutSeconds: 20,
        expectedStatusCode: 204,
        maxResponseTimeMs: 3500,
        failuresBeforeOutage: 2,
      },
    });
    fixture.detectChanges();

    expect(fixture.componentInstance.form.controls.name.value).toBe('Checkout API');
    expect(fixture.componentInstance.form.controls.type.value).toBe('FRONTEND');
    expect(fixture.componentInstance.form.controls.healthUrl.value).toBe(
      'https://example.com/checkout',
    );
    expect(fixture.componentInstance.form.controls.checkIntervalSeconds.value).toBe(45);
  });

  it('blocks submit when required fields are invalid', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.submitted, 'emit');

    fixture.componentRef.setInput('mode', 'create');
    fixture.componentRef.setInput('productId', 10);
    fixture.detectChanges();

    fixture.componentInstance.form.patchValue({
      name: '',
      healthUrl: '',
    });
    fixture.detectChanges();

    const formElement: HTMLFormElement = fixture.nativeElement.querySelector('form');
    formElement.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(emitSpy).not.toHaveBeenCalled();
    expect(fixture.nativeElement.textContent).toContain('Name is required.');
    expect(fixture.nativeElement.textContent).toContain('Health URL is required.');
  });

  it('emits create payload with product id', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.submitted, 'emit');

    fixture.componentRef.setInput('mode', 'create');
    fixture.componentRef.setInput('productId', 5);
    fixture.detectChanges();

    fixture.componentInstance.form.setValue({
      name: 'Checkout API',
      type: 'BACKEND',
      healthUrl: 'https://example.com/health',
      checkIntervalSeconds: 60,
      timeoutSeconds: 30,
      expectedStatusCode: 200,
      maxResponseTimeMs: 5000,
      failuresBeforeOutage: 3,
    });

    const formElement: HTMLFormElement = fixture.nativeElement.querySelector('form');
    formElement.dispatchEvent(new Event('submit'));

    expect(emitSpy).toHaveBeenCalledWith({
      productId: 5,
      name: 'Checkout API',
      type: 'BACKEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/health',
        checkIntervalSeconds: 60,
        timeoutSeconds: 30,
        expectedStatusCode: 200,
        maxResponseTimeMs: 5000,
        failuresBeforeOutage: 3,
      },
    });
  });

  it('emits update payload in edit mode', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.submitted, 'emit');

    fixture.componentRef.setInput('mode', 'edit');
    fixture.detectChanges();

    fixture.componentInstance.form.setValue({
      name: 'Checkout Frontend',
      type: 'FRONTEND',
      healthUrl: 'https://example.com/frontend-health',
      checkIntervalSeconds: 90,
      timeoutSeconds: 50,
      expectedStatusCode: 200,
      maxResponseTimeMs: 8000,
      failuresBeforeOutage: 4,
    });

    const formElement: HTMLFormElement = fixture.nativeElement.querySelector('form');
    formElement.dispatchEvent(new Event('submit'));

    expect(emitSpy).toHaveBeenCalledWith({
      name: 'Checkout Frontend',
      type: 'FRONTEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/frontend-health',
        checkIntervalSeconds: 90,
        timeoutSeconds: 50,
        expectedStatusCode: 200,
        maxResponseTimeMs: 8000,
        failuresBeforeOutage: 4,
      },
    });
  });

  it('shows inline error message when provided', () => {
    const fixture = TestBed.createComponent(ComponentFormModalComponent);
    fixture.componentRef.setInput('errorMessage', 'Request failed');
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Request failed');
  });
});
