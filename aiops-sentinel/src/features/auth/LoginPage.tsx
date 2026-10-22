import { useState, type FormEvent } from 'react';
import axios from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { getAuthStatus, login } from '../../services/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const statusQuery = useQuery({
    queryKey: ['authStatus'],
    queryFn: getAuthStatus,
    retry: false,
  });
  const loginMutation = useMutation({
    mutationFn: () => login(email, password),
    onSuccess: () => {
      queryClient.clear();
      navigate('/', { replace: true });
    },
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    loginMutation.mutate();
  };
  const loginError = axios.isAxiosError<{ detail?: string }>(loginMutation.error)
    ? loginMutation.error.response?.data?.detail
    : undefined;

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <section className="w-full max-w-md rounded-xl border border-border bg-card p-8 shadow-xl">
        <h1 className="text-2xl font-bold">Sign in to AIOps Sentinel</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Use the local administrator or an account created by an administrator.
        </p>

        {statusQuery.isLoading && <p className="mt-5 text-sm text-muted-foreground">Checking account setup…</p>}
        {statusQuery.isError && (
          <p role="alert" className="mt-5 text-sm text-destructive">
            Could not check the authentication service. Verify the backend is running and try again.
          </p>
        )}
        {statusQuery.data && !statusQuery.data.configured && (
          <p role="alert" className="mt-5 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
            No local account exists. Set <code>ADMIN_EMAIL</code> and <code>ADMIN_PASSWORD</code> in the project
            environment file, then restart the backend to create the initial administrator.
          </p>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4">
          <label className="block text-sm">
            Email
            <input
              autoComplete="username"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>
          <label className="block text-sm">
            Password
            <input
              autoComplete="current-password"
              type="password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2"
            />
          </label>
          {loginMutation.isError && (
            <p role="alert" className="text-sm text-destructive">
              {loginError || 'Sign-in failed. Check your credentials and retry.'}
            </p>
          )}
          <button
            type="submit"
            disabled={loginMutation.isPending || statusQuery.data?.configured !== true}
            className="w-full rounded-md bg-primary px-4 py-2 font-semibold text-primary-foreground disabled:opacity-50"
          >
            {loginMutation.isPending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  );
}
