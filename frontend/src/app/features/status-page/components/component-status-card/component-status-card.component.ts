import { Component, computed, input } from '@angular/core';

import { ComponentViewModel } from '../../../../core/models/status.models';
import { StatusBadgeComponent } from '../status-badge/status-badge.component';

@Component({
  selector: 'app-component-status-card',
  standalone: true,
  imports: [StatusBadgeComponent],
  templateUrl: './component-status-card.component.html',
})
export class ComponentStatusCardComponent {
  readonly component = input.required<ComponentViewModel>();

  readonly uptimeText = computed(() => {
    const uptime = this.component().latestUptime;
    return uptime === null ? 'No uptime data yet' : `${uptime.toFixed(1)}% uptime`;
  });

  readonly avgResponseTimeText = computed(() => {
    const average = this.component().latestAvgResponseTimeMs;
    return average === null ? 'No latency data yet' : `${average.toFixed(0)} ms avg`;
  });
}
