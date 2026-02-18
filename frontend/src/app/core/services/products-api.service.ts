import { inject, Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { PagedResponse, ProductApi } from '../models/status.models';

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
}
