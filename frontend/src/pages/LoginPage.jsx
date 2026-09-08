import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { errorMessage } from "../api/client.js";
import Spinner from "../components/ui/Spinner.jsx";

function validate(values) {
  const errors = {};
  if (!values.email.trim()) errors.email = "Email is required.";
  else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
    errors.email = "Enter a valid email address.";
  }
  if (!values.password) errors.password = "Password is required.";
  return errors;
}

export default function LoginPage() {
  const { signin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [values, setValues] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from || "/dashboard";

  const handleChange = (e) => {
    const { name, value } = e.target;
    setValues((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: "" }));
    setServerError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const nextErrors = validate(values);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setSubmitting(true);
    setServerError("");
    try {
      await signin({ email: values.email.trim(), password: values.password });
      navigate(from, { replace: true });
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const field = (name, label, type = "text", placeholder = "") => (
    <div>
      <label htmlFor={name} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        autoComplete={name}
        value={values[name]}
        onChange={handleChange}
        placeholder={placeholder}
        className={`mt-1.5 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition-colors placeholder:text-slate-400 focus:ring-2 ${
          errors[name]
            ? "border-red-300 focus:border-red-400 focus:ring-red-200"
            : "border-slate-200 focus:border-brand-500 focus:ring-brand-200"
        }`}
      />
      {errors[name] && <p className="mt-1 text-xs text-red-600">{errors[name]}</p>}
    </div>
  );

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-brand-600 text-white shadow-md">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-6 w-6">
              <path d="M7 17V9.5a3.5 3.5 0 0 1 7 0V17" />
              <path d="M7 13h7" />
              <path d="M9 22h6" />
              <path d="M12 15v3" />
              <path d="M20 12c0-4.4-3.6-8-8-8S4 7.6 4 12" />
            </svg>
          </div>
          <h1 className="mt-4 text-2xl font-semibold tracking-tight text-slate-900">SycAudit</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to audit AI sycophancy</p>
        </div>

        <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
          {serverError && (
            <div className="mb-4 rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700 ring-1 ring-inset ring-red-200">
              {serverError}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {field("email", "Email address", "email", "you@example.com")}
            {field("password", "Password", "password", "••••••••")}
            <button
              type="submit"
              disabled={submitting}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-400 focus:ring-offset-2 disabled:opacity-60"
            >
              {submitting && <Spinner className="h-4 w-4" />}
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-slate-500">
            No account yet?{" "}
            <Link to="/signup" className="font-semibold text-brand-600 hover:text-brand-700">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}