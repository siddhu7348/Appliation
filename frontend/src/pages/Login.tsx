import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, Card, CardContent } from '@/components/ui';
import { api, ApiError } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

const DEMO_ACCOUNTS = [
  { email: 'manager@forecastiq.io', role: 'Store manager' },
  { email: 'director@forecastiq.io', role: 'Regional director' },
  { email: 'hq@forecastiq.io', role: 'HQ' },
  { email: 'admin@forecastiq.io', role: 'Admin' },
];

export default function LoginPage() {
  const [email, setEmail] = useState('manager@forecastiq.io');
  const [password, setPassword] = useState('ForecastIQ!2024');
  const { setToken, setUser } = useAuthStore();

  const mutation = useMutation({
    mutationFn: () => api.login(email, password),
    onSuccess: async (token) => {
      setToken(token.access_token);
      setUser(await api.me());
    },
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy px-4">
      <Card className="w-full max-w-md border-none">
        <CardContent className="p-8">
          <div className="mb-6 flex items-center gap-2">
            <span className="h-3 w-3 rounded-full bg-teal" aria-hidden />
            <h1 className="text-xl font-semibold text-navy">ForecastIQ</h1>
          </div>
          <p className="mb-6 text-sm text-slate-500">
            Sign in to the retail demand intelligence console.
          </p>

          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate();
            }}
          >
            <div>
              <label htmlFor="email" className="mb-1 block text-xs font-semibold text-slate-600">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
              />
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-xs font-semibold text-slate-600">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-10 w-full rounded-md border border-slate-300 px-3 text-sm focus:border-teal focus:outline-none focus:ring-1 focus:ring-teal"
              />
            </div>

            {mutation.isError ? (
              <p role="alert" className="rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-700">
                {(mutation.error as ApiError).message}
              </p>
            ) : null}

            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>

          <div className="mt-6 rounded-md bg-slate-50 p-3 text-xs text-slate-500">
            <p className="mb-1 font-semibold text-slate-600">Demo accounts (password ForecastIQ!2024)</p>
            <ul className="space-y-0.5">
              {DEMO_ACCOUNTS.map((account) => (
                <li key={account.email}>
                  <button
                    type="button"
                    className="text-teal-dark hover:underline"
                    onClick={() => setEmail(account.email)}
                  >
                    {account.email}
                  </button>{' '}
                  - {account.role}
                </li>
              ))}
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
