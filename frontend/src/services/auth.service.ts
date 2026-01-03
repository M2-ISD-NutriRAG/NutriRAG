import { apiClient } from '@/lib/api'

export interface LoginRequest {
  account: string
}

export interface LoginResponse {
  ok: boolean
}

export const authService = {
  async login(payload: LoginRequest): Promise<LoginResponse> {
    const { data } = await apiClient.post('/auth/login', payload)
    return data
  },

  async me(): Promise<LoginResponse> {
    const { data } = await apiClient.get('/auth/me')
    return data
  },

  async logout(): Promise<void> {
    await apiClient.post('/auth/logout')
  },
}