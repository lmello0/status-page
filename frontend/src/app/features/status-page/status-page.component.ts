import { DestroyRef, OnDestroy, OnInit, Component, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, finalize, skip, Subscription } from 'rxjs';

import { ProductViewModel } from '../../core/models/status.models';
import { mapProducts, filterProductsByQuery } from '../../core/mappers/status.mapper';
import { ProductsApiService } from '../../core/services/products-api.service';
import { LoadMoreButtonComponent } from './components/load-more-button/load-more-button.component';
import { ProductTreeComponent } from './components/product-tree/product-tree.component';
import { StatePanelComponent } from './components/state-panel/state-panel.component';
import { StatusSearchComponent } from './components/status-search/status-search.component';

const PAGE_SIZE = 10;

@Component({
  selector: 'app-status-page',
  standalone: true,
  imports: [
    LoadMoreButtonComponent,
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

  readonly query = signal('');
  private readonly query$ = toObservable(this.query);
  readonly serverItems = signal<ProductViewModel[]>([]);
  readonly page = signal(-1);
  readonly totalPages = signal(0);
  readonly isLoading = signal(false);
  readonly isLoadingMore = signal(false);
  readonly error = signal<string | null>(null);
  readonly expandedProductIds = signal<Set<number>>(new Set());

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
  }

  ngOnDestroy(): void {
    this.activeRequest?.unsubscribe();
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

  private fetchPage(targetPage: number, reset: boolean): void {
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
}
