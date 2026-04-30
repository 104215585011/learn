create table if not exists public.floatvocab_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default 'FloatVocab User',
  avatar_url text not null default '',
  bio text not null default '',
  updated_at timestamptz not null default now()
);

create table if not exists public.floatvocab_sync_state (
  user_id uuid primary key references auth.users(id) on delete cascade,
  data jsonb not null default '{}'::jsonb,
  client_updated_at timestamptz,
  updated_at timestamptz not null default now()
);

create or replace function public.floatvocab_touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists floatvocab_profiles_touch_updated_at on public.floatvocab_profiles;
create trigger floatvocab_profiles_touch_updated_at
before update on public.floatvocab_profiles
for each row execute function public.floatvocab_touch_updated_at();

drop trigger if exists floatvocab_sync_state_touch_updated_at on public.floatvocab_sync_state;
create trigger floatvocab_sync_state_touch_updated_at
before update on public.floatvocab_sync_state
for each row execute function public.floatvocab_touch_updated_at();

alter table public.floatvocab_profiles enable row level security;
alter table public.floatvocab_sync_state enable row level security;

drop policy if exists "Users can read own FloatVocab profile" on public.floatvocab_profiles;
create policy "Users can read own FloatVocab profile"
on public.floatvocab_profiles
for select
using (auth.uid() = user_id);

drop policy if exists "Users can insert own FloatVocab profile" on public.floatvocab_profiles;
create policy "Users can insert own FloatVocab profile"
on public.floatvocab_profiles
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update own FloatVocab profile" on public.floatvocab_profiles;
create policy "Users can update own FloatVocab profile"
on public.floatvocab_profiles
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "Users can read own FloatVocab sync state" on public.floatvocab_sync_state;
create policy "Users can read own FloatVocab sync state"
on public.floatvocab_sync_state
for select
using (auth.uid() = user_id);

drop policy if exists "Users can insert own FloatVocab sync state" on public.floatvocab_sync_state;
create policy "Users can insert own FloatVocab sync state"
on public.floatvocab_sync_state
for insert
with check (auth.uid() = user_id);

drop policy if exists "Users can update own FloatVocab sync state" on public.floatvocab_sync_state;
create policy "Users can update own FloatVocab sync state"
on public.floatvocab_sync_state
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
