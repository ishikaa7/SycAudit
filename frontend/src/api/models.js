import { api } from "./client.js";

export function getModels() {
  return api.get("/admin/models");
}

export function setModelActive(modelId, isActive) {
  return api.patch(`/admin/models/${modelId}`, { is_active: isActive });
}