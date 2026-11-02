'use client';

import React from 'react';
import Link from 'next/link';
import { motion } from 'motion/react';
import { 
  TrendingUp, 
  BarChart3, 
  Newspaper, 
  Building2, 
  ArrowRight, 
  CheckCircle2,
  ShieldCheck,
  Zap,
  Globe
} from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 font-sans">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 bg-white/80 dark:bg-[#0B0F19]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="bg-emerald-600 p-1.5 rounded-lg">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight">NEPSE Insight</span>
            </div>
            <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600 dark:text-slate-400">
              <a href="#features" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Features</a>
              <a href="#about" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">About</a>
              <Link href="/login" className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">Login</Link>
              <Link 
                href="/register" 
                className="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-700 transition-colors shadow-sm shadow-emerald-200 dark:shadow-none"
              >
                Get Started
              </Link>
            </div>
            {/* Mobile menu button - simplified for now */}
            <div className="md:hidden flex items-center">
              <Link href="/login" className="text-sm font-medium text-emerald-600">Login</Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full -z-10">
          <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-emerald-500/10 blur-[120px]" />
          <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-blue-500/10 blur-[120px]" />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-xs font-semibold mb-6"
          >
            <Zap className="w-3 h-3" />
            <span>Next-Gen Market Analytics for NEPSE</span>
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-5xl lg:text-7xl font-extrabold tracking-tight mb-6 leading-[1.1]"
          >
            Master the Market with <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-600 to-emerald-400 dark:from-emerald-500 dark:to-emerald-300">
              Data-Driven Insights
            </span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="max-w-2xl mx-auto text-lg text-slate-600 dark:text-slate-400 mb-10 leading-relaxed"
          >
            Unlock professional-grade stock analysis, real-time market intelligence, and comprehensive company data. 
            Empowering investors to make informed decisions in the Nepal Stock Exchange.
          </motion.p>
          
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row items-center justify-center gap-4"
          >
            <Link 
              href="/register" 
              className="group w-full sm:w-auto flex items-center justify-center gap-2 bg-emerald-600 text-white px-8 py-4 rounded-xl font-semibold hover:bg-emerald-700 transition-all hover:scale-105 shadow-lg shadow-emerald-200 dark:shadow-none"
            >
              Get Started Now
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link 
              href="/login" 
              className="w-full sm:w-auto px-8 py-4 rounded-xl font-semibold border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-all"
            >
              Sign In
            </Link>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-20 lg:py-32 bg-slate-50 dark:bg-[#0E1422]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">Powerful Tools for Every Investor</h2>
            <p className="text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
              Everything you need to track, analyze, and understand the Nepal Stock Exchange in one unified platform.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <FeatureCard 
              icon={<BarChart3 className="w-6 h-6" />}
              title="Market Insights"
              description="Get a high-level overview of market trends, index performance, and key technical indicators."
              color="emerald"
            />
            <FeatureCard 
              icon={<TrendingUp className="w-6 h-6" />}
              title="Stock Analysis"
              description="Deep dive into individual company performance with detailed metrics and comparative analysis."
              color="blue"
            />
            <FeatureCard 
              icon={<Newspaper className="w-6 h-6" />}
              title="Market News"
              description="Stay updated with the latest curated news and intelligence from trusted financial sources."
              color="purple"
            />
            <FeatureCard 
              icon={<Building2 className="w-6 h-6" />}
              title="Company Data"
              description="Access comprehensive information about listed companies, including fundamentals and reports."
              color="orange"
            />
          </div>
        </div>
      </section>

      {/* Why Choose Us Section */}
      <section id="about" className="py-20 lg:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col lg:flex-row items-center gap-16">
            <div className="flex-1">
              <div className="relative">
                <div className="absolute -top-4 -left-4 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl -z-10" />
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-4 mt-8">
                    <StatBox label="Accuracy" value="99.9%" icon={<ShieldCheck className="w-4 h-4" />} />
                    <StatBox label="Update Frequency" value="Real-time" icon={<Zap className="w-4 h-4" />} />
                  </div>
                  <div className="space-y-4">
                    <StatBox label="Data Sources" value="Multi-channel" icon={<Globe className="w-4 h-4" />} />
                    <StatBox label="User Satisfaction" value="High" icon={<CheckCircle2 className="w-4 h-4" />} />
                  </div>
                </div>
              </div>
            </div>
            <div className="flex-1 text-left">
              <h2 className="text-3xl lg:text-4xl font-bold mb-6 leading-tight">
                Built for the Modern <br />
                Nepalese Investor
              </h2>
              <p className="text-slate-600 dark:text-slate-400 mb-8 text-lg leading-relaxed">
                NEPSE Insight isn't just a data aggregator. It's a sophisticated analysis engine that transforms 
                raw market data into actionable intelligence. Whether you are a day trader or a long-term 
                investor, our platform provides the clarity you need.
              </p>
              <ul className="space-y-4">
                {[
                  'Comprehensive historical data tracking',
                  'Intelligent news categorization',
                  'Company-to-company comparative analysis',
                  'Clean, intuitive professional interface'
                ].map((item, i) => (
                  <li key={i} className="flex items-center gap-3 text-slate-700 dark:text-slate-300">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0B0F19]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row justify-between items-center gap-8">
            <div className="flex items-center gap-2">
              <div className="bg-emerald-600 p-1 rounded-lg">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <span className="text-lg font-bold tracking-tight">NEPSE Insight</span>
            </div>
            <div className="flex gap-8 text-sm text-slate-500 dark:text-slate-400">
              <a href="#" className="hover:text-emerald-600 transition-colors">Terms</a>
              <a href="#" className="hover:text-emerald-600 transition-colors">Privacy</a>
              <a href="#" className="hover:text-emerald-600 transition-colors">Contact</a>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              © {new Date().getFullYear()} NEPSE Insight. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description, color }: { 
  icon: React.ReactNode, 
  title: string, 
  description: string, 
  color: 'emerald' | 'blue' | 'purple' | 'orange' 
}) {
  const colorMap = {
    emerald: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-500/20',
    blue: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-200 dark:border-blue-500/20',
    purple: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-200 dark:border-purple-500/20',
    orange: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-500/20',
  };

  return (
    <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] hover:border-emerald-500 dark:hover:border-emerald-500 transition-all group">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 border transition-colors ${colorMap[color]}`}>
        {icon}
      </div>
      <h3 className="text-xl font-bold mb-2 group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">{title}</h3>
      <p className="text-slate-600 dark:text-slate-400 text-sm leading-relaxed">
        {description}
      </p>
    </div>
  );
}

function StatBox({ label, value, icon }: { label: string, value: string, icon: React.ReactNode }) {
  return (
    <div className="p-4 rounded-xl bg-white dark:bg-[#111827] border border-slate-200 dark:border-slate-800 shadow-sm">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-emerald-600 dark:text-emerald-400">{icon}</span>
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
