import { useState } from "react";
import AuthCard from "./components/AuthCard";
import ChatPage from "./components/ChatPage";

const TOKEN_KEY = "smart_travel_access_token";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [authMode, setAuthMode] = useState("login");
  const [authNotice, setAuthNotice] = useState("");

  const handleLoginSuccess = (nextToken) => {
    localStorage.setItem(TOKEN_KEY, nextToken);
    setToken(nextToken);
    setAuthNotice("");
  };

  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setAuthMode("login");
    setAuthNotice("You have been logged out.");
  };

  const handleRegisteredWithoutToken = () => {
    setAuthMode("login");
    setAuthNotice("Registration complete. Please sign in to continue.");
  };

  return (
    <div className="app-shell">
      <div className="background-orb orb-one" />
      <div className="background-orb orb-two" />
      {!token ? (
        <main className="auth-wrap">
          <AuthCard
            mode={authMode}
            onModeChange={setAuthMode}
            onLoginSuccess={handleLoginSuccess}
            onRegisteredWithoutToken={handleRegisteredWithoutToken}
            notice={authNotice}
          />
        </main>
      ) : (
        <ChatPage token={token} onLogout={handleLogout} onUnauthorized={handleLogout} />
      )}
    </div>
  );
}

export default App;
