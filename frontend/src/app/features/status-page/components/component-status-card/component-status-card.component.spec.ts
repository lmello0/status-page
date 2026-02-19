import { TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import {
  ComponentViewModel,
  HealthcheckDayLogViewModel,
} from '../../../../core/models/status.models';
import { ComponentStatusCardComponent } from './component-status-card.component';

function buildDayLog(overrides: Partial<HealthcheckDayLogViewModel> = {}): HealthcheckDayLogViewModel {
  return {
    date: '2026-02-18T00:00:00Z',
    status: 'OPERATIONAL',
    uptime: 100,
    avgResponseTimeMs: 220,
    maxResponseTimeMs: 480,
    totalChecks: 40,
    successfulChecks: 40,
    ...overrides,
  };
}

function buildComponent(overrides: Partial<ComponentViewModel> = {}): ComponentViewModel {
  return {
    id: 101,
    productId: 1,
    name: 'Checkout API',
    type: 'BACKEND',
    monitoringConfig: {
      healthUrl: 'https://example.com/health',
      checkIntervalSeconds: 60,
      timeoutSeconds: 30,
      expectedStatusCode: 200,
      maxResponseTimeMs: 5000,
      failuresBeforeOutage: 3,
    },
    status: 'OPERATIONAL',
    latestLogDate: '2026-02-18T00:00:00Z',
    latestUptime: 100,
    latestAvgResponseTimeMs: 220,
    healthcheckDayLogs: [buildDayLog()],
    ...overrides,
  };
}

function createComponentFixture(component: ComponentViewModel) {
  const fixture = TestBed.createComponent(ComponentStatusCardComponent);
  fixture.componentRef.setInput('component', component);
  fixture.detectChanges();
  return fixture;
}

describe('ComponentStatusCardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ComponentStatusCardComponent],
    }).compileComponents();
  });

  it('renders health url as plain text in the card', () => {
    const baseComponent = buildComponent();
    const healthUrl = 'https://example.com/health/checks/status?region=us-east-1';
    const fixture = createComponentFixture(
      buildComponent({
        monitoringConfig: {
          ...baseComponent.monitoringConfig,
          healthUrl,
        },
      }),
    );

    const healthUrlValue: HTMLElement | null = fixture.nativeElement.querySelector('[data-health-url]');

    expect(fixture.nativeElement.textContent).toContain('Health URL');
    expect(healthUrlValue?.textContent).toContain(healthUrl);
    expect(fixture.nativeElement.querySelector(`a[href="${healthUrl}"]`)).toBeNull();
  });

  it('shows empty logs fallback when no day logs are available', () => {
    const fixture = createComponentFixture(
      buildComponent({
        latestLogDate: null,
        latestUptime: null,
        latestAvgResponseTimeMs: null,
        healthcheckDayLogs: [],
      }),
    );

    const dayBars = fixture.debugElement.queryAll(By.css('button[aria-label]'));

    expect(dayBars).toHaveLength(0);
    expect(fixture.nativeElement.textContent).toContain('No daily health logs yet.');
  });

  it('renders at most 100 day bars', () => {
    const dayLogs = Array.from({ length: 120 }, (_, index) =>
      buildDayLog({
        date: new Date(Date.UTC(2026, 1, 18 - index)).toISOString(),
      }),
    );

    const fixture = createComponentFixture(
      buildComponent({
        healthcheckDayLogs: dayLogs,
      }),
    );

    const dayBars = fixture.debugElement.queryAll(By.css('button[aria-label]'));
    expect(dayBars).toHaveLength(100);
  });

  it('applies status color classes to daily bars', () => {
    const fixture = createComponentFixture(
      buildComponent({
        healthcheckDayLogs: [
          buildDayLog({ status: 'OPERATIONAL' }),
          buildDayLog({ date: '2026-02-17T00:00:00Z', status: 'DEGRADED' }),
          buildDayLog({ date: '2026-02-16T00:00:00Z', status: 'PARTIAL_OUTAGE' }),
          buildDayLog({ date: '2026-02-15T00:00:00Z', status: 'MAJOR_OUTAGE' }),
          buildDayLog({ date: '2026-02-14T00:00:00Z', status: 'UNKNOWN' }),
        ],
      }),
    );

    const dayBars = fixture.debugElement
      .queryAll(By.css('button[aria-label]'))
      .map((item) => item.nativeElement as HTMLButtonElement);

    expect(dayBars[0].classList.contains('bg-slate-400/70')).toBe(true);
    expect(dayBars[1].classList.contains('bg-rose-400/80')).toBe(true);
    expect(dayBars[2].classList.contains('bg-orange-400/80')).toBe(true);
    expect(dayBars[3].classList.contains('bg-amber-400/80')).toBe(true);
    expect(dayBars[4].classList.contains('bg-emerald-400/80')).toBe(true);
  });

  it('emits edit event with component id', () => {
    const fixture = createComponentFixture(buildComponent({ id: 404 }));
    const emitSpy = vi.spyOn(fixture.componentInstance.editComponent, 'emit');

    const editButton = fixture.nativeElement.querySelector(
      'button[data-action="edit-component"]',
    ) as HTMLButtonElement | null;
    editButton?.click();

    expect(emitSpy).toHaveBeenCalledWith(404);
  });

  it('emits remove event with component id', () => {
    const fixture = createComponentFixture(buildComponent({ id: 505 }));
    const emitSpy = vi.spyOn(fixture.componentInstance.removeComponent, 'emit');

    const removeButton = fixture.nativeElement.querySelector(
      'button[data-action="remove-component"]',
    ) as HTMLButtonElement | null;
    removeButton?.click();

    expect(emitSpy).toHaveBeenCalledWith(505);
  });

  it('opens popup only after hover delay', () => {
    vi.useFakeTimers();

    try {
      const fixture = createComponentFixture(
        buildComponent({
          healthcheckDayLogs: [
            buildDayLog({
              date: '2026-02-18T00:00:00Z',
            }),
            buildDayLog({
              date: '2026-02-17T00:00:00Z',
            }),
          ],
        }),
      );

      const dayBars = fixture.debugElement
        .queryAll(By.css('button[aria-label]'))
        .map((item) => item.nativeElement as HTMLButtonElement);

      dayBars[0].dispatchEvent(new Event('mouseenter'));
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-day-popup]')).toBeNull();

      vi.advanceTimersByTime(200);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-day-popup]')).not.toBeNull();
      expect(fixture.nativeElement.textContent).toContain('Feb 17, 2026');
    } finally {
      vi.useRealTimers();
    }
  });

  it('keeps popup visible while pointer is on popup and hides after popup mouse leave', () => {
    vi.useFakeTimers();

    try {
      const fixture = createComponentFixture(
        buildComponent({
          healthcheckDayLogs: [
            buildDayLog({
              date: '2026-02-18T00:00:00Z',
            }),
            buildDayLog({
              date: '2026-02-17T00:00:00Z',
            }),
          ],
        }),
      );

      const dayBars = fixture.debugElement
        .queryAll(By.css('button[aria-label]'))
        .map((item) => item.nativeElement as HTMLButtonElement);

      dayBars[1].dispatchEvent(new Event('mouseenter'));
      vi.advanceTimersByTime(200);
      fixture.detectChanges();

      const barsContainer: HTMLElement | null = fixture.nativeElement.querySelector('[data-day-bars]');
      expect(barsContainer).not.toBeNull();

      barsContainer?.dispatchEvent(new Event('mouseleave'));
      const popupAfterShow: HTMLElement | null = fixture.nativeElement.querySelector('[data-day-popup]');
      popupAfterShow?.dispatchEvent(new Event('mouseenter'));
      vi.advanceTimersByTime(200);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-day-popup]')).not.toBeNull();

      popupAfterShow?.dispatchEvent(new Event('mouseleave'));
      vi.advanceTimersByTime(200);
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('[data-day-popup]')).toBeNull();
    } finally {
      vi.useRealTimers();
    }
  });

  it('pins popup on click and closes only on outside click', () => {
    const fixture = createComponentFixture(
      buildComponent({
        healthcheckDayLogs: [
          buildDayLog({
            date: '2026-02-18T00:00:00Z',
          }),
          buildDayLog({
            date: '2026-02-17T00:00:00Z',
          }),
        ],
      }),
    );

    const dayBars = fixture.debugElement
      .queryAll(By.css('button[aria-label]'))
      .map((item) => item.nativeElement as HTMLButtonElement);

    dayBars[0].dispatchEvent(new Event('focus'));
    fixture.detectChanges();

    const popup: HTMLElement | null = fixture.nativeElement.querySelector('[data-day-popup]');
    expect(popup).not.toBeNull();

    popup?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    popup?.dispatchEvent(new Event('mouseleave'));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-day-popup]')).not.toBeNull();

    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('[data-day-popup]')).toBeNull();
  });

  it('shows full day metrics for hovered or focused bars', () => {
    const fixture = createComponentFixture(
      buildComponent({
        healthcheckDayLogs: [
          buildDayLog({
            date: '2026-02-18T00:00:00Z',
            status: 'OPERATIONAL',
            uptime: 100,
            avgResponseTimeMs: 150,
            maxResponseTimeMs: 280,
            totalChecks: 48,
            successfulChecks: 48,
          }),
          buildDayLog({
            date: '2026-02-17T00:00:00Z',
            status: 'MAJOR_OUTAGE',
            uptime: 81.2,
            avgResponseTimeMs: 640,
            maxResponseTimeMs: 1820,
            totalChecks: 48,
            successfulChecks: 39,
          }),
        ],
      }),
    );

    const dayBars = fixture.debugElement
      .queryAll(By.css('button[aria-label]'))
      .map((item) => item.nativeElement as HTMLButtonElement);

    dayBars[0].dispatchEvent(new Event('focus'));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Feb 17, 2026');
    expect(fixture.nativeElement.textContent).toContain('Major outage');
    expect(fixture.nativeElement.textContent).toContain('81.2%');
    expect(fixture.nativeElement.textContent).toContain('640 ms');
    expect(fixture.nativeElement.textContent).toContain('1820 ms');
    expect(fixture.nativeElement.textContent).toContain('39/48');

    const popupBeforeBlur: HTMLElement | null = fixture.nativeElement.querySelector('[data-day-popup]');
    expect(popupBeforeBlur).not.toBeNull();
    popupBeforeBlur?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    fixture.detectChanges();

    dayBars[0].dispatchEvent(new Event('blur'));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Feb 17, 2026');

    fixture.componentInstance.clearActiveDay();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Hover or focus a day bar to inspect metrics.');
    expect(fixture.nativeElement.textContent).not.toContain('Feb 17, 2026');
  });
});
