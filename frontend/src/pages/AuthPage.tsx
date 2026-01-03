import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
// import { apiClient } from '@/lib/api'
import { authService } from '@/services/auth.service'

export function AuthPage({ onLogin }: { onLogin: () => void }) {
  const [account, setAccount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async () => {
    if (!account) return

    setLoading(true)
    setError(null)

    try {
      await authService.login({ account: account })
      onLogin()
    } catch {
      setError('Snowflake authentication failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-full items-center justify-center">
      <Card className="w-full max-w-sm p-6 space-y-4">
        <h1 className="text-xl font-bold text-center">
          Login with Snowflake
        </h1>

        <Input
          placeholder="Account identifier (e.g. abc123.eu-west-1)"
          value={account}
          onChange={(e) => setAccount(e.target.value)}
        />

        {error && (
          <p className="text-sm text-red-500 text-center">
            {error}
          </p>
        )}

        <Button
          onClick={handleLogin}
          disabled={loading}
          className="w-full"
        >
          {loading ? 'Redirecting…' : 'Continue'}
        </Button>
      </Card>
    </div>
  )
}
