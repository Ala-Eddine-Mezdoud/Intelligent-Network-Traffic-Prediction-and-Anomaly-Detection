import { createClient } from '@supabase/supabase-js'
import { Database } from './database.types'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || ''

if (!supabaseUrl || !supabaseKey) {
  console.error('[Supabase] Missing environment variables:', {
    url: supabaseUrl ? 'set' : 'MISSING',
    key: supabaseKey ? 'set' : 'MISSING'
  })
}

// Create typed Supabase client
export const supabase = createClient<Database>(supabaseUrl, supabaseKey, {
  auth: {
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: false
  },
  global: {
    headers: {
      'x-application-name': 'network-monitoring-dashboard'
    }
  }
})

// Test connection helper
export async function testConnection() {
  try {
    const { data, error } = await supabase.from('realtime_metrics').select('count').single()
    if (error) throw error
    return { ok: true, data }
  } catch (err: any) {
    console.error('[Supabase] Connection test failed:', err.message)
    return { ok: false, error: err.message }
  }
}
