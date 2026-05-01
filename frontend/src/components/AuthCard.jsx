import { useState } from "react";
import { login, register, ApiError } from "../api";

function AuthCard({
  mode,
  onModeChange,
  onLoginSuccess,
  onRegisteredWithoutToken,
  notice,
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isLoginMode = mode === "login";
  const title = isLoginMode ? "Welcome Back" : "Create Account";
  const subtitle = isLoginMode
    ? "Sign in to continue planning your next trip."
    : "Register to start using your travel agent.";
  const submitLabel = isLoginMode ? "Sign In" : "Create Account";
  const altLabel = isLoginMode ? "Need an account?" : "Already have an account?";
  const altAction = isLoginMode ? "Register" : "Sign In";

  const resetFormFeedback = () => {
    setError("");
  };

  const handleModeSwitch = () => {
    resetFormFeedback();
    onModeChange(isLoginMode ? "register" : "login");
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    resetFormFeedback();
    setSubmitting(true);

    try {
      if (isLoginMode) {
        const response = await login(email.trim(), password);
        if (!response?.access_token) {
          throw new ApiError("Login succeeded but no token was returned.", 500, response);
        }
        onLoginSuccess(response.access_token);
      } else {
        const response = await register(email.trim(), password);
        if (response?.access_token) {
          onLoginSuccess(response.access_token);
        } else {
          setEmail("");
          setPassword("");
          onRegisteredWithoutToken();
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="auth-card" aria-live="polite">
      <p className="brand-kicker">Smart Travel Planner</p>
      <h1>{title}</h1>
      <p className="muted-text">{subtitle}</p>
      {notice ? <div className="notice-banner">{notice}</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="form-field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
            disabled={submitting}
          />
        </label>
        <label className="form-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            autoComplete={isLoginMode ? "current-password" : "new-password"}
            minLength={8}
            required
            disabled={submitting}
          />
        </label>

        <button type="submit" className="primary-button" disabled={submitting}>
          {submitting ? "Please wait..." : submitLabel}
        </button>
      </form>

      <p className="auth-alt">
        {altLabel}{" "}
        <button type="button" className="text-button" onClick={handleModeSwitch}>
          {altAction}
        </button>
      </p>
    </section>
  );
}

export default AuthCard;
