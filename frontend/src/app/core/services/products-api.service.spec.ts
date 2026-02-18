import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

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

  it('requests products with page and size params', () => {
    service.getProducts(0, 10).subscribe();

    const request = httpMock.expectOne((req) => req.url === '/api/products');

    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('page')).toBe('0');
    expect(request.request.params.get('size')).toBe('10');
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

    const request = httpMock.expectOne((req) => req.url === '/api/products');

    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('size')).toBe('10');
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

    const request = httpMock.expectOne((req) => req.url === '/api/products');

    expect(request.request.params.has('search')).toBe(false);

    request.flush({
      pageSize: 10,
      pageCount: 1,
      totalElements: 0,
      totalPages: 0,
      content: [],
    });
  });
});
