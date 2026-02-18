import {
  ComponentViewModel,
  HealthcheckDayLogApi,
  ProductApi,
  ProductComponentApi,
  ProductViewModel,
} from '../models/status.models';
import { aggregateProductStatus, normalizeStatus } from '../utils/status-severity';

function getLatestLog(logs: HealthcheckDayLogApi[]): HealthcheckDayLogApi | null {
  if (!logs.length) {
    return null;
  }

  return logs.reduce((latest, current) =>
    Date.parse(current.date) > Date.parse(latest.date) ? current : latest,
  );
}

function mapComponent(component: ProductComponentApi): ComponentViewModel | null {
  if (!component.isActive) {
    return null;
  }

  const latestLog = getLatestLog(component.healthcheckDayLogs ?? []);

  return {
    id: component.id,
    productId: component.productId,
    name: component.name,
    type: component.type,
    status: normalizeStatus(component.currentStatus),
    latestLogDate: latestLog?.date ?? null,
    latestUptime: latestLog?.uptime ?? null,
    latestAvgResponseTimeMs: latestLog?.avgResponseTime ?? null,
  };
}

export function mapProduct(product: ProductApi): ProductViewModel | null {
  if (!product.isVisible) {
    return null;
  }

  const components = (product.components ?? [])
    .map((component) => mapComponent(component))
    .filter((component): component is ComponentViewModel => component !== null);

  if (!components.length) {
    return null;
  }

  const description = typeof product.description === 'string' ? product.description.trim() : '';

  return {
    id: product.id,
    name: product.name,
    description: description || 'No description provided',
    status: aggregateProductStatus(components),
    components,
  };
}

export function mapProducts(products: ProductApi[]): ProductViewModel[] {
  return products
    .map((product) => mapProduct(product))
    .filter((product): product is ProductViewModel => product !== null);
}

export function normalizeText(text: string): string {
  return text
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

export function filterProductsByQuery(products: ProductViewModel[], query: string): ProductViewModel[] {
  const normalizedQuery = normalizeText(query);

  if (!normalizedQuery) {
    return products;
  }

  return products.reduce<ProductViewModel[]>((result, product) => {
    const productMatches = normalizeText(product.name).includes(normalizedQuery);

    if (productMatches) {
      result.push(product);
      return result;
    }

    const matchingComponents = product.components.filter((component) =>
      normalizeText(component.name).includes(normalizedQuery),
    );

    if (matchingComponents.length) {
      result.push({
        ...product,
        components: matchingComponents,
      });
    }

    return result;
  }, []);
}
