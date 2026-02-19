import { TestBed } from '@angular/core/testing';

import { ProductViewModel } from '../../../../core/models/status.models';
import { ProductTreeComponent } from './product-tree.component';

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

describe('ProductTreeComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProductTreeComponent],
    }).compileComponents();
  });

  it('forwards product and component action events', () => {
    const fixture = TestBed.createComponent(ProductTreeComponent);
    const editProductSpy = vi.spyOn(fixture.componentInstance.editProduct, 'emit');
    const removeProductSpy = vi.spyOn(fixture.componentInstance.removeProduct, 'emit');
    const addComponentSpy = vi.spyOn(fixture.componentInstance.addComponent, 'emit');
    const editComponentSpy = vi.spyOn(fixture.componentInstance.editComponent, 'emit');
    const removeComponentSpy = vi.spyOn(fixture.componentInstance.removeComponent, 'emit');

    fixture.componentRef.setInput('products', [buildProduct()]);
    fixture.componentRef.setInput('expandedProductIds', new Set([1]));
    fixture.detectChanges();

    const editProductButton = fixture.nativeElement.querySelector(
      'button[data-action="edit-product"]',
    ) as HTMLButtonElement | null;
    const removeProductButton = fixture.nativeElement.querySelector(
      'button[data-action="remove-product"]',
    ) as HTMLButtonElement | null;

    editProductButton?.click();
    removeProductButton?.click();
    findButtonByText(fixture.nativeElement, 'Add Component')?.click();
    const componentCard: HTMLElement | null = fixture.nativeElement.querySelector('app-component-status-card');
    componentCard?.querySelector('button[data-action="edit-component"]')?.dispatchEvent(
      new Event('click'),
    );
    componentCard?.querySelector('button[data-action="remove-component"]')?.dispatchEvent(
      new Event('click'),
    );

    expect(editProductSpy).toHaveBeenCalledWith(1);
    expect(removeProductSpy).toHaveBeenCalledWith(1);
    expect(addComponentSpy).toHaveBeenCalledWith(1);
    expect(editComponentSpy).toHaveBeenCalledWith(101);
    expect(removeComponentSpy).toHaveBeenCalledWith(101);
  });
});
