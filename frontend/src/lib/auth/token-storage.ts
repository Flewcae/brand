const ACCESS_KEY = "flewcae_access_token";
const REFRESH_KEY = "flewcae_refresh_token";

const isBrowser = () => typeof window !== "undefined";

export const tokenStorage = {
  getAccess(): string | null {
    return isBrowser() ? localStorage.getItem(ACCESS_KEY) : null;
  },
  getRefresh(): string | null {
    return isBrowser() ? localStorage.getItem(REFRESH_KEY) : null;
  },
  set(access: string, refresh: string) {
    if (!isBrowser()) return;
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  setAccess(access: string) {
    if (!isBrowser()) return;
    localStorage.setItem(ACCESS_KEY, access);
  },
  clear() {
    if (!isBrowser()) return;
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};
