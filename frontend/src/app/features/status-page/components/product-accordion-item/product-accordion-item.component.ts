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

  readonly componentCount = computed(() => this.product().components.length);

  onToggle(): void {
    this.toggled.emit(this.product().id);
  }
}
