import { api } from "./client.js";

export function login(credentials) {
  return api.post("/auth/login", credentials);
}

export function signup(payload) {
  return api.post("/auth/signup", payload);
}