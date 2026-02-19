import { Component, computed, input, output } from '@angular/core';

import { ProductViewModel } from '../../../../core/models/status.models';
import { ComponentStatusCardComponent } from '../component-status-card/component-status-card.component';
import { StatusBadgeComponent } from '../status-badge/status-badge.component';

@Component({
  selector: 'app-product-accordion-item',
  standalone: true,
  imports: [StatusBadgeComponent, ComponentStatusCardComponent],
  templateUrl: './product-accordion-item.component.html',
})
export class ProductAccordionItemComponent {
  readonly product = input.required<ProductViewModel>();
  readonly expanded = input(false);
  readonly toggled = output<number>();
  readonly editProduct = output<number>();
  readonly removeProduct = output<number>();
  readonly addComponent = output<number>();
  readonly editComponent = output<number>();
  readonly removeComponent = output<number>();

  readonly componentCount = computed(() => this.product().components.length);

  onToggle(): void {
    this.toggled.emit(this.product().id);
  }

  onEditProduct(): void {
    this.editProduct.emit(this.product().id);
  }

  onRemoveProduct(): void {
    this.removeProduct.emit(this.product().id);
  }

  onAddComponent(): void {
    this.addComponent.emit(this.product().id);
  }

  onEditComponent(componentId: number): void {
    this.editComponent.emit(componentId);
  }

  onRemoveComponent(componentId: number): void {
    this.removeComponent.emit(componentId);
  }
}
