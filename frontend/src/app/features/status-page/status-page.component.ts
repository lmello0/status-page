import { DestroyRef, OnDestroy, OnInit, Component, computed, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import {
  debounceTime,
  distinctUntilChanged,
  finalize,
  forkJoin,
  interval,
  map,
  Observable,
  of,
  skip,
  Subscription,
  switchMap,
} from 'rxjs';

import {
  ComponentCreateDto,
  ComponentUpdateDto,
  PagedResponse,
  ProductApi,
  ProductCreateDto,
  ProductUpdateDto,
  ProductViewModel,
} from '../../core/models/status.models';
import { mapProducts, filterProductsByQuery } from '../../core/mappers/status.mapper';
import { ProductsApiService } from '../../core/services/products-api.service';
import { ConfirmActionModalComponent } from './components/confirm-action-modal/confirm-action-modal.component';
import {
  ComponentFormInitialValue,
  ComponentFormModalComponent,
} from './components/component-form-modal/component-form-modal.component';
import { LoadMoreButtonComponent } from './components/load-more-button/load-more-button.component';
import {
  ProductFormInitialValue,
  ProductFormModalComponent,
} from './components/product-form-modal/product-form-modal.component';
import { ProductTreeComponent } from './components/product-tree/product-tree.component';
import { StatePanelComponent } from './components/state-panel/state-panel.component';
import { StatusSearchComponent } from './components/status-search/status-search.component';

const PAGE_SIZE = 10;
const AUTO_REFRESH_INTERVAL_MS = 30_000;

type ActiveModalState =
  | { kind: 'none' }
  | { kind: 'product-create' }
  | { kind: 'product-edit'; productId: number }
  | { kind: 'product-delete'; productId: number }
  | { kind: 'component-create'; productId: number }
  | { kind: 'component-edit'; componentId: number }
  | { kind: 'component-delete'; componentId: number };

@Component({
  selector: 'app-status-page',
  standalone: true,
  imports: [
    ConfirmActionModalComponent,
    ComponentFormModalComponent,
    LoadMoreButtonComponent,
    ProductFormModalComponent,
    ProductTreeComponent,
    StatePanelComponent,
    StatusSearchComponent,
  ],
  templateUrl: './status-page.component.html',
  styleUrl: './status-page.component.css',
})
export class StatusPageComponent implements OnInit, OnDestroy {
  private readonly productsApi = inject(ProductsApiService);
  private readonly destroyRef = inject(DestroyRef);

  private activeRequest: Subscription | null = null;
  private autoRefreshRequest: Subscription | null = null;
  private isAutoRefreshing = false;

  readonly query = signal('');
  private readonly query$ = toObservable(this.query);
  readonly serverItems = signal<ProductViewModel[]>([]);
  readonly page = signal(-1);
  readonly totalPages = signal(0);
  readonly isLoading = signal(false);
  readonly isLoadingMore = signal(false);
  readonly error = signal<string | null>(null);
  readonly expandedProductIds = signal<Set<number>>(new Set());
  readonly activeModal = signal<ActiveModalState>({ kind: 'none' });
  readonly modalError = signal<string | null>(null);
  readonly isSaving = signal(false);

  readonly isProductModalOpen = computed(() => {
    const modal = this.activeModal();
    return modal.kind === 'product-create' || modal.kind === 'product-edit';
  });

  readonly isComponentModalOpen = computed(() => {
    const modal = this.activeModal();
    return modal.kind === 'component-create' || modal.kind === 'component-edit';
  });

  readonly isConfirmModalOpen = computed(() => {
    const modal = this.activeModal();
    return modal.kind === 'product-delete' || modal.kind === 'component-delete';
  });

  readonly productModalMode = computed(() =>
    this.activeModal().kind === 'product-edit' ? 'edit' : 'create',
  );

  readonly componentModalMode = computed(() =>
    this.activeModal().kind === 'component-edit' ? 'edit' : 'create',
  );

  readonly productModalInitialValue = computed<ProductFormInitialValue | null>(() => {
    const modal = this.activeModal();

    if (modal.kind !== 'product-edit') {
      return null;
    }

    const product = this.findProductById(modal.productId);

    if (!product) {
      return null;
    }

    return {
      name: product.name,
      description: product.description === 'No description provided' ? null : product.description,
    };
  });

  readonly componentModalProductId = computed<number | null>(() => {
    const modal = this.activeModal();

    if (modal.kind === 'component-create') {
      return modal.productId;
    }

    if (modal.kind === 'component-edit') {
      return this.findComponentById(modal.componentId)?.productId ?? null;
    }

    return null;
  });

  readonly componentModalInitialValue = computed<ComponentFormInitialValue | null>(() => {
    const modal = this.activeModal();

    if (modal.kind !== 'component-edit') {
      return null;
    }

    const component = this.findComponentById(modal.componentId);

    if (!component) {
      return null;
    }

    return {
      name: component.name,
      type: component.type,
      monitoringConfig: component.monitoringConfig,
    };
  });

  readonly confirmModalTitle = computed(() => {
    const modal = this.activeModal();

    if (modal.kind === 'product-delete') {
      return 'Remove Product';
    }

    if (modal.kind === 'component-delete') {
      return 'Remove Component';
    }

    return '';
  });

  readonly confirmModalMessage = computed(() => {
    const modal = this.activeModal();

    if (modal.kind === 'product-delete') {
      const product = this.findProductById(modal.productId);

      if (product) {
        return `Are you sure you want to remove "${product.name}"? This action cannot be undone.`;
      }

      return 'This product is no longer available.';
    }

    if (modal.kind === 'component-delete') {
      const component = this.findComponentById(modal.componentId);

      if (component) {
        return `Are you sure you want to remove "${component.name}"? This action cannot be undone.`;
      }

      return 'This component is no longer available.';
    }

    return '';
  });

  readonly confirmModalConfirmLabel = computed(() => {
    const modal = this.activeModal();

    if (modal.kind === 'product-delete') {
      return 'Remove Product';
    }

    if (modal.kind === 'component-delete') {
      return 'Remove Component';
    }

    return 'Remove';
  });

  readonly confirmTargetExists = computed(() => {
    const modal = this.activeModal();

    if (modal.kind === 'product-delete') {
      return this.findProductById(modal.productId) !== undefined;
    }

    if (modal.kind === 'component-delete') {
      return this.findComponentById(modal.componentId) !== undefined;
    }

    return false;
  });

  readonly filteredItems = computed(() => filterProductsByQuery(this.serverItems(), this.query()));
  readonly hasMore = computed(() => this.page() + 1 < this.totalPages());
  readonly showInitialLoading = computed(() => this.isLoading() && this.serverItems().length === 0);
  readonly showEmpty = computed(
    () => !this.showInitialLoading() && !this.error() && this.filteredItems().length === 0,
  );
  readonly summary = computed(() => {
    const loaded = this.serverItems().length;
    const visible = this.filteredItems().length;
    const normalizedQuery = this.query().trim();

    if (!loaded && this.isLoading()) {
      return 'Loading products...';
    }

    if (!normalizedQuery) {
      return `${loaded} products loaded`;
    }

    return `Showing ${visible} of ${loaded} loaded products`;
  });

  ngOnInit(): void {
    this.fetchPage(1, true);

    this.query$
      .pipe(skip(1), debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.fetchPage(1, true);
      });

    interval(AUTO_REFRESH_INTERVAL_MS)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.refreshDashboard();
      });
  }

  ngOnDestroy(): void {
    this.activeRequest?.unsubscribe();
    this.autoRefreshRequest?.unsubscribe();
  }

  onQueryChange(value: string): void {
    this.query.set(value);
  }

  onToggleProduct(productId: number): void {
    const nextExpanded = new Set(this.expandedProductIds());

    if (nextExpanded.has(productId)) {
      nextExpanded.delete(productId);
    } else {
      nextExpanded.add(productId);
    }

    this.expandedProductIds.set(nextExpanded);
  }

  onLoadMore(): void {
    if (!this.hasMore() || this.isLoading() || this.isLoadingMore()) {
      return;
    }

    this.fetchPage(this.page() + 1, false);
  }

  onRetry(): void {
    this.fetchPage(1, true);
  }

  onAddProduct(): void {
    this.activeModal.set({ kind: 'product-create' });
    this.modalError.set(null);
  }

  onEditProduct(productId: number): void {
    if (!this.findProductById(productId)) {
      return;
    }

    this.activeModal.set({ kind: 'product-edit', productId });
    this.modalError.set(null);
  }

  onAddComponent(productId: number): void {
    if (!this.findProductById(productId)) {
      return;
    }

    this.activeModal.set({ kind: 'component-create', productId });
    this.modalError.set(null);
  }

  onRemoveProduct(productId: number): void {
    if (!this.findProductById(productId)) {
      return;
    }

    this.activeModal.set({ kind: 'product-delete', productId });
    this.modalError.set(null);
  }

  onEditComponent(componentId: number): void {
    if (!this.findComponentById(componentId)) {
      return;
    }

    this.activeModal.set({ kind: 'component-edit', componentId });
    this.modalError.set(null);
  }

  onRemoveComponent(componentId: number): void {
    if (!this.findComponentById(componentId)) {
      return;
    }

    this.activeModal.set({ kind: 'component-delete', componentId });
    this.modalError.set(null);
  }

  onProductSubmit(payload: ProductCreateDto | ProductUpdateDto): void {
    const modal = this.activeModal();

    if (modal.kind === 'product-create') {
      this.executeMutation(this.productsApi.createProduct(payload as ProductCreateDto));
      return;
    }

    if (modal.kind === 'product-edit') {
      this.executeMutation(
        this.productsApi.updateProduct(modal.productId, payload as ProductUpdateDto),
      );
    }
  }

  onComponentSubmit(payload: ComponentCreateDto | ComponentUpdateDto): void {
    const modal = this.activeModal();

    if (modal.kind === 'component-create') {
      this.executeMutation(this.productsApi.createComponent(payload as ComponentCreateDto));
      return;
    }

    if (modal.kind === 'component-edit') {
      this.executeMutation(
        this.productsApi.updateComponent(modal.componentId, payload as ComponentUpdateDto),
      );
    }
  }

  onConfirmRemove(): void {
    const modal = this.activeModal();

    if (modal.kind === 'product-delete') {
      if (!this.findProductById(modal.productId)) {
        this.onModalClose();
        return;
      }

      this.executeMutation(
        this.productsApi.deleteProduct(modal.productId),
        'Unable to remove item. Please try again.',
      );
      return;
    }

    if (modal.kind === 'component-delete') {
      if (!this.findComponentById(modal.componentId)) {
        this.onModalClose();
        return;
      }

      this.executeMutation(
        this.productsApi.deleteComponent(modal.componentId),
        'Unable to remove item. Please try again.',
      );
    }
  }

  onModalClose(): void {
    if (this.isSaving()) {
      return;
    }

    this.activeModal.set({ kind: 'none' });
    this.modalError.set(null);
  }

  private fetchPage(targetPage: number, reset: boolean): void {
    if (this.isAutoRefreshing) {
      this.autoRefreshRequest?.unsubscribe();
    }

    if (!reset && (this.isLoading() || this.isLoadingMore())) {
      return;
    }

    if (reset) {
      this.activeRequest?.unsubscribe();
      this.isLoading.set(true);
      this.error.set(null);
    } else {
      this.isLoadingMore.set(true);
    }

    const normalizedQuery = this.query().trim();

    this.activeRequest = this.productsApi
      .getProducts(targetPage, PAGE_SIZE, normalizedQuery || undefined)
      .pipe(
        finalize(() => {
          if (reset) {
            this.isLoading.set(false);
          } else {
            this.isLoadingMore.set(false);
          }
        }),
      )
      .subscribe({
        next: (response) => {
          const mappedProducts = mapProducts(response.content ?? []);
          const merged = reset
            ? mappedProducts
            : this.mergeProducts(this.serverItems(), mappedProducts);

          this.serverItems.set(merged);
          this.page.set(targetPage);
          this.totalPages.set(Math.max(response.totalPages ?? 0, targetPage + 1));
          this.pruneExpandedProducts(merged);
          this.error.set(null);
        },
        error: () => {
          if (reset) {
            this.serverItems.set([]);
            this.page.set(-1);
            this.totalPages.set(0);
            this.expandedProductIds.set(new Set());
          }

          this.error.set('Unable to load status data. Please try again.');
        },
      });
  }

  private refreshDashboard(): void {
    if (this.isLoading() || this.isLoadingMore() || this.isAutoRefreshing) {
      return;
    }

    const currentPage = Math.max(this.page(), 1);
    const normalizedQuery = this.query().trim() || undefined;
    this.isAutoRefreshing = true;

    this.autoRefreshRequest = this.productsApi
      .getProducts(1, PAGE_SIZE, normalizedQuery)
      .pipe(
        switchMap((firstResponse) => {
          const maxPageFromFirst = Math.max(firstResponse.totalPages ?? 0, 1);
          const effectiveMaxPage = Math.min(currentPage, maxPageFromFirst);

          if (effectiveMaxPage <= 1) {
            return of({
              firstResponse,
              effectiveMaxPage,
              additionalResponses: [] as PagedResponse<ProductApi>[],
            });
          }

          const additionalRequests: Observable<PagedResponse<ProductApi>>[] = [];

          for (let page = 2; page <= effectiveMaxPage; page++) {
            additionalRequests.push(this.productsApi.getProducts(page, PAGE_SIZE, normalizedQuery));
          }

          return forkJoin(additionalRequests).pipe(
            map((additionalResponses) => ({
              firstResponse,
              effectiveMaxPage,
              additionalResponses,
            })),
          );
        }),
        finalize(() => {
          this.isAutoRefreshing = false;
          this.autoRefreshRequest = null;
        }),
      )
      .subscribe({
        next: ({ firstResponse, effectiveMaxPage, additionalResponses }) => {
          const refreshedProducts = this.buildRefreshedProducts([firstResponse, ...additionalResponses]);

          this.serverItems.set(refreshedProducts);
          this.page.set(effectiveMaxPage);
          this.totalPages.set(Math.max(firstResponse.totalPages ?? 0, effectiveMaxPage + 1));
          this.pruneExpandedProducts(refreshedProducts);
          this.error.set(null);
        },
        error: () => {
          if (this.serverItems().length === 0) {
            this.error.set('Unable to load status data. Please try again.');
          }
        },
      });
  }

  private executeMutation(
    request$: Observable<unknown>,
    fallbackErrorMessage = 'Unable to save changes. Please try again.',
  ): void {
    if (this.isSaving()) {
      return;
    }

    this.isSaving.set(true);
    this.modalError.set(null);

    request$
      .pipe(
        finalize(() => {
          this.isSaving.set(false);
        }),
      )
      .subscribe({
        next: () => {
          this.activeModal.set({ kind: 'none' });
          this.modalError.set(null);
          this.refreshDashboard();
        },
        error: (error: unknown) => {
          this.modalError.set(this.resolveMutationError(error, fallbackErrorMessage));
        },
      });
  }

  private resolveMutationError(error: unknown, fallbackErrorMessage: string): string {
    if (!(error instanceof HttpErrorResponse)) {
      return fallbackErrorMessage;
    }

    if (error.status === 422) {
      const detail = (error.error as { detail?: Array<{ loc?: Array<string | number>; msg?: string }> })
        ?.detail;

      if (Array.isArray(detail) && detail.length) {
        return detail
          .map((item) => {
            const location = Array.isArray(item.loc) ? item.loc.join('.') : 'request';
            const message = item.msg ?? 'invalid value';
            return `${location}: ${message}`;
          })
          .join(' | ');
      }
    }

    return fallbackErrorMessage;
  }

  private buildRefreshedProducts(responses: PagedResponse<ProductApi>[]): ProductViewModel[] {
    const dedupedProducts: ProductViewModel[] = [];
    const seenProductIds = new Set<number>();

    for (const response of responses) {
      const mappedProducts = mapProducts(response.content ?? []);

      for (const product of mappedProducts) {
        if (seenProductIds.has(product.id)) {
          continue;
        }

        seenProductIds.add(product.id);
        dedupedProducts.push(product);
      }
    }

    return dedupedProducts;
  }

  private mergeProducts(
    currentProducts: ProductViewModel[],
    incomingProducts: ProductViewModel[],
  ): ProductViewModel[] {
    const merged = new Map<number, ProductViewModel>();

    for (const product of currentProducts) {
      merged.set(product.id, product);
    }

    for (const product of incomingProducts) {
      merged.set(product.id, product);
    }

    return [...merged.values()];
  }

  private pruneExpandedProducts(products: ProductViewModel[]): void {
    const availableIds = new Set(products.map((product) => product.id));
    const nextExpanded = new Set(
      [...this.expandedProductIds()].filter((productId) => availableIds.has(productId)),
    );

    this.expandedProductIds.set(nextExpanded);
  }

  private findProductById(productId: number): ProductViewModel | undefined {
    return this.serverItems().find((product) => product.id === productId);
  }

  private findComponentById(componentId: number) {
    for (const product of this.serverItems()) {
      const component = product.components.find((item) => item.id === componentId);

      if (component) {
        return component;
      }
    }

    return undefined;
  }
}
