import { useState, type FormEvent } from 'react';
import axios from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createUser,
  deleteUser,
  fetchUsers,
  setUserActive,
  updateUser,
  type CreateUserRequest,
  type ManagedUser,
} from '../../services/api';

const roles: CreateUserRequest['role'][] = ['VIEWER', 'OPERATOR', 'ADMIN'];

export function UserManagement() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [role, setRole] = useState<CreateUserRequest['role']>('VIEWER');
  const [editedRoles, setEditedRoles] = useState<Record<string, ManagedUser['role']>>({});
  const queryClient = useQueryClient();
  const usersQuery = useQuery({ queryKey: ['users'], queryFn: fetchUsers });
  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: async () => {
      setEmail('');
      setPassword('');
      setFirstName('');
      setLastName('');
      setRole('VIEWER');
      await queryClient.invalidateQueries({ queryKey: ['users'] });
    },
  });
  const refreshUsers = () => queryClient.invalidateQueries({ queryKey: ['users'] });
  const updateMutation = useMutation({
    mutationFn: ({ id, newRole }: { id: string; newRole: ManagedUser['role'] }) =>
      updateUser(id, { role: newRole }),
    onSuccess: refreshUsers,
  });
  const statusMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: string; isActive: boolean }) =>
      setUserActive(id, isActive),
    onSuccess: refreshUsers,
  });
  const deleteMutation = useMutation({
    mutationFn: deleteUser,
    onSuccess: refreshUsers,
  });

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate({
      email,
      password,
      firstName: firstName || undefined,
      lastName: lastName || undefined,
      role,
    });
  };
  const errorMessage = (error: unknown) => {
    if (!axios.isAxiosError<{ detail?: string }>(error)) return 'Request failed. Please retry.';
    if (typeof error.response?.data?.detail === 'string') return error.response.data.detail;
    if (error.response?.status === 403) return 'Only an administrator can manage users.';
    return 'Request failed. Please check the backend connection and retry.';
  };

  return (
    <section className="grid gap-space-md xl:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <form onSubmit={submit} className="flex flex-col gap-3 rounded border border-outline-variant bg-surface-container-lowest p-space-md">
        <div>
          <h2 className="font-headline-sm text-on-surface font-semibold">Create an account</h2>
          <p className="mt-1 text-sm text-on-surface-variant">New users are assigned to your organization. Passwords must be at least 12 characters.</p>
        </div>
        <label className="text-sm text-on-surface">
          Email
          <input required type="email" autoComplete="off" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 w-full rounded border border-outline-variant bg-surface-container-low px-3 py-2" />
        </label>
        <label className="text-sm text-on-surface">
          Temporary password
          <input required minLength={12} maxLength={72} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded border border-outline-variant bg-surface-container-low px-3 py-2" />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-sm text-on-surface">
            First name
            <input value={firstName} onChange={(event) => setFirstName(event.target.value)} className="mt-1 w-full rounded border border-outline-variant bg-surface-container-low px-3 py-2" />
          </label>
          <label className="text-sm text-on-surface">
            Last name
            <input value={lastName} onChange={(event) => setLastName(event.target.value)} className="mt-1 w-full rounded border border-outline-variant bg-surface-container-low px-3 py-2" />
          </label>
        </div>
        <label className="text-sm text-on-surface">
          Role
          <select value={role} onChange={(event) => setRole(event.target.value as CreateUserRequest['role'])} className="mt-1 w-full rounded border border-outline-variant bg-surface-container-low px-3 py-2">
            {roles.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        {(createMutation.isError || updateMutation.isError || statusMutation.isError || deleteMutation.isError) && (
          <p role="alert" className="text-sm text-destructive">
            {errorMessage(createMutation.error || updateMutation.error || statusMutation.error || deleteMutation.error)}
          </p>
        )}
        {createMutation.isSuccess && <p role="status" className="text-sm text-success">Account created.</p>}
        <button disabled={createMutation.isPending} type="submit" className="rounded bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground disabled:opacity-50">
          {createMutation.isPending ? 'Creating…' : 'Create user'}
        </button>
      </form>

      <div className="rounded border border-outline-variant bg-surface-container-lowest p-space-md">
        <h2 className="font-headline-sm text-on-surface font-semibold">Organization users</h2>
        {usersQuery.isLoading && <p className="mt-4 text-sm text-on-surface-variant">Loading users…</p>}
        {usersQuery.isError && <p role="alert" className="mt-4 text-sm text-destructive">{errorMessage(usersQuery.error)}</p>}
        {usersQuery.data && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-outline-variant text-on-surface-variant"><th className="py-2 pr-3">Email</th><th className="py-2 pr-3">Name</th><th className="py-2 pr-3">Role</th><th className="py-2 pr-3">Status</th><th className="py-2">Actions</th></tr></thead>
              <tbody>
                {usersQuery.data.map((user) => (
                  <tr key={user.id} className="border-b border-outline-variant/60 text-on-surface">
                    <td className="py-2 pr-3">{user.email}</td>
                    <td className="py-2 pr-3">{[user.firstName, user.lastName].filter(Boolean).join(' ') || '—'}</td>
                    <td className="py-2 pr-3">
                      <select
                        aria-label={`Role for ${user.email}`}
                        value={editedRoles[user.id] ?? user.role}
                        onChange={(event) => setEditedRoles((previous) => ({
                          ...previous,
                          [user.id]: event.target.value as ManagedUser['role'],
                        }))}
                        className="rounded border border-outline-variant bg-surface-container-low px-2 py-1"
                      >
                        {roles.map((item) => <option key={item} value={item}>{item}</option>)}
                      </select>
                    </td>
                    <td className="py-2 pr-3">{user.isActive ? 'Active' : 'Disabled'}</td>
                    <td className="py-2">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          disabled={(editedRoles[user.id] ?? user.role) === user.role || updateMutation.isPending}
                          onClick={() => updateMutation.mutate({ id: user.id, newRole: editedRoles[user.id] ?? user.role })}
                          className="rounded border border-outline-variant px-2 py-1 text-xs disabled:opacity-50"
                        >
                          Save role
                        </button>
                        <button
                          type="button"
                          disabled={statusMutation.isPending}
                          onClick={() => statusMutation.mutate({ id: user.id, isActive: !user.isActive })}
                          className="rounded border border-outline-variant px-2 py-1 text-xs disabled:opacity-50"
                        >
                          {user.isActive ? 'Disable' : 'Enable'}
                        </button>
                        <button
                          type="button"
                          disabled={deleteMutation.isPending || !user.isActive}
                          onClick={() => {
                            if (window.confirm(`Delete ${user.email}? The account will be deactivated and retained for audit history.`)) {
                              deleteMutation.mutate(user.id);
                            }
                          }}
                          className="rounded border border-destructive px-2 py-1 text-xs text-destructive disabled:opacity-50"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {usersQuery.data.length === 0 && <tr><td colSpan={5} className="py-4 text-center text-on-surface-variant">No users found.</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
