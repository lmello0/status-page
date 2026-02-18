import { NgClass } from '@angular/common';
import { Component, computed, input } from '@angular/core';

import { StatusLevel } from '../../../../core/models/status.models';
import { statusToLabel } from '../../../../core/utils/status-severity';

@Component({
  selector: 'app-status-badge',
  standalone: true,
  imports: [NgClass],
  templateUrl: './status-badge.component.html',
})
export class StatusBadgeComponent {
  readonly status = input<StatusLevel>('UNKNOWN');

  readonly label = computed(() => statusToLabel(this.status()));

  readonly toneClasses = computed(() => {
    switch (this.status()) {
      case 'OPERATIONAL':
        return 'bg-emerald-500/15 text-emerald-200 ring-emerald-400/30';
      case 'DEGRADED':
        return 'bg-amber-500/15 text-amber-200 ring-amber-400/30';
      case 'PARTIAL_OUTAGE':
        return 'bg-orange-500/15 text-orange-200 ring-orange-400/30';
      case 'MAJOR_OUTAGE':
        return 'bg-rose-500/20 text-rose-200 ring-rose-400/30';
      default:
        return 'bg-slate-500/20 text-slate-200 ring-slate-300/30';
    }
  });
}
