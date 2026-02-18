import { ComponentViewModel, StatusLevel } from '../models/status.models';

const STATUS_ALIAS: Record<string, StatusLevel> = {
  OPERATIONAL: 'OPERATIONAL',
  DEGRADED: 'DEGRADED',
  DEGRADED_PERFORMANCE: 'DEGRADED',
  PARTIAL_OUTAGE: 'PARTIAL_OUTAGE',
  MAJOR_OUTAGE: 'MAJOR_OUTAGE',
  OUTAGE: 'MAJOR_OUTAGE',
};

export const STATUS_SEVERITY: Record<StatusLevel, number> = {
  OPERATIONAL: 0,
  DEGRADED: 1,
  PARTIAL_OUTAGE: 2,
  MAJOR_OUTAGE: 3,
  UNKNOWN: -1,
};

export function normalizeStatus(status: string | null | undefined): StatusLevel {
  if (!status) {
    return 'UNKNOWN';
  }

  return STATUS_ALIAS[status.trim().toUpperCase()] ?? 'UNKNOWN';
}

export function compareStatusSeverity(left: StatusLevel, right: StatusLevel): number {
  return STATUS_SEVERITY[left] - STATUS_SEVERITY[right];
}

export function getMostSevereStatus(statuses: StatusLevel[]): StatusLevel {
  if (statuses.length === 0) {
    return 'UNKNOWN';
  }

  return statuses.reduce((worst, current) =>
    compareStatusSeverity(current, worst) > 0 ? current : worst,
  );
}

export function aggregateProductStatus(components: ComponentViewModel[]): StatusLevel {
  return getMostSevereStatus(components.map((component) => component.status));
}

export function statusToLabel(status: StatusLevel): string {
  switch (status) {
    case 'OPERATIONAL':
      return 'Operational';
    case 'DEGRADED':
      return 'Degraded';
    case 'PARTIAL_OUTAGE':
      return 'Partial outage';
    case 'MAJOR_OUTAGE':
      return 'Major outage';
    default:
      return 'Unknown';
  }
}
