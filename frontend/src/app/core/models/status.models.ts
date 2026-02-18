export interface PagedResponse<T> {
  pageSize: number;
  pageCount: number;
  totalElements: number;
  totalPages: number;
  content: T[];
}

export type StatusLevel = 'OPERATIONAL' | 'DEGRADED' | 'PARTIAL_OUTAGE' | 'MAJOR_OUTAGE' | 'UNKNOWN';

export interface MonitoringConfigApi {
  healthUrl: string;
  checkIntervalSeconds: number;
  timeoutSeconds: number;
  expectedStatusCode: number;
  maxResponseTimeMs: number;
  failuresBeforeOutage: number;
}

export interface HealthcheckDayLogApi {
  date: string;
  totalChecks: number;
  successfulChecks: number;
  uptime: number;
  avgResponseTime: number;
  maxResponseTime: number;
  overallStatus: string;
}

export interface ProductComponentApi {
  id: number;
  productId: number;
  name: string;
  type: string;
  monitoringConfig: MonitoringConfigApi;
  currentStatus: string;
  isActive: boolean;
  healthcheckDayLogs: HealthcheckDayLogApi[];
}

export interface ProductApi {
  id: number;
  name: string;
  description: string | null;
  isVisible: boolean;
  createdAt: string;
  updatedAt: string;
  components: ProductComponentApi[];
}

export interface ComponentViewModel {
  id: number;
  productId: number;
  name: string;
  type: string;
  status: StatusLevel;
  latestLogDate: string | null;
  latestUptime: number | null;
  latestAvgResponseTimeMs: number | null;
}

export interface ProductViewModel {
  id: number;
  name: string;
  description: string;
  status: StatusLevel;
  components: ComponentViewModel[];
}
