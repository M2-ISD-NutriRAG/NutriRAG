import { useState } from 'react'

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Layout } from './components/Layout'
import { ChatPage } from './pages/ChatPage'
import { AuthPage } from './pages/AuthPage'
import { DashboardPage } from './pages/DashboardPage'
import { useEffect } from 'react'
import { authService } from './services/auth.service'

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const handleAuth = async () => {
      const params = new URLSearchParams(window.location.search);
      const code = params.get('code');
      // Retrieve the account name you saved before the redirect
      const savedAccount = localStorage.getItem('pending_snowflake_account');

      if (code && savedAccount) {
        try {
          const result = await authService.finalizeLogin(code, savedAccount);
          if (result.ok) {
            // Save the token! 
            // Usually you'd put it in a cookie or localStorage
            localStorage.setItem('snowflake_token', result.access_token);
            localStorage.setItem('snowflake_account_display', result.username || savedAccount);
            setIsAuthenticated(true);
          }
        } catch (error) {
          console.error("Login finalization failed", error);
        } finally {
          // Clean the URL so the code isn't sitting there anymore
          window.history.replaceState({}, document.title, window.location.pathname);
          localStorage.removeItem('pending_snowflake_account');
          setLoading(false);
        }
      } else {
        // No code in URL? Just check if we already have a token
        const existingToken = localStorage.getItem('snowflake_token');
        if (existingToken) setIsAuthenticated(true);
        setLoading(false);
      }
    };

    handleAuth();
  }, []);

  if (loading) return <div className='Spinner'>Finishing connection...</div>;

  if (!isAuthenticated)
    return <AuthPage />;
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App

