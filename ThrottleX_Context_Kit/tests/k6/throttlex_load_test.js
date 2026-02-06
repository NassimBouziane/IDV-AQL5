import http from 'k6/http';
import { sleep, check } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Configure via env vars:
// BASE_URL - ThrottleX base URL (default: http://localhost:8000)
// TENANTS - comma-separated tenant IDs
// ROUTE - API route to test
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const TENANTS = (__ENV.TENANTS || 't-free-01,t-pro-01,t-ent-01').split(',');
const ROUTE = __ENV.ROUTE || '/api/v1';

// Custom metrics
const allowedRate = new Rate('allowed_requests');
const blockedRate = new Rate('blocked_requests');
const validResponses = new Rate('valid_responses');  // 200 or 429 are both valid
const evaluateLatency = new Trend('evaluate_latency');

export const options = {
  stages: [
    { duration: '10s', target: 20 },   // Warmup
    { duration: '30s', target: 50 },   // Ramp up
    { duration: '30s', target: 100 },  // Peak load
    { duration: '10s', target: 0 },    // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<150', 'p(99)<300'],  // SLO: p95 < 150ms, p99 < 300ms
    'http_req_duration{status:200}': ['p(95)<100'], // Allowed requests faster
    valid_responses: ['rate>0.99'],                  // >99% valid (200 or 429)
  },
};

export default function () {
  const tenant = TENANTS[Math.floor(Math.random() * TENANTS.length)];
  
  const start = Date.now();
  const res = http.post(
    `${BASE_URL}/evaluate`,
    JSON.stringify({ tenantId: tenant, route: ROUTE }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  evaluateLatency.add(Date.now() - start);

  // 200 = allowed, 429 = rate limited (both are valid responses)
  const isValidResponse = res.status === 200 || res.status === 429;
  validResponses.add(isValidResponse);

  const success = check(res, { 
    'valid response (200 or 429)': r => r.status === 200 || r.status === 429,
    'has allow field': r => r.status === 200 ? r.json('allow') !== undefined : true,
  });

  if (res.status === 200 && res.json()) {
    const data = res.json();
    allowedRate.add(data.allow === true);
    blockedRate.add(data.allow === false);
  } else if (res.status === 429) {
    // 429 means rate limited - this is expected behavior
    blockedRate.add(1);
    allowedRate.add(0);
  }

  sleep(0.05); // 50ms between requests
}

// Setup: Create test policies
export function setup() {
  console.log(`Testing against ${BASE_URL}`);
  console.log(`Tenants: ${TENANTS.join(', ')}`);
  
  // Create policies for each tenant
  TENANTS.forEach(tenant => {
    const policy = {
      tenantId: tenant,
      scope: 'TENANT',
      algorithm: 'SLIDING_WINDOW',
      limit: 100,
      windowSeconds: 60,
    };
    
    http.post(`${BASE_URL}/policies`, JSON.stringify(policy), {
      headers: { 'Content-Type': 'application/json' }
    });
  });
  
  return { tenants: TENANTS };
}
