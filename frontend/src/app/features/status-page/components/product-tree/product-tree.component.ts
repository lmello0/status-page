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
  readonly editProduct = output<number>();
  readonly removeProduct = output<number>();
  readonly addComponent = output<number>();
  readonly editComponent = output<number>();
  readonly removeComponent = output<number>();

  onToggle(productId: number): void {
    this.toggled.emit(productId);
  }

  onEditProduct(productId: number): void {
    this.editProduct.emit(productId);
  }

  onRemoveProduct(productId: number): void {
    this.removeProduct.emit(productId);
  }

  onAddComponent(productId: number): void {
    this.addComponent.emit(productId);
  }

  onEditComponent(componentId: number): void {
    this.editComponent.emit(componentId);
  }

  onRemoveComponent(componentId: number): void {
    this.removeComponent.emit(componentId);
  }
}
