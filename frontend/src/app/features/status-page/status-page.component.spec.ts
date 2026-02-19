import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, Subject, throwError } from 'rxjs';

import { PagedResponse, ProductApi } from '../../core/models/status.models';
import { ProductsApiService } from '../../core/services/products-api.service';
import { StatusPageComponent } from './status-page.component';

const AUTO_REFRESH_INTERVAL_MS = 30_000;

function buildProduct(overrides: Partial<ProductApi> = {}): ProductApi {
  return {
    id: 1,
    name: 'Payments',
    description: 'Payment stack',
    isVisible: true,
    createdAt: '2026-02-18T00:00:00Z',
    updatedAt: '2026-02-18T00:00:00Z',
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
        currentStatus: 'OPERATIONAL',
        isActive: true,
        healthcheckDayLogs: [
          {
            date: '2026-02-18T00:00:00Z',
            totalChecks: 12,
            successfulChecks: 12,
            uptime: 100,
            avgResponseTime: 220,
            maxResponseTime: 500,
            overallStatus: 'OPERATIONAL',
          },
        ],
      },
    ],
    ...overrides,
  };
}

function paged(content: ProductApi[], totalPages = 1): PagedResponse<ProductApi> {
  return {
    pageSize: 10,
    pageCount: content.length,
    totalElements: content.length,
    totalPages,
    content,
  };
}

function findButtonByText(root: HTMLElement, text: string): HTMLButtonElement | null {
  const buttons = Array.from(root.querySelectorAll('button')) as HTMLButtonElement[];
  return buttons.find((button) => button.textContent?.trim() === text) ?? null;
}

describe('StatusPageComponent', () => {
  let getProductsMock: ReturnType<typeof vi.fn>;
  let createProductMock: ReturnType<typeof vi.fn>;
  let updateProductMock: ReturnType<typeof vi.fn>;
  let deleteProductMock: ReturnType<typeof vi.fn>;
  let createComponentMock: ReturnType<typeof vi.fn>;
  let updateComponentMock: ReturnType<typeof vi.fn>;
  let deleteComponentMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    getProductsMock = vi.fn();
    createProductMock = vi.fn();
    updateProductMock = vi.fn();
    deleteProductMock = vi.fn();
    createComponentMock = vi.fn();
    updateComponentMock = vi.fn();
    deleteComponentMock = vi.fn();

    await TestBed.configureTestingModule({
      imports: [StatusPageComponent],
      providers: [
        {
          provide: ProductsApiService,
          useValue: {
            getProducts: getProductsMock,
            createProduct: createProductMock,
            updateProduct: updateProductMock,
            deleteProduct: deleteProductMock,
            createComponent: createComponentMock,
            updateComponent: updateComponentMock,
            deleteComponent: deleteComponentMock,
          },
        },
      ],
    }).compileComponents();
  });

  it('shows loading state while initial request is pending', () => {
    const pendingRequest = new Subject<PagedResponse<ProductApi>>();
    getProductsMock.mockReturnValue(pendingRequest.asObservable());

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Loading status overview');
  });

  it('shows error state and retry action on request failure', () => {
    getProductsMock.mockReturnValue(throwError(() => new Error('boom')));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Could not load status data');
    expect(fixture.nativeElement.textContent).toContain('Retry');
  });

  it('shows empty state when API has no visible active products', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct({ isVisible: false })])));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('No products found');
  });

  it('performs debounced search and matches component names', async () => {
    const payments = buildProduct();
    const messaging = buildProduct({
      id: 2,
      name: 'Messaging',
      components: [
        {
          ...buildProduct().components[0],
          id: 201,
          productId: 2,
          name: 'Queue Engine',
        },
      ],
    });

    getProductsMock.mockImplementation((page: number, _size: number, search?: string) => {
      expect(page).toBe(1);
      return of(paged(search ? [payments, messaging] : [payments, messaging]));
    });

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const searchInput: HTMLInputElement = fixture.nativeElement.querySelector('#status-search-input');
    searchInput.value = 'checkout';
    searchInput.dispatchEvent(new Event('input'));

    await new Promise((resolve) => setTimeout(resolve, 350));
    fixture.detectChanges();

    expect(getProductsMock).toHaveBeenCalledWith(1, 10, 'checkout');
    expect(fixture.nativeElement.textContent).toContain('Payments');
    expect(fixture.nativeElement.textContent).not.toContain('Messaging');
  });

  it('supports multi-expand and load-more append flow', () => {
    const payments = buildProduct();
    const messaging = buildProduct({
      id: 2,
      name: 'Messaging',
      components: [
        {
          ...buildProduct().components[0],
          id: 202,
          productId: 2,
          name: 'Delivery API',
        },
      ],
    });
    const commerce = buildProduct({
      id: 3,
      name: 'Commerce',
      components: [
        {
          ...buildProduct().components[0],
          id: 301,
          productId: 3,
          name: 'Catalog API',
        },
      ],
    });

    getProductsMock.mockImplementation((page: number) => {
      if (page === 1) {
        return of(paged([payments, messaging], 3));
      }

      return of(paged([commerce], 3));
    });

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const accordionButtons = fixture.debugElement.queryAll(
      By.css('app-product-accordion-item button[aria-controls]'),
    );
    accordionButtons[0].nativeElement.click();
    accordionButtons[1].nativeElement.click();
    fixture.detectChanges();

    const expandedRegions = fixture.debugElement.queryAll(By.css('[role="region"]'));
    expect(expandedRegions.length).toBe(2);

    const loadMoreButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'app-load-more-button button',
    );
    loadMoreButton.click();
    fixture.detectChanges();

    expect(getProductsMock).toHaveBeenCalledWith(2, 10, undefined);
    expect(fixture.nativeElement.textContent).toContain('Commerce');
  });

  it('refreshes every 30 seconds', () => {
    vi.useFakeTimers();

    try {
      getProductsMock.mockReturnValue(of(paged([buildProduct()])));

      const fixture = TestBed.createComponent(StatusPageComponent);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(1);
      expect(getProductsMock).toHaveBeenNthCalledWith(1, 1, 10, undefined);

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(2);
      expect(getProductsMock).toHaveBeenNthCalledWith(2, 1, 10, undefined);
    } finally {
      vi.useRealTimers();
    }
  });

  it('refreshes all loaded pages in background', () => {
    vi.useFakeTimers();

    try {
      const payments = buildProduct();
      const commerce = buildProduct({
        id: 2,
        name: 'Commerce',
      });

      getProductsMock.mockImplementation((page: number) => {
        if (page === 1) {
          return of(paged([payments], 3));
        }

        if (page === 2) {
          return of(paged([commerce], 3));
        }

        return of(paged([], 3));
      });

      const fixture = TestBed.createComponent(StatusPageComponent);
      fixture.detectChanges();

      const loadMoreButton: HTMLButtonElement = fixture.nativeElement.querySelector(
        'app-load-more-button button',
      );
      loadMoreButton.click();
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(2);
      expect(getProductsMock).toHaveBeenNthCalledWith(1, 1, 10, undefined);
      expect(getProductsMock).toHaveBeenNthCalledWith(2, 2, 10, undefined);

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(4);
      expect(getProductsMock).toHaveBeenNthCalledWith(3, 1, 10, undefined);
      expect(getProductsMock).toHaveBeenNthCalledWith(4, 2, 10, undefined);
    } finally {
      vi.useRealTimers();
    }
  });

  it('keeps current data visible when background refresh fails', () => {
    vi.useFakeTimers();

    try {
      let calls = 0;
      const payments = buildProduct();

      getProductsMock.mockImplementation(() => {
        calls += 1;

        if (calls === 1) {
          return of(paged([payments]));
        }

        return throwError(() => new Error('background refresh failed'));
      });

      const fixture = TestBed.createComponent(StatusPageComponent);
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Payments');

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(fixture.nativeElement.textContent).toContain('Payments');
      expect(fixture.nativeElement.textContent).not.toContain('Could not load status data');
    } finally {
      vi.useRealTimers();
    }
  });

  it('uses active query value for auto-refresh requests', () => {
    vi.useFakeTimers();

    try {
      getProductsMock.mockReturnValue(of(paged([buildProduct()])));

      const fixture = TestBed.createComponent(StatusPageComponent);
      fixture.detectChanges();

      const searchInput: HTMLInputElement = fixture.nativeElement.querySelector('#status-search-input');
      searchInput.value = 'checkout';
      searchInput.dispatchEvent(new Event('input'));

      vi.advanceTimersByTime(350);
      fixture.detectChanges();

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(3);
      expect(getProductsMock).toHaveBeenNthCalledWith(2, 1, 10, 'checkout');
      expect(getProductsMock).toHaveBeenNthCalledWith(3, 1, 10, 'checkout');
    } finally {
      vi.useRealTimers();
    }
  });

  it('skips overlapping auto-refresh cycles while one is pending', () => {
    vi.useFakeTimers();

    try {
      const pendingRefresh = new Subject<PagedResponse<ProductApi>>();
      let calls = 0;

      getProductsMock.mockImplementation(() => {
        calls += 1;

        if (calls === 1) {
          return of(paged([buildProduct()]));
        }

        if (calls === 2) {
          return pendingRefresh.asObservable();
        }

        return of(paged([buildProduct()]));
      });

      const fixture = TestBed.createComponent(StatusPageComponent);
      fixture.detectChanges();

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(2);

      vi.advanceTimersByTime(AUTO_REFRESH_INTERVAL_MS);
      fixture.detectChanges();

      expect(getProductsMock).toHaveBeenCalledTimes(2);

      pendingRefresh.complete();
    } finally {
      vi.useRealTimers();
    }
  });

  it('opens add product modal, submits create, and refreshes data', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    createProductMock.mockReturnValue(of(buildProduct({ id: 9, name: 'New Product' })));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const addProductButton = findButtonByText(fixture.nativeElement, 'Add Product');
    addProductButton?.click();
    fixture.detectChanges();

    const nameInput: HTMLInputElement = fixture.nativeElement.querySelector('#product-name-input');
    const descriptionInput: HTMLTextAreaElement = fixture.nativeElement.querySelector(
      '#product-description-input',
    );
    nameInput.value = 'New Product';
    nameInput.dispatchEvent(new Event('input'));
    descriptionInput.value = 'New product description';
    descriptionInput.dispatchEvent(new Event('input'));

    const modalForm: HTMLFormElement = fixture.nativeElement.querySelector('app-product-form-modal form');
    modalForm.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(createProductMock).toHaveBeenCalledWith({
      name: 'New Product',
      description: 'New product description',
    });
    expect(getProductsMock).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.querySelector('app-product-form-modal')).toBeNull();
  });

  it('opens edit product modal with prefilled values and submits update', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    updateProductMock.mockReturnValue(of(buildProduct({ name: 'Payments v2' })));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const editProductButton = findButtonByText(fixture.nativeElement, 'Edit Product');
    editProductButton?.click();
    fixture.detectChanges();

    const nameInput: HTMLInputElement = fixture.nativeElement.querySelector('#product-name-input');
    expect(nameInput.value).toBe('Payments');

    nameInput.value = 'Payments v2';
    nameInput.dispatchEvent(new Event('input'));

    const modalForm: HTMLFormElement = fixture.nativeElement.querySelector('app-product-form-modal form');
    modalForm.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(updateProductMock).toHaveBeenCalledWith(1, {
      name: 'Payments v2',
      description: 'Payment stack',
    });
    expect(fixture.nativeElement.querySelector('app-product-form-modal')).toBeNull();
  });

  it('opens add component modal for selected product and submits create payload', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    createComponentMock.mockReturnValue(of(buildProduct().components[0]));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const expandButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'app-product-accordion-item button[aria-controls]',
    );
    expandButton.click();
    fixture.detectChanges();

    const addComponentButton = findButtonByText(fixture.nativeElement, 'Add Component');
    addComponentButton?.click();
    fixture.detectChanges();

    const nameInput: HTMLInputElement = fixture.nativeElement.querySelector('#component-name-input');
    const healthUrlInput: HTMLInputElement = fixture.nativeElement.querySelector(
      '#component-health-url-input',
    );
    nameInput.value = 'Checkout API 2';
    nameInput.dispatchEvent(new Event('input'));
    healthUrlInput.value = 'https://example.com/health-v2';
    healthUrlInput.dispatchEvent(new Event('input'));

    const modalForm: HTMLFormElement = fixture.nativeElement.querySelector(
      'app-component-form-modal form',
    );
    modalForm.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(createComponentMock).toHaveBeenCalledWith({
      productId: 1,
      name: 'Checkout API 2',
      type: 'BACKEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/health-v2',
        checkIntervalSeconds: 60,
        timeoutSeconds: 30,
        expectedStatusCode: 200,
        maxResponseTimeMs: 5000,
        failuresBeforeOutage: 3,
      },
    });
    expect(fixture.nativeElement.querySelector('app-component-form-modal')).toBeNull();
  });

  it('opens edit component modal with prefilled values and submits update', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    updateComponentMock.mockReturnValue(of(buildProduct().components[0]));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const expandButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'app-product-accordion-item button[aria-controls]',
    );
    expandButton.click();
    fixture.detectChanges();

    const componentCard: HTMLElement | null = fixture.nativeElement.querySelector('app-component-status-card');
    const editComponentButton = componentCard?.querySelector(
      'button[data-action="edit-component"]',
    ) as HTMLButtonElement | null;
    editComponentButton?.click();
    fixture.detectChanges();

    const nameInput: HTMLInputElement = fixture.nativeElement.querySelector('#component-name-input');
    const healthUrlInput: HTMLInputElement = fixture.nativeElement.querySelector(
      '#component-health-url-input',
    );
    expect(nameInput.value).toBe('Checkout API');
    expect(healthUrlInput.value).toBe('https://example.com/health');

    nameInput.value = 'Checkout API Updated';
    nameInput.dispatchEvent(new Event('input'));
    healthUrlInput.value = 'https://example.com/health-updated';
    healthUrlInput.dispatchEvent(new Event('input'));

    const modalForm: HTMLFormElement = fixture.nativeElement.querySelector(
      'app-component-form-modal form',
    );
    modalForm.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(updateComponentMock).toHaveBeenCalledWith(101, {
      name: 'Checkout API Updated',
      type: 'BACKEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/health-updated',
        checkIntervalSeconds: 60,
        timeoutSeconds: 30,
        expectedStatusCode: 200,
        maxResponseTimeMs: 5000,
        failuresBeforeOutage: 3,
      },
    });
    expect(fixture.nativeElement.querySelector('app-component-form-modal')).toBeNull();
  });

  it('opens remove product confirmation, submits delete, and refreshes data', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    deleteProductMock.mockReturnValue(of(void 0));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const removeProductButton = fixture.nativeElement.querySelector(
      'button[data-action="remove-product"]',
    ) as HTMLButtonElement | null;
    removeProductButton?.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('app-confirm-action-modal')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Are you sure you want to remove "Payments"');

    const confirmModal = fixture.nativeElement.querySelector('app-confirm-action-modal') as
      | HTMLElement
      | null;
    const confirmButton = confirmModal ? findButtonByText(confirmModal, 'Remove Product') : null;
    confirmButton?.click();
    fixture.detectChanges();

    expect(deleteProductMock).toHaveBeenCalledWith(1);
    expect(getProductsMock).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.querySelector('app-confirm-action-modal')).toBeNull();
  });

  it('opens remove component confirmation, submits delete, and refreshes data', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    deleteComponentMock.mockReturnValue(of(void 0));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const expandButton: HTMLButtonElement = fixture.nativeElement.querySelector(
      'app-product-accordion-item button[aria-controls]',
    );
    expandButton.click();
    fixture.detectChanges();

    const componentCard: HTMLElement | null = fixture.nativeElement.querySelector('app-component-status-card');
    const removeComponentButton = componentCard?.querySelector(
      'button[data-action="remove-component"]',
    ) as HTMLButtonElement | null;
    removeComponentButton?.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('app-confirm-action-modal')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain(
      'Are you sure you want to remove "Checkout API"',
    );

    const confirmButton = findButtonByText(fixture.nativeElement, 'Remove Component');
    confirmButton?.click();
    fixture.detectChanges();

    expect(deleteComponentMock).toHaveBeenCalledWith(101);
    expect(getProductsMock).toHaveBeenCalledTimes(2);
    expect(fixture.nativeElement.querySelector('app-confirm-action-modal')).toBeNull();
  });

  it('keeps remove confirmation open and shows inline error when delete fails', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    deleteProductMock.mockReturnValue(throwError(() => new Error('delete failed')));

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const removeProductButton = fixture.nativeElement.querySelector(
      'button[data-action="remove-product"]',
    ) as HTMLButtonElement | null;
    removeProductButton?.click();
    fixture.detectChanges();

    const confirmModal = fixture.nativeElement.querySelector('app-confirm-action-modal') as
      | HTMLElement
      | null;
    const confirmButton = confirmModal ? findButtonByText(confirmModal, 'Remove Product') : null;
    confirmButton?.click();
    fixture.detectChanges();

    expect(deleteProductMock).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.querySelector('app-confirm-action-modal')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('Unable to remove item. Please try again.');
    expect(fixture.nativeElement.textContent).not.toContain('Could not load status data');
  });

  it('keeps modal open and shows inline validation error when mutation fails', () => {
    getProductsMock.mockReturnValue(of(paged([buildProduct()])));
    createProductMock.mockReturnValue(
      throwError(
        () =>
          new HttpErrorResponse({
            status: 422,
            error: {
              detail: [
                {
                  loc: ['body', 'name'],
                  msg: 'field required',
                },
              ],
            },
          }),
      ),
    );

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const addProductButton = findButtonByText(fixture.nativeElement, 'Add Product');
    addProductButton?.click();
    fixture.detectChanges();

    const nameInput: HTMLInputElement = fixture.nativeElement.querySelector('#product-name-input');
    nameInput.value = 'A';
    nameInput.dispatchEvent(new Event('input'));

    const modalForm: HTMLFormElement = fixture.nativeElement.querySelector('app-product-form-modal form');
    modalForm.dispatchEvent(new Event('submit'));
    fixture.detectChanges();

    expect(createProductMock).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.querySelector('app-product-form-modal')).not.toBeNull();
    expect(fixture.nativeElement.textContent).toContain('body.name: field required');
    expect(fixture.nativeElement.textContent).not.toContain('Could not load status data');
  });
});
