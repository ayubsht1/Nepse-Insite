import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useRouter } from 'next/navigation';
import {
  clearAuthTokens,
  fetchCurrentUser,
  getAccessToken,
  login as requestLogin,
  logout as requestLogout,
  register as requestRegistration,
} from '../services/api';
import {
  Company,
  NavigationTab,
  NotificationItem,
  UserProfile,
  UserRole,
} from '../types';

interface AppContextType {
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  selectedCompanyId: string | null;
  setSelectedCompanyId: (id: string | null) => void;
  selectedCompany: Company | undefined;
  userProfile: UserProfile | null;
  userRole: UserRole;
  authLoading: boolean;
  authError: string | null;
  isSearchOpen: boolean;
  setIsSearchOpen: (open: boolean) => void;
  sidebarCollapsed: boolean;
  setSidebarCollapsed: React.Dispatch<React.SetStateAction<boolean>>;
  mobileMenuOpen: boolean;
  setMobileMenuOpen: React.Dispatch<React.SetStateAction<boolean>>;
  notifications: NotificationItem[];
  markNotificationAsRead: (id: string) => void;
  markAllNotificationsAsRead: () => void;
  unreadNotificationsCount: number;
  login: (username: string, password: string) => Promise<void>;
  register: (input: {
    username: string;
    first_name: string;
    email: string;
    password: string;
  }) => Promise<void>;
  handleLogout: () => Promise<void>;
  theme: 'dark' | 'light';
  setTheme: (theme: 'dark' | 'light') => void;
  toggleTheme: () => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

function toUserProfile(user: {
  username: string;
  first_name: string;
  email: string;
  role: UserRole;
}): UserProfile {
  return {
    name: user.first_name.trim() || user.username,
    email: user.email,
    role: user.role,
  };
}

export const AppProvider: React.FC<{
  children: React.ReactNode;
  initialTab?: NavigationTab;
}> = ({ children, initialTab = 'overview' }) => {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<NavigationTab>(initialTab);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [theme, setThemeState] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    let active = true;
    const handleExpiredSession = () => {
      clearAuthTokens();
      setUserProfile(null);
      setAuthError('Your session expired. Please sign in again.');
      router.replace('/login');
    };
    window.addEventListener('auth:expired', handleExpiredSession);

    try {
      if (window.localStorage.getItem('nepse_insight_theme') === 'light') {
        setThemeState('light');
      }
    } catch (error) {
      console.warn('Unable to read the saved theme preference.', error);
    }

    if (!getAccessToken()) {
      setAuthLoading(false);
    } else {
      fetchCurrentUser()
        .then((user) => {
          if (active) {
            setUserProfile(toUserProfile(user));
            setAuthError(null);
          }
        })
        .catch((error: Error) => {
          if (active) {
            clearAuthTokens();
            setAuthError(error.message);
          }
        })
        .finally(() => {
          if (active) setAuthLoading(false);
        });
    }

    return () => {
      active = false;
      window.removeEventListener('auth:expired', handleExpiredSession);
    };
  }, [router]);

  const login = async (username: string, password: string) => {
    setAuthError(null);
    await requestLogin(username, password);
    try {
      const user = await fetchCurrentUser();
      setUserProfile(toUserProfile(user));
    } catch (error) {
      clearAuthTokens();
      throw error;
    }
  };

  const register = async (input: {
    username: string;
    first_name: string;
    email: string;
    password: string;
  }) => {
    await requestRegistration(input);
    await login(input.username, input.password);
  };

  const handleLogout = async () => {
    try {
      await requestLogout();
    } finally {
      clearAuthTokens();
      setUserProfile(null);
      setActiveTab('overview');
      router.replace('/login');
    }
  };

  const setTheme = (newTheme: 'dark' | 'light') => {
    setThemeState(newTheme);
    try {
      window.localStorage.setItem('nepse_insight_theme', newTheme);
    } catch (error) {
      console.warn('Unable to save the theme preference.', error);
    }
    document.documentElement.classList.toggle('dark', newTheme === 'dark');
  };

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        setIsSearchOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const markNotificationAsRead = (id: string) => {
    setNotifications((current) =>
      current.map((item) => (item.id === id ? { ...item, read: true } : item)),
    );
  };
  const markAllNotificationsAsRead = () => {
    setNotifications((current) => current.map((item) => ({ ...item, read: true })));
  };
  const unreadNotificationsCount = useMemo(
    () => notifications.filter((notification) => !notification.read).length,
    [notifications],
  );

  return (
    <AppContext.Provider
      value={{
        activeTab,
        setActiveTab,
        selectedCompanyId,
        setSelectedCompanyId,
        selectedCompany: undefined,
        userProfile,
        userRole: userProfile?.role ?? 'viewer',
        authLoading,
        authError,
        isSearchOpen,
        setIsSearchOpen,
        sidebarCollapsed,
        setSidebarCollapsed,
        mobileMenuOpen,
        setMobileMenuOpen,
        notifications,
        markNotificationAsRead,
        markAllNotificationsAsRead,
        unreadNotificationsCount,
        login,
        register,
        handleLogout,
        theme,
        setTheme,
        toggleTheme,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
