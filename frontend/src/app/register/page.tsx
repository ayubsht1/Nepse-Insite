'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, login, register } from '../../services/api';

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      await register({
        username,
        first_name: firstName,
        email,
        password,
      });
      await login(username, password);
      router.replace('/dashboard');
    } catch (registrationError) {
      setError((registrationError as ApiError).message || 'Unable to register.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 p-4 dark:bg-[#0B0F19]">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-5 rounded-2xl border border-slate-200 bg-white p-7 shadow-xl dark:border-slate-800 dark:bg-[#111827]"
      >
        <div>
          <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">
            NEPSE Insight
          </p>
          <h1 className="mt-2 text-2xl font-bold">Create an account</h1>
          <p className="mt-1 text-sm text-slate-500">
            New registrations receive read-only Viewer access.
          </p>
        </div>
        <label className="block text-sm">
          Username
          <input
            autoComplete="username"
            required
            minLength={1}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          />
        </label>
        <label className="block text-sm">
          First name
          <input
            autoComplete="given-name"
            value={firstName}
            onChange={(event) => setFirstName(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          />
        </label>
        <label className="block text-sm">
          Email
          <input
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          />
        </label>
        <label className="block text-sm">
          Password
          <input
            type="password"
            autoComplete="new-password"
            minLength={8}
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-300 bg-transparent px-3 py-2 dark:border-slate-700"
          />
        </label>
        {error && (
          <p role="alert" className="text-sm text-rose-600">
            {error}
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {submitting ? 'Creating account…' : 'Create Viewer account'}
        </button>
        <p className="text-center text-sm text-slate-500">
          Already registered?{' '}
          <Link className="text-emerald-600 hover:underline" href="/login">
            Sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
