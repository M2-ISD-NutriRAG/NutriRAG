import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Loader2 } from 'lucide-react' // Add this line
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
// import { apiClient } from '@/lib/api'
import { authService } from '@/services/auth.service'

export function AuthPage() {
  const [account, setAccount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async () => {
    if (!account) return
    setLoading(true)
    setError(null)

    localStorage.setItem('pending_snowflake_account', account);

    try {
      // This call should return the Snowflake OAuth URL
      // const resp = await authService.loginWithSnowflake({ account: account })
      await authService.loginWithSnowflake({ account: account })
    } catch {
      setError('Failed to reach authentication server')
      setLoading(false)
    }
  }

  return (
    // Changed h-full to min-h-screen to ensure it takes the full browser height
    // Added bg-slate-50 (optional) just to give the background some depth
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-50 p-4">
      <Card className="w-full max-w-sm p-6 space-y-4 shadow-lg">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-center tracking-tight">
            Login with Snowflake
          </h1>
          <p className="text-sm text-muted-foreground text-center">
            Enter your account identifier to continue
          </p>
        </div>

        <div className="space-y-4 pt-2">
          <Input
            placeholder="ORG-ACCOUNT (e.g. MYORG-MYAPP)"
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            className="focus-visible:ring-primary"
          />

          {error && (
            <p className="text-sm font-medium text-destructive text-center">
              {error}
            </p>
          )}

          <Button
            onClick={handleLogin}
            disabled={loading}
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Redirecting...
              </>
            ) : (
              'Continue'
            )}
          </Button>
        </div>
      </Card>
    </div>
  )
}