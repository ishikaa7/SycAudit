import { createContext, useCallback, useContext, useMemo, useState } from "react";
import {
  clearAuth,
  extractAuthPayload,
  getStoredToken,
  getStoredUser,
  storeAuth,
} from "../api/client.js";
import { login as apiLogin, signup as apiSignup } from "../api/auth.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser);

  const token = getStoredToken();
  const isAuthenticated = Boolean(token);

  const signin = useCallback(async (credentials) => {
    const res = await apiLogin(credentials);
    const { token: nextToken, user: nextUser } = extractAuthPayload(res.data || res);
    if (!nextToken) {
      throw new Error("Sign-in succeeded but no token was returned by the server.");
    }
    storeAuth(nextToken, nextUser);
    setUser(nextUser);
    return nextUser;
  }, []);

  const signup = useCallback(async (payload) => {
    const res = await apiSignup(payload);
    const { token: nextToken, user: nextUser } = extractAuthPayload(res.data || res);
    if (!nextToken) {
      throw new Error("Account created but no token was returned by the server.");
    }
    storeAuth(nextToken, nextUser);
    setUser(nextUser);
    return nextUser;
  }, []);

  const signout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      isAuthenticated,
      signin,
      signup,
      signout,
    }),
    [user, token, isAuthenticated, signin, signup, signout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}