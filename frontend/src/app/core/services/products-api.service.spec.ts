import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { ProductsApiService } from './products-api.service';

describe('ProductsApiService', () => {
  let service: ProductsApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [ProductsApiService, provideHttpClient(), provideHttpClientTesting()],
    });

    service = TestBed.inject(ProductsApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('requests products with page and page_size params', () => {
    service.getProducts(0, 10).subscribe();

    const request = httpMock.expectOne((req) => req.url === `${environment.apiBaseUrl}/product`);

    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('page')).toBe('0');
    expect(request.request.params.get('page_size')).toBe('10');
    expect(request.request.params.has('search')).toBe(false);

    request.flush({
      pageSize: 10,
      pageCount: 1,
      totalElements: 0,
      totalPages: 0,
      content: [],
    });
  });

  it('sends search param for filtered requests', () => {
    service.getProducts(2, 10, 'payments').subscribe();

    const request = httpMock.expectOne((req) => req.url === `${environment.apiBaseUrl}/product`);

    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('page_size')).toBe('10');
    expect(request.request.params.get('search')).toBe('payments');

    request.flush({
      pageSize: 10,
      pageCount: 1,
      totalElements: 0,
      totalPages: 0,
      content: [],
    });
  });

  it('omits search when only whitespace is provided', () => {
    service.getProducts(0, 10, '   ').subscribe();

    const request = httpMock.expectOne((req) => req.url === `${environment.apiBaseUrl}/product`);

    expect(request.request.params.has('search')).toBe(false);

    request.flush({
      pageSize: 10,
      pageCount: 1,
      totalElements: 0,
      totalPages: 0,
      content: [],
    });
  });

  it('creates a product', () => {
    service.createProduct({ name: 'Payments', description: 'Payment stack' }).subscribe();

    const request = httpMock.expectOne((req) => req.url === `${environment.apiBaseUrl}/product`);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      name: 'Payments',
      description: 'Payment stack',
    });

    request.flush({
      id: 1,
      name: 'Payments',
      description: 'Payment stack',
      isVisible: true,
      createdAt: '2026-02-19T00:00:00Z',
      updatedAt: '2026-02-19T00:00:00Z',
      components: [],
    });
  });

  it('updates a product', () => {
    service.updateProduct(7, { name: 'Commerce', description: null }).subscribe();

    const request = httpMock.expectOne(
      (req) => req.url === `${environment.apiBaseUrl}/product/7`,
    );

    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({
      name: 'Commerce',
      description: null,
    });

    request.flush({
      id: 7,
      name: 'Commerce',
      description: null,
      isVisible: true,
      createdAt: '2026-02-19T00:00:00Z',
      updatedAt: '2026-02-19T00:00:00Z',
      components: [],
    });
  });

  it('creates a component', () => {
    service
      .createComponent({
        productId: 3,
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
      })
      .subscribe();

    const request = httpMock.expectOne((req) => req.url === `${environment.apiBaseUrl}/component`);

    expect(request.request.method).toBe('POST');
    expect(request.request.body.productId).toBe(3);
    expect(request.request.body.name).toBe('Checkout API');
    expect(request.request.body.type).toBe('BACKEND');
    expect(request.request.body.monitoringConfig.healthUrl).toBe('https://example.com/health');

    request.flush({
      id: 99,
      productId: 3,
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
      healthcheckDayLogs: [],
    });
  });

  it('updates a component', () => {
    service
      .updateComponent(55, {
        name: 'Checkout API v2',
        type: 'FRONTEND',
        monitoringConfig: {
          healthUrl: 'https://example.com/checkout',
          checkIntervalSeconds: 45,
          timeoutSeconds: 20,
          expectedStatusCode: 200,
          maxResponseTimeMs: 3000,
          failuresBeforeOutage: 2,
        },
      })
      .subscribe();

    const request = httpMock.expectOne(
      (req) => req.url === `${environment.apiBaseUrl}/component/55`,
    );

    expect(request.request.method).toBe('PATCH');
    expect(request.request.body.name).toBe('Checkout API v2');
    expect(request.request.body.type).toBe('FRONTEND');
    expect(request.request.body.monitoringConfig.checkIntervalSeconds).toBe(45);

    request.flush({
      id: 55,
      productId: 3,
      name: 'Checkout API v2',
      type: 'FRONTEND',
      monitoringConfig: {
        healthUrl: 'https://example.com/checkout',
        checkIntervalSeconds: 45,
        timeoutSeconds: 20,
        expectedStatusCode: 200,
        maxResponseTimeMs: 3000,
        failuresBeforeOutage: 2,
      },
      currentStatus: 'DEGRADED',
      isActive: true,
      healthcheckDayLogs: [],
    });
  });

  it('deletes a product', () => {
    service.deleteProduct(9).subscribe();

    const request = httpMock.expectOne(
      (req) => req.url === `${environment.apiBaseUrl}/product/9`,
    );

    expect(request.request.method).toBe('DELETE');

    request.flush(null, {
      status: 204,
      statusText: 'No Content',
    });
  });

  it('deletes a component', () => {
    service.deleteComponent(42).subscribe();

    const request = httpMock.expectOne(
      (req) => req.url === `${environment.apiBaseUrl}/component/42`,
    );

    expect(request.request.method).toBe('DELETE');

    request.flush(null, {
      status: 204,
      statusText: 'No Content',
    });
  });
});
