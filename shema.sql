-- Execute no SQL Editor do Supabase. Cada usuário só enxerga os próprios dados (RLS).

create table if not exists public.memories (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  category text not null,
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  persona text,
  updated_at timestamptz not null default now()
);

create table if not exists public.chats (
  id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  messages jsonb not null default '[]',
  updated_at timestamptz not null default now()
);

alter table public.memories      enable row level security;
alter table public.user_settings enable row level security;
alter table public.chats         enable row level security;

drop policy if exists "dono_memories" on public.memories;
create policy "dono_memories" on public.memories for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "dono_settings" on public.user_settings;
create policy "dono_settings" on public.user_settings for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "dono_chats" on public.chats;
create policy "dono_chats" on public.chats for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Tarefas e lembretes (novo)
create table if not exists public.tasks (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  due text not null default '',
  done boolean not null default false,
  created_at timestamptz not null default now()
);
alter table public.tasks enable row level security;
drop policy if exists "dono_tasks" on public.tasks;
create policy "dono_tasks" on public.tasks for all
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
