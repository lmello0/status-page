import { Component, input, output } from '@angular/core';

import { ProductViewModel } from '../../../../core/models/status.models';
import { ProductAccordionItemComponent } from '../product-accordion-item/product-accordion-item.component';

@Component({
  selector: 'app-product-tree',
  standalone: true,
  imports: [ProductAccordionItemComponent],
  templateUrl: './product-tree.component.html',
})
export class ProductTreeComponent {
  readonly products = input.required<ProductViewModel[]>();
  readonly expandedProductIds = input.required<Set<number>>();
  readonly toggled = output<number>();

  onToggle(productId: number): void {
    this.toggled.emit(productId);
  }
}
