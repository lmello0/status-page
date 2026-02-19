import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  ComponentCreateDto,
  ComponentUpdateDto,
  PagedResponse,
  ProductApi,
  ProductComponentApi,
  ProductCreateDto,
  ProductUpdateDto,
} from '../models/status.models';

@Injectable({
  providedIn: 'root',
})
export class ProductsApiService {
  private readonly http = inject(HttpClient);

  getProducts(page: number, size: number, search?: string): Observable<PagedResponse<ProductApi>> {
    let params = new HttpParams().set('page', `${page}`).set('page_size', `${size}`);
    const normalizedSearch = search?.trim();

    if (normalizedSearch) {
      params = params.set('search', normalizedSearch);
    }

    return this.http.get<PagedResponse<ProductApi>>(`${environment.apiBaseUrl}/product`, {
      params,
    });
  }

  createProduct(payload: ProductCreateDto): Observable<ProductApi> {
    return this.http.post<ProductApi>(`${environment.apiBaseUrl}/product`, payload);
  }

  updateProduct(productId: number, payload: ProductUpdateDto): Observable<ProductApi> {
    payload = Object.fromEntries(
      Object.entries(payload).map(([key, value]) => [key, value === null ? '' : value]),
    );

    return this.http.patch<ProductApi>(`${environment.apiBaseUrl}/product/${productId}`, payload);
  }

  deleteProduct(productId: number): Observable<void> {
    return this.http.delete<void>(`${environment.apiBaseUrl}/product/${productId}`);
  }

  createComponent(payload: ComponentCreateDto): Observable<ProductComponentApi> {
    return this.http.post<ProductComponentApi>(`${environment.apiBaseUrl}/component`, payload);
  }

  updateComponent(
    componentId: number,
    payload: ComponentUpdateDto,
  ): Observable<ProductComponentApi> {
    payload = Object.fromEntries(
      Object.entries(payload).map(([key, value]) => [key, value === null ? '' : value]),
    );

    return this.http.patch<ProductComponentApi>(
      `${environment.apiBaseUrl}/component/${componentId}`,
      payload,
    );
  }

  deleteComponent(componentId: number): Observable<void> {
    return this.http.delete<void>(`${environment.apiBaseUrl}/component/${componentId}`);
  }
}
