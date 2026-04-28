import { createContext, useContext, useState, ReactNode } from 'react';
import { getStoredTokens, storeTokens } from '../lib/api';

interface AuthUser {
  name: string;
  email: string;
  orgName: string;
  role: 'admin' | 'user';
  plan: 'Free' | 'Pro' | 'Enterprise';
  bioRegion?: string;
  signature?: string;
  country?: string;
  legalEntityName?: string;
  legalAddress?: string;
  postalCode?: string;
  registrationId?: string;
  taxId?: string;
  noticeEmail?: string;
  contactPhone?: string;
}

interface AuthContextType {
  user: AuthUser;
  tokens: { access: string; refresh: string } | null;
  isAuthenticated: boolean;
  setUser: (u: AuthUser) => void;
  setTokens: (t: { access: string; refresh: string } | null) => void;
  logout: () => void;
}

const defaultUser: AuthUser = {
  name: 'Sentinel User',
  email: 'user@sentinel.local',
  orgName: 'Your Organization',
  role: 'user',
  plan: 'Free',
  bioRegion: 'Europe (West)',
  signature: 'SENTINEL-USER',
  country: 'India',
  legalEntityName: 'Your Organization Pvt Ltd',
  legalAddress: 'Official registered office address',
  postalCode: '000000',
  registrationId: 'CIN/REG-ID',
  taxId: 'GST/VAT/TAX-ID',
  noticeEmail: 'legal@yourorg.com',
  contactPhone: '+00 0000 000000',
};

const AUTH_STORAGE_KEY = 'sentinel_user';

function readStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AuthUser>;
    if (!parsed.name || !parsed.email || !parsed.orgName) return null;

    return {
      ...defaultUser,
      ...parsed,
      role: parsed.role === 'admin' ? 'admin' : 'user',
      plan:
        parsed.plan === 'Enterprise'
          ? 'Enterprise'
          : parsed.plan === 'Pro'
          ? 'Pro'
          : 'Free',
    };
  } catch {
    return null;
  }
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<AuthUser>(() => readStoredUser() || defaultUser);
  const [tokens, setTokensState] = useState<{ access: string; refresh: string } | null>(() => getStoredTokens());

  const setUser = (u: AuthUser) => {
    setUserState(u);
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(u));
  };

  const setTokens = (t: { access: string; refresh: string } | null) => {
    setTokensState(t);
    storeTokens(t);
  };

  const logout = () => {
    setTokens(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{ user, tokens, isAuthenticated: Boolean(tokens?.access), setUser, setTokens, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
