import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, Subject, throwError } from 'rxjs';

import { PagedResponse, ProductApi } from '../../core/models/status.models';
import { ProductsApiService } from '../../core/services/products-api.service';
import { StatusPageComponent } from './status-page.component';

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

describe('StatusPageComponent', () => {
  let getProductsMock: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    getProductsMock = vi.fn();

    await TestBed.configureTestingModule({
      imports: [StatusPageComponent],
      providers: [
        {
          provide: ProductsApiService,
          useValue: {
            getProducts: getProductsMock,
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
      expect(page).toBe(0);
      return of(paged(search ? [payments, messaging] : [payments, messaging]));
    });

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const searchInput: HTMLInputElement = fixture.nativeElement.querySelector('#status-search-input');
    searchInput.value = 'checkout';
    searchInput.dispatchEvent(new Event('input'));

    await new Promise((resolve) => setTimeout(resolve, 350));
    fixture.detectChanges();

    expect(getProductsMock).toHaveBeenCalledWith(0, 10, 'checkout');
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
      if (page === 0) {
        return of(paged([payments, messaging], 2));
      }

      return of(paged([commerce], 2));
    });

    const fixture = TestBed.createComponent(StatusPageComponent);
    fixture.detectChanges();

    const accordionButtons = fixture.debugElement.queryAll(By.css('app-product-accordion-item button'));
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

    expect(getProductsMock).toHaveBeenCalledWith(1, 10, undefined);
    expect(fixture.nativeElement.textContent).toContain('Commerce');
  });
});
