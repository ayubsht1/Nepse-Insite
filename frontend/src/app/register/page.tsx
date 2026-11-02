'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ApiError, login, register } from '../../services/api';
import { TrendingUp, User, Mail, Lock, ArrowRight, Loader2, Eye, EyeOff } from 'lucide-react';
import { motion } from 'motion/react';

export default function RegisterPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [firstName, setFirstName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const clearFieldError = (field: string) => {
    setFieldErrors((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setGeneralError('');
    setFieldErrors({});

    // Client-side validation for password confirmation
    if (password !== confirmPassword) {
      setFieldErrors({ confirmPassword: 'Passwords do not match' });
      setSubmitting(false);
      return;
    }

    try {
      await register({
        username,
        first_name: firstName,
        email,
        password,
      });
      await login(username, password);
      router.replace('/dashboard');
    } catch (error) {
      const apiError = error as ApiError;
      if (apiError.data && typeof apiError.data === 'object') {
        const data = apiError.data as Record<string, any>;
        const newFieldErrors: Record<string, string> = {};
        
        Object.entries(data).forEach(([field, messages]) => {
          if (field === 'non_field_errors') {
            setGeneralError(Array.isArray(messages) ? messages[0] : String(messages));
          } else {
            newFieldErrors[field] = Array.isArray(messages) ? messages[0] : String(messages);
          }
        });
        setFieldErrors(newFieldErrors);
      } else {
        setGeneralError(apiError.message || 'Unable to register.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const renderError = (field: string) => {
    const error = fieldErrors[field];
    if (!error) return null;
    return (
      <motion.p 
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-xs text-rose-600 mt-1"
      >
        {error}
      </motion.p>
    );
  };

  const getInputStyles = (field: string) => {
    const baseStyles = "block w-full pl-10 pr-10 py-2.5 rounded-lg border bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 focus:ring-2 outline-none transition-all";
    const errorStyles = fieldErrors[field] 
      ? "border-rose-500 focus:ring-rose-500 dark:border-rose-500" 
      : "border-slate-300 dark:border-slate-700 focus:ring-emerald-500";
    
    return `${baseStyles} ${errorStyles}`;
  };

  return (
    <main className="min-h-screen flex items-center justify-center bg-slate-50 p-4 dark:bg-[#0B0F19] relative overflow-hidden">
      {/* Background Decorative Elements */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-emerald-500/5 blur-[120px] -z-10" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-blue-500/5 blur-[120px] -z-10" />

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-emerald-600 text-white mb-4 shadow-lg shadow-emerald-200 dark:shadow-none">
            <TrendingUp className="w-6 h-6" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            Create Account
          </h1>
          <p className="mt-2 text-slate-500 dark:text-slate-400">
            Join NEPSE Insight and start analyzing the market.
          </p>
        </div>

        <div className="bg-white dark:bg-[#111827] p-8 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="grid grid-cols-1 gap-5">
              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Username
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-5 h-5" />
                  </div>
                  <input
                    autoComplete="username"
                    required
                    minLength={1}
                    value={username}
                    onChange={(event) => {
                      setUsername(event.target.value);
                      clearFieldError('username');
                    }}
                    placeholder="Choose a username"
                    className={getInputStyles('username')}
                  />
                </div>
                {renderError('username')}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  First Name
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <User className="w-5 h-5" />
                  </div>
                  <input
                    autoComplete="given-name"
                    value={firstName}
                    onChange={(event) => {
                      setFirstName(event.target.value);
                      clearFieldError('first_name');
                    }}
                    placeholder="Your first name"
                    className={getInputStyles('first_name')}
                  />
                </div>
                {renderError('first_name')}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Mail className="w-5 h-5" />
                  </div>
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(event) => {
                      setEmail(event.target.value);
                      clearFieldError('email');
                    }}
                    placeholder="name@example.com"
                    className={getInputStyles('email')}
                  />
                </div>
                {renderError('email')}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-5 h-5" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    minLength={8}
                    required
                    value={password}
                    onChange={(event) => {
                      setPassword(event.target.value);
                      clearFieldError('password');
                    }}
                    placeholder="••••••••"
                    className={getInputStyles('password')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                  >
                    {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {renderError('password')}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                  Confirm Password
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-5 h-5" />
                  </div>
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    autoComplete="new-password"
                    required
                    value={confirmPassword}
                    onChange={(event) => {
                      setConfirmPassword(event.target.value);
                      clearFieldError('confirmPassword');
                    }}
                    placeholder="••••••••"
                    className={getInputStyles('confirmPassword')}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                  </button>
                </div>
                {renderError('confirmPassword')}
              </div>
            </div>

            {generalError && (
              <motion.p 
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                role="alert" 
                className="text-sm text-rose-600 bg-rose-50 dark:bg-rose-500/10 p-3 rounded-lg border border-rose-100 dark:border-rose-500/20"
              >
                {generalError}
              </motion.p>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700 transition-all disabled:opacity-60 shadow-lg shadow-emerald-200 dark:shadow-none active:scale-95"
            >
              {submitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                <>
                  Create Viewer Account
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Already have an account?{' '}
              <Link 
                className="text-emerald-600 dark:text-emerald-400 font-semibold hover:underline" 
                href="/login"
              >
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </motion.div>
    </main>
  );
}
