export interface PagedResponse<T> {
  pageSize: number;
  pageCount: number;
  totalElements: number;
  totalPages: number;
  content: T[];
}

export type ComponentType = 'BACKEND' | 'FRONTEND';
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
  type: ComponentType;
  monitoringConfig: MonitoringConfigApi;
  currentStatus: string | null;
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

export interface HealthcheckDayLogViewModel {
  date: string;
  status: StatusLevel;
  uptime: number;
  avgResponseTimeMs: number;
  maxResponseTimeMs: number;
  totalChecks: number;
  successfulChecks: number;
}

export interface ComponentViewModel {
  id: number;
  productId: number;
  name: string;
  type: ComponentType;
  monitoringConfig: MonitoringConfigApi;
  status: StatusLevel;
  latestLogDate: string | null;
  latestUptime: number | null;
  latestAvgResponseTimeMs: number | null;
  healthcheckDayLogs: HealthcheckDayLogViewModel[];
}

export interface ProductViewModel {
  id: number;
  name: string;
  description: string;
  status: StatusLevel;
  components: ComponentViewModel[];
}

export interface ProductCreateDto {
  name: string;
  description?: string | null;
}

export interface ProductUpdateDto {
  name?: string | null;
  description?: string | null;
}

export interface MonitoringConfigCreateDto {
  healthUrl: string;
  checkIntervalSeconds: number;
  timeoutSeconds: number;
  expectedStatusCode: number;
  maxResponseTimeMs: number;
  failuresBeforeOutage: number;
}

export interface MonitoringConfigUpdateDto {
  healthUrl?: string | null;
  checkIntervalSeconds?: number | null;
  timeoutSeconds?: number | null;
  expectedStatusCode?: number | null;
  maxResponseTimeMs?: number | null;
  failuresBeforeOutage?: number | null;
}

export interface ComponentCreateDto {
  productId: number;
  name: string;
  type: ComponentType;
  monitoringConfig: MonitoringConfigCreateDto;
}

export interface ComponentUpdateDto {
  name?: string | null;
  type?: ComponentType | null;
  monitoringConfig?: MonitoringConfigUpdateDto | null;
}
