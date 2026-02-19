import { TestBed } from '@angular/core/testing';

import { ProductViewModel } from '../../../../core/models/status.models';
import { ProductAccordionItemComponent } from './product-accordion-item.component';

function buildProduct(): ProductViewModel {
  return {
    id: 1,
    name: 'Payments',
    description: 'Payment stack',
    status: 'OPERATIONAL',
    components: [
      {
        id: 101,
        productId: 1,
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
        status: 'OPERATIONAL',
        latestLogDate: null,
        latestUptime: null,
        latestAvgResponseTimeMs: null,
        healthcheckDayLogs: [],
      },
    ],
  };
}

function findButtonByText(root: HTMLElement, text: string): HTMLButtonElement | null {
  const buttons = Array.from(root.querySelectorAll('button')) as HTMLButtonElement[];
  return buttons.find((button) => button.textContent?.trim() === text) ?? null;
}

describe('ProductAccordionItemComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductAccordionItemComponent],
    }).compileComponents();
  });

  it('emits editProduct from header action', () => {
    const fixture = TestBed.createComponent(ProductAccordionItemComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.editProduct, 'emit');

    fixture.componentRef.setInput('product', buildProduct());
    fixture.detectChanges();

    const button = fixture.nativeElement.querySelector(
      'button[data-action="edit-product"]',
    ) as HTMLButtonElement | null;
    button?.click();

    expect(emitSpy).toHaveBeenCalledWith(1);
  });

  it('emits removeProduct from header action', () => {
    const fixture = TestBed.createComponent(ProductAccordionItemComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.removeProduct, 'emit');

    fixture.componentRef.setInput('product', buildProduct());
    fixture.detectChanges();

    const button = fixture.nativeElement.querySelector(
      'button[data-action="remove-product"]',
    ) as HTMLButtonElement | null;
    button?.click();

    expect(emitSpy).toHaveBeenCalledWith(1);
  });

  it('emits addComponent for expanded product', () => {
    const fixture = TestBed.createComponent(ProductAccordionItemComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.addComponent, 'emit');

    fixture.componentRef.setInput('product', buildProduct());
    fixture.componentRef.setInput('expanded', true);
    fixture.detectChanges();

    const button = findButtonByText(fixture.nativeElement, 'Add Component');
    button?.click();

    expect(emitSpy).toHaveBeenCalledWith(1);
  });

  it('propagates component edit event from component card', () => {
    const fixture = TestBed.createComponent(ProductAccordionItemComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.editComponent, 'emit');

    fixture.componentRef.setInput('product', buildProduct());
    fixture.componentRef.setInput('expanded', true);
    fixture.detectChanges();

    const componentCard: HTMLElement | null = fixture.nativeElement.querySelector('app-component-status-card');
    const editButton = componentCard?.querySelector(
      'button[data-action="edit-component"]',
    ) as HTMLButtonElement | null;
    editButton?.click();

    expect(emitSpy).toHaveBeenCalledWith(101);
  });

  it('propagates component remove event from component card', () => {
    const fixture = TestBed.createComponent(ProductAccordionItemComponent);
    const emitSpy = vi.spyOn(fixture.componentInstance.removeComponent, 'emit');

    fixture.componentRef.setInput('product', buildProduct());
    fixture.componentRef.setInput('expanded', true);
    fixture.detectChanges();

    const componentCard: HTMLElement | null = fixture.nativeElement.querySelector('app-component-status-card');
    const removeButton = componentCard?.querySelector(
      'button[data-action="remove-component"]',
    ) as HTMLButtonElement | null;
    removeButton?.click();

    expect(emitSpy).toHaveBeenCalledWith(101);
  });
});
