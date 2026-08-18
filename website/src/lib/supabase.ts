import { createClient, type SupabaseClient } from '@supabase/supabase-js';

const supabaseUrl = (import.meta.env.VITE_SUPABASE_URL as string | undefined)?.trim() || '';
const supabaseAnonKey = (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined)?.trim() || '';

// Default: Admin username + password (FastAPI JWT), same as AWS.
// Opt in to Supabase email login only with VITE_USE_SUPABASE_AUTH=true.
const allowSupabase = import.meta.env.VITE_USE_SUPABASE_AUTH === 'true';
export const isSupabaseAuth = allowSupabase && Boolean(supabaseUrl && supabaseAnonKey);

export const supabase: SupabaseClient | null = isSupabaseAuth
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
      },
    })
  : null;
