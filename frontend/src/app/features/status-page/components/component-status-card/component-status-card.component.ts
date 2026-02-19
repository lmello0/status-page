import { NgClass } from '@angular/common';
import {
  Component,
  computed,
  HostListener,
  input,
  OnDestroy,
  output,
  signal,
  ViewChild,
  ElementRef,
} from '@angular/core';

import {
  ComponentViewModel,
  HealthcheckDayLogViewModel,
  StatusLevel,
} from '../../../../core/models/status.models';
import { statusToLabel } from '../../../../core/utils/status-severity';
import { StatusBadgeComponent } from '../status-badge/status-badge.component';

const MAX_DAYS_DISPLAYED = 100;
const HOVER_OPEN_DELAY_MS = 160;
const HOVER_CLOSE_DELAY_MS = 140;
const DATE_FORMATTER = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: '2-digit',
  year: 'numeric',
  timeZone: 'UTC',
});

function dateToTimestamp(date: string): number {
  const timestamp = Date.parse(date);
  return Number.isNaN(timestamp) ? 0 : timestamp;
}

@Component({
  selector: 'app-component-status-card',
  standalone: true,
  imports: [NgClass, StatusBadgeComponent],
  templateUrl: './component-status-card.component.html',
})
export class ComponentStatusCardComponent implements OnDestroy {
  @ViewChild('dayPopup') private dayPopup?: ElementRef<HTMLElement>;

  readonly component = input.required<ComponentViewModel>();
  readonly editComponent = output<number>();
  readonly removeComponent = output<number>();
  readonly activeDayIndex = signal<number | null>(null);
  readonly popupPinned = signal(false);

  private hoverOpenTimeout: ReturnType<typeof setTimeout> | null = null;
  private hoverCloseTimeout: ReturnType<typeof setTimeout> | null = null;

  readonly uptimeText = computed(() => {
    const uptime = this.component().latestUptime;
    return uptime === null ? 'No uptime data yet' : `${uptime.toFixed(1)}% uptime`;
  });

  readonly avgResponseTimeText = computed(() => {
    const average = this.component().latestAvgResponseTimeMs;
    return average === null ? 'No latency data yet' : `${average.toFixed(0)} ms avg`;
  });

  readonly visibleDayLogs = computed(() =>
    [...this.component().healthcheckDayLogs]
      .sort((left, right) => dateToTimestamp(left.date) - dateToTimestamp(right.date))
      .slice(-MAX_DAYS_DISPLAYED),
  );

  readonly activeDayLog = computed(() => {
    const dayIndex = this.activeDayIndex();

    if (dayIndex === null) {
      return null;
    }

    return this.visibleDayLogs()[dayIndex] ?? null;
  });

  ngOnDestroy(): void {
    this.clearTimers();
  }

  onDayEnter(index: number): void {
    if (this.popupPinned()) {
      return;
    }

    this.clearCloseTimeout();
    this.clearOpenTimeout();
    this.hoverOpenTimeout = setTimeout(() => {
      this.activeDayIndex.set(index);
      this.hoverOpenTimeout = null;
    }, HOVER_OPEN_DELAY_MS);
  }

  onDayFocus(index: number): void {
    if (this.popupPinned()) {
      return;
    }

    this.clearTimers();
    this.activeDayIndex.set(index);
  }

  onBarsLeave(): void {
    if (this.popupPinned()) {
      return;
    }

    this.scheduleHide();
  }

  onPopupEnter(): void {
    this.clearCloseTimeout();
  }

  onPopupLeave(): void {
    if (this.popupPinned()) {
      return;
    }

    this.scheduleHide();
  }

  onPopupClick(event: MouseEvent): void {
    event.stopPropagation();
    this.clearTimers();
    this.popupPinned.set(true);
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.popupPinned()) {
      return;
    }

    const popupElement = this.dayPopup?.nativeElement;
    const target = event.target;

    if (!popupElement || !(target instanceof Node)) {
      return;
    }

    if (popupElement.contains(target)) {
      return;
    }

    this.clearActiveDay();
  }

  clearActiveDay(event?: Event): void {
    event?.stopPropagation();
    this.clearTimers();
    this.popupPinned.set(false);
    this.activeDayIndex.set(null);
  }

  statusLabel(status: StatusLevel): string {
    return statusToLabel(status);
  }

  dayBarClasses(status: StatusLevel): string {
    switch (status) {
      case 'OPERATIONAL':
        return 'bg-emerald-400/80 hover:bg-emerald-300 focus-visible:bg-emerald-300';
      case 'DEGRADED':
        return 'bg-amber-400/80 hover:bg-amber-300 focus-visible:bg-amber-300';
      case 'PARTIAL_OUTAGE':
        return 'bg-orange-400/80 hover:bg-orange-300 focus-visible:bg-orange-300';
      case 'MAJOR_OUTAGE':
        return 'bg-rose-400/80 hover:bg-rose-300 focus-visible:bg-rose-300';
      default:
        return 'bg-slate-400/70 hover:bg-slate-300 focus-visible:bg-slate-300';
    }
  }

  formatDay(date: string): string {
    const timestamp = Date.parse(date);

    if (Number.isNaN(timestamp)) {
      return date;
    }

    return DATE_FORMATTER.format(new Date(timestamp));
  }

  formatUptime(value: number): string {
    return `${value.toFixed(1)}%`;
  }

  formatLatency(valueMs: number): string {
    return `${valueMs.toFixed(0)} ms`;
  }

  dayAriaLabel(log: HealthcheckDayLogViewModel): string {
    return `${this.formatDay(log.date)} - ${this.statusLabel(log.status)}`;
  }

  onEditComponent(): void {
    this.editComponent.emit(this.component().id);
  }

  onRemoveComponent(): void {
    this.removeComponent.emit(this.component().id);
  }

  private scheduleHide(): void {
    this.clearOpenTimeout();
    this.clearCloseTimeout();
    this.hoverCloseTimeout = setTimeout(() => {
      if (!this.popupPinned()) {
        this.activeDayIndex.set(null);
      }

      this.hoverCloseTimeout = null;
    }, HOVER_CLOSE_DELAY_MS);
  }

  private clearTimers(): void {
    this.clearOpenTimeout();
    this.clearCloseTimeout();
  }

  private clearOpenTimeout(): void {
    if (this.hoverOpenTimeout !== null) {
      clearTimeout(this.hoverOpenTimeout);
      this.hoverOpenTimeout = null;
    }
  }

  private clearCloseTimeout(): void {
    if (this.hoverCloseTimeout !== null) {
      clearTimeout(this.hoverCloseTimeout);
      this.hoverCloseTimeout = null;
    }
  }
}
