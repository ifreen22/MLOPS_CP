import { test, expect } from '@playwright/test';

test.describe('AIOps Sentinel Production UI Test Suite', () => {
  test.beforeEach(async ({ page }) => {
    // Use the same storage key as the production auth client and make each UI
    // test independent from a running backend or a real user session.
    await page.addInitScript(() => {
      sessionStorage.setItem('aiops-access-token', 'playwright-test-token');
    });

    await page.route('**/api/v1/**', async (route) => {
      const { pathname } = new URL(route.request().url());
      const method = route.request().method();
      const json = pathname.endsWith('/system/settings')
        ? { isMonitoring: true, autoRecovery: false, pollingInterval: 2 }
        : pathname.endsWith('/system/live')
          ? {
              is_docker: false,
              data: {
                timestamp: '2026-10-22T00:00:00+00:00',
                cpu: { usage_percent: 42.5, logical_cores: 8, physical_cores: 4, current_freq: 3200, max_freq: 4500, load_avg: [0, 0, 0] },
                ram: { total: 16000000000, available: 8000000000, used: 8000000000, percent: 50 },
                disk: { drives: [], total: 500000000000, used: 250000000000, percent: 50 },
                network: { upload_speed: 1048576, download_speed: 2097152, bytes_sent: 1, bytes_recv: 1 },
                battery_percent: null,
                temperature: null,
                processes: [],
                system: { hostname: 'playwright-host', os: 'Windows', version: 'test', architecture: 'x64', uptime: 1 },
              },
            }
          : pathname.endsWith('/ml/health')
            ? { status: 'healthy', services: { root_cause_analysis: true, risk_prediction: true, alert_clustering: true } }
            : pathname.endsWith('/ml/cluster/health')
              ? { status: 'healthy' }
              : pathname.endsWith('/notifications/settings')
                ? { webhookUrl: '', slackChannel: '', pagerDutyRoutingKey: '', minSeverity: 'CRITICAL', enabledEvents: [] }
                : pathname.endsWith('/auth/me')
                  ? {
                      id: 'admin-1',
                      organizationId: 'org-1',
                      email: 'admin@example.test',
                      firstName: 'Test',
                      lastName: 'Admin',
                      role: 'ADMIN',
                      isActive: true,
                      createdAt: '2026-01-01T00:00:00Z',
                      updatedAt: '2026-01-01T00:00:00Z',
                    }
                  : method === 'GET'
                  ? []
                  : {};

      await route.fulfill({ contentType: 'application/json', body: JSON.stringify(json) });
    });
  });

  test('Page 1: Mission Control loads hardware KPIs and controls', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('main').getByRole('heading', { name: 'Mission Control' })).toBeVisible();
    await expect(page.locator('text=Status:')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Compute' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Network' })).toBeVisible();
    await page.getByRole('button', { name: 'Network' }).click();
    await expect(page.getByRole('button', { name: 'Network' })).toHaveClass(/bg-background/);
  });

  test('Page 2: Situation Room renders incidents and actions', async ({ page }) => {
    await page.goto('/situations');
    await expect(page.locator('main').getByRole('heading', { name: 'Situation Room' })).toBeVisible();
    await expect(page.locator('button:has-text("Refresh")')).toBeVisible();
    await expect(page.locator('button:has-text("Export Report")')).toBeVisible();
  });

  test('Page 3: Alert Clustering supports filters and mode toggles', async ({ page }) => {
    await page.goto('/alert-clustering');
    await expect(page.locator('text=Alert Intelligence & Clustering')).toBeVisible();
    await expect(page.locator('button:has-text("Split Mode")')).toBeVisible();
    await expect(page.locator('button:has-text("Alerts Only")')).toBeVisible();
    await expect(page.locator('button:has-text("Situations Only")')).toBeVisible();
    await page.getByRole('button', { name: 'Alerts Only' }).click();
    await expect(page.getByRole('button', { name: 'Alerts Only' })).toHaveAttribute('aria-pressed', 'true');
  });

  test('Page 4: Root Cause Graph renders topology canvas', async ({ page }) => {
    await page.goto('/root-cause-graph');
    await expect(page.locator('text=Root Cause Topology')).toBeVisible();
    await expect(page.locator('button[aria-label="Refresh topology"]')).toBeVisible();
    await page.getByRole('button', { name: 'Refresh topology' }).click();
  });

  test('Page 5: Remediation Playbooks table and search', async ({ page }) => {
    await page.goto('/remediation-playbooks');
    await expect(page.locator('text=Remediation Playbooks')).toBeVisible();
    await expect(page.locator('input[placeholder="Filter playbooks..."]')).toBeVisible();
    await page.getByPlaceholder('Filter playbooks...').fill('restart');
  });

  test('Page 6: SLO Dashboard allows defining host resource objectives', async ({ page }) => {
    await page.goto('/slo-dashboard');
    await expect(page.locator('text=Service Level Objectives (SLOs)')).toBeVisible();
    await expect(page.locator('button:has-text("Create SLO")')).toBeVisible();
  });

  test('Page 7: Audit Logs renders organization audit history', async ({ page }) => {
    await page.goto('/audit-logs');
    await expect(page.locator('main').getByRole('heading', { name: 'Audit Logs' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Refresh' })).toBeEnabled({ timeout: 10000 });
    await page.getByRole('button', { name: 'Refresh' }).click();
  });

  test('Page 8: Settings renders OPA policy editor, service tiers, and routing', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.locator('text=Settings & Policies')).toBeVisible();
    await expect(page.locator('text=Policy Editor (Rego)')).toBeVisible();
    await expect(page.locator('text=Service Tiers')).toBeVisible();
    await expect(page.locator('text=Notification Routing')).toBeVisible();

    // Switch to Service Tiers tab
    await page.click('button:has-text("Service Tiers")');
    await expect(page.locator('text=Service Criticality & SLA Tiers')).toBeVisible();

    // Switch to Notification Routing tab
    await page.click('button:has-text("Notification Routing")');
    await expect(page.getByRole('heading', { name: 'Alert Routing Webhooks' })).toBeVisible();
    await expect(page.locator('button:has-text("Send Test Alert")')).toBeVisible();
  });
});
