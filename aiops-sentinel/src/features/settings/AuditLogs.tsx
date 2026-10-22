import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { fetchAuditLogs, getCurrentUser } from '../../services/api';

function auditLogsErrorMessage(error: unknown): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : 'An unknown error occurred.';
  }

  const status = error.response?.status;
  const body: unknown = error.response?.data;
  const detail =
    body && typeof body === 'object' && 'detail' in body
      ? body.detail
      : undefined;
  const responseBody =
    typeof detail === 'string'
      ? detail
      : body
        ? JSON.stringify(body)
        : error.message;

  return status
    ? `HTTP ${status}: ${responseBody}`
    : `Network error: ${responseBody}`;
}

export function AuditLogs() {
  const currentUserQuery = useQuery({
    queryKey: ['currentUser'],
    queryFn: getCurrentUser,
    retry: false,
    staleTime: 30_000,
  });
  const {
    data = [],
    error,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['auditLogs'],
    queryFn: async () => {
      try {
        return await fetchAuditLogs(200);
      } catch (requestError: unknown) {
        if (axios.isAxiosError(requestError)) {
          console.error('Audit logs request failed', {
            status: requestError.response?.status ?? null,
            responseBody: requestError.response?.data ?? null,
          });
        } else {
          console.error('Audit logs request failed', requestError);
        }
        throw requestError;
      }
    },
    enabled: currentUserQuery.data?.role === 'ADMIN',
    refetchInterval: 15000,
  });
  const currentUserError = currentUserQuery.isError
    ? auditLogsErrorMessage(currentUserQuery.error)
    : null;
  const isAdministrator = currentUserQuery.data?.role === 'ADMIN';

  return (
    <div className="flex min-h-full w-full flex-col gap-space-md bg-surface-container-lowest p-space-lg text-on-surface">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-headline-md font-semibold">Audit Logs</h1>
          <p className="mt-1 text-sm text-on-surface-variant">
            Organization-scoped authentication, user-management, and playbook events.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={!isAdministrator || isFetching}
          className="rounded border border-outline-variant px-3 py-2 text-sm disabled:opacity-50"
        >
          {isFetching ? 'Refreshing…' : 'Refresh'}
        </button>
      </header>

      {currentUserQuery.isLoading && (
        <p role="status" className="text-sm text-on-surface-variant">Checking administrator access…</p>
      )}
      {currentUserError && (
        <p role="alert" className="text-sm text-destructive">
          Could not verify account access: {currentUserError}
        </p>
      )}
      {!currentUserQuery.isLoading && !currentUserError && !isAdministrator && (
        <p role="alert" className="text-sm text-destructive">
          Administrator access is required. Your current role is {currentUserQuery.data?.role ?? 'unknown'}.
        </p>
      )}
      {isAdministrator && isLoading && (
        <p role="status" className="text-sm text-on-surface-variant">Loading audit events…</p>
      )}
      {isAdministrator && isError && (
        <p role="alert" className="text-sm text-destructive">
          Could not load audit logs: {auditLogsErrorMessage(error)}
        </p>
      )}
      {isAdministrator && !isLoading && !isError && data.length === 0 && (
        <p className="rounded border border-outline-variant bg-surface-container-low p-5 text-sm text-on-surface-variant">
          No audit events have been recorded.
        </p>
      )}
      {isAdministrator && data.length > 0 && (
        <div className="overflow-x-auto rounded border border-outline-variant bg-surface-container-low">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-outline-variant text-on-surface-variant">
                <th className="whitespace-nowrap px-3 py-2">Time</th>
                <th className="px-3 py-2">User</th>
                <th className="px-3 py-2">Action</th>
                <th className="px-3 py-2">Resource</th>
                <th className="px-3 py-2">Details</th>
              </tr>
            </thead>
            <tbody>
              {data.map((entry) => (
                <tr key={entry.id} className="border-b border-outline-variant/60 align-top">
                  <td className="whitespace-nowrap px-3 py-2">{new Date(entry.createdAt).toLocaleString()}</td>
                  <td className="px-3 py-2">{entry.userEmail || entry.userId}</td>
                  <td className="px-3 py-2 font-medium">{entry.action}</td>
                  <td className="px-3 py-2">{entry.resource}{entry.resourceId ? ` · ${entry.resourceId}` : ''}</td>
                  <td className="max-w-lg break-words px-3 py-2 text-on-surface-variant">{entry.details || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
