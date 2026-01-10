import { useState, useRef, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { ChatPage } from './pages/ChatPage'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { authService } from './services/auth.service'
import { Loader2 } from 'lucide-react'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function AppContent() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const authInitialized = useRef(false);

  useEffect(() => {
    const handleAuth = async () => {
      // Prevents double-execution in React Strict Mode
      if (authInitialized.current) return;
      authInitialized.current = true;

      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      const savedAccount = localStorage.getItem('pending_snowflake_account');

      if (code && savedAccount) {
        // 1. Immediately clean URL to prevent re-processing on manual refresh
        window.history.replaceState({}, document.title, window.location.pathname);

        try {
          const result = await authService.finalizeLogin(code, savedAccount);
          if (result.ok) {
            localStorage.setItem('snowflake_token', result.access_token);
            localStorage.setItem('snowflake_account_display', result.username || savedAccount);
            setIsAuthenticated(true);
          }
        } catch (error) {
          console.error("Login finalization failed", error);
        } finally {
          localStorage.removeItem('pending_snowflake_account');
          setLoading(false);
        }
      } else {
        // 2. Regular check for existing session
        const existingToken = localStorage.getItem('snowflake_token');
        if (existingToken) {
          setIsAuthenticated(true);
        }
        setLoading(false);
      }
    };

    handleAuth();
  }, []);

  // While checking tokens, show a clean loading screen
  if (loading) {
    return (
      <div className="flex h-screen w-full flex-col items-center justify-center gap-4 bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm font-medium text-muted-foreground">Authenticating with Snowflake...</p>
      </div>
    );
  }

  // If not logged in, only show the AuthPage
  if (!isAuthenticated) {
    return <AuthPage />;
  }

  // If logged in, show the Layout and Routes
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/chat/:id" element={<ChatPage />} />
        {/* Redirect any unknown paths to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

// Final App wrapper
function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App