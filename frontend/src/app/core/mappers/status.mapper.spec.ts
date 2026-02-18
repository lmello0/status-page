import { filterProductsByQuery, mapProducts } from './status.mapper';
import { ProductApi } from '../models/status.models';

function buildProduct(overrides: Partial<ProductApi> = {}): ProductApi {
  return {
    id: 1,
    name: 'Payments',
    description: 'Payment platform',
    isVisible: true,
    createdAt: '2026-02-14T19:42:23.142764',
    updatedAt: '2026-02-15T16:34:24.001255',
    components: [
      {
        id: 10,
        productId: 1,
        name: 'Checkout API',
        type: 'BACKEND',
        monitoringConfig: {
          healthUrl: 'https://example.com/health',
          checkIntervalSeconds: 60,
          timeoutSeconds: 30,
          expectedStatusCode: 200,
          maxResponseTimeMs: 3000,
          failuresBeforeOutage: 3,
        },
        currentStatus: 'OPERATIONAL',
        isActive: true,
        healthcheckDayLogs: [
          {
            date: '2026-02-18T00:00:00Z',
            totalChecks: 50,
            successfulChecks: 50,
            uptime: 100,
            avgResponseTime: 120,
            maxResponseTime: 300,
            overallStatus: 'OPERATIONAL',
          },
        ],
      },
      {
        id: 11,
        productId: 1,
        name: 'Legacy Worker',
        type: 'BACKEND',
        monitoringConfig: {
          healthUrl: 'https://example.com/worker',
          checkIntervalSeconds: 60,
          timeoutSeconds: 30,
          expectedStatusCode: 200,
          maxResponseTimeMs: 3000,
          failuresBeforeOutage: 3,
        },
        currentStatus: 'MAJOR_OUTAGE',
        isActive: false,
        healthcheckDayLogs: [],
      },
    ],
    ...overrides,
  };
}

describe('status.mapper', () => {
  it('filters out hidden products and inactive components', () => {
    const visibleProduct = buildProduct();
    const hiddenProduct = buildProduct({
      id: 2,
      name: 'Internal Tooling',
      isVisible: false,
    });

    const result = mapProducts([visibleProduct, hiddenProduct]);

    expect(result).toHaveLength(1);
    expect(result[0].id).toBe(1);
    expect(result[0].components).toHaveLength(1);
    expect(result[0].components[0].name).toBe('Checkout API');
  });

  it('aggregates product status from the most severe active component', () => {
    const product = buildProduct({
      components: [
        {
          ...buildProduct().components[0],
          id: 20,
          name: 'API Gateway',
          currentStatus: 'DEGRADED',
          isActive: true,
        },
        {
          ...buildProduct().components[0],
          id: 21,
          name: 'Core Processor',
          currentStatus: 'MAJOR_OUTAGE',
          isActive: true,
        },
      ],
    });

    const [mapped] = mapProducts([product]);

    expect(mapped.status).toBe('MAJOR_OUTAGE');
  });

  it('maps components with empty logs using null metric fallbacks', () => {
    const product = buildProduct({
      components: [
        {
          ...buildProduct().components[0],
          id: 30,
          name: 'Queue Processor',
          healthcheckDayLogs: [],
        },
      ],
    });

    const [mapped] = mapProducts([product]);

    expect(mapped.components[0].latestLogDate).toBeNull();
    expect(mapped.components[0].latestUptime).toBeNull();
    expect(mapped.components[0].latestAvgResponseTimeMs).toBeNull();
    expect(mapped.components[0].healthcheckDayLogs).toEqual([]);
  });

  it('maps day logs sorted by newest date and normalizes daily statuses', () => {
    const product = buildProduct({
      components: [
        {
          ...buildProduct().components[0],
          healthcheckDayLogs: [
            {
              date: '2026-02-17T00:00:00Z',
              totalChecks: 60,
              successfulChecks: 58,
              uptime: 96.7,
              avgResponseTime: 210,
              maxResponseTime: 640,
              overallStatus: 'DEGRADED_PERFORMANCE',
            },
            {
              date: '2026-02-18T00:00:00Z',
              totalChecks: 60,
              successfulChecks: 50,
              uptime: 83.3,
              avgResponseTime: 540,
              maxResponseTime: 1150,
              overallStatus: 'OUTAGE',
            },
            {
              date: '2026-02-16T00:00:00Z',
              totalChecks: 60,
              successfulChecks: 60,
              uptime: 100,
              avgResponseTime: 140,
              maxResponseTime: 320,
              overallStatus: 'OPERATIONAL',
            },
          ],
        },
      ],
    });

    const [mapped] = mapProducts([product]);
    const [component] = mapped.components;

    expect(component.latestLogDate).toBe('2026-02-18T00:00:00Z');
    expect(component.latestUptime).toBe(83.3);
    expect(component.latestAvgResponseTimeMs).toBe(540);
    expect(component.healthcheckDayLogs.map((log) => log.date)).toEqual([
      '2026-02-18T00:00:00Z',
      '2026-02-17T00:00:00Z',
      '2026-02-16T00:00:00Z',
    ]);
    expect(component.healthcheckDayLogs.map((log) => log.status)).toEqual([
      'MAJOR_OUTAGE',
      'DEGRADED',
      'OPERATIONAL',
    ]);
  });

  it('includes product when query matches component name', () => {
    const mappedProducts = mapProducts([buildProduct()]);

    const result = filterProductsByQuery(mappedProducts, 'checkout');

    expect(result).toHaveLength(1);
    expect(result[0].name).toBe('Payments');
    expect(result[0].components).toHaveLength(1);
    expect(result[0].components[0].name).toBe('Checkout API');
  });
});
