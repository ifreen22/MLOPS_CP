import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, expect, test, vi } from 'vitest';
import LoginPage from './LoginPage';
import { getAuthStatus, login } from '../../services/api';

const navigate = vi.fn();

vi.mock('../../services/api', () => ({
  getAuthStatus: vi.fn(),
  login: vi.fn(),
}));

vi.mock('react-router-dom', async (importOriginal) => ({
  ...(await importOriginal<typeof import('react-router-dom')>()),
  useNavigate: () => navigate,
}));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(getAuthStatus).mockResolvedValue({ configured: true });
  vi.mocked(login).mockResolvedValue({
    access_token: 'test-token',
    token_type: 'bearer',
    expires_in: 900,
    user: {
      id: 'admin-1',
      organizationId: 'org-1',
      email: 'admin@example.test',
      firstName: 'Test',
      lastName: 'Admin',
      role: 'ADMIN',
      isActive: true,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    },
  });
});

test('submits configured administrator credentials and redirects after sign-in', async () => {
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );

  const submit = await screen.findByRole('button', { name: 'Sign in' });
  await user.type(screen.getByLabelText('Email'), 'admin@example.test');
  await user.type(screen.getByLabelText('Password'), 'correct-horse-battery-staple');
  await user.click(submit);

  await waitFor(() => {
    expect(login).toHaveBeenCalledWith('admin@example.test', 'correct-horse-battery-staple');
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });
});
