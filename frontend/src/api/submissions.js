import { api } from "./client.js";

export function createSubmission(originalPrompt) {
  return api.post("/submissions", { original_prompt: originalPrompt });
}

export function getSubmissions() {
  return api.get("/submissions");
}

export function getSubmission(submissionId) {
  return api.get(`/submissions/${submissionId}`);
}