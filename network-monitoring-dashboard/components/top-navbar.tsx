'use client';

import { CheckCircle, AlertCircle, User } from 'lucide-react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';

interface TopNavbarProps {
  status?: 'healthy' | 'warning';
}

export function TopNavbar({ status = 'healthy' }: TopNavbarProps) {
  return (
    <header className="fixed top-0 left-0 right-0 md:left-64 h-16 border-b border-border bg-background px-4 md:px-8 flex items-center justify-between z-40">
      <div className="flex-1 min-w-0">
        <h1 className="text-lg md:text-2xl font-bold text-foreground truncate">
          Network Traffic Monitor
        </h1>
      </div>
      <div className="flex items-center gap-4 md:gap-6 flex-shrink-0">
        <div className="flex items-center gap-2">
          {status === 'healthy' ? (
            <>
              <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
              <span className="text-xs md:text-sm font-medium text-foreground hidden sm:inline">
                System Healthy
              </span>
            </>
          ) : (
            <>
              <AlertCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
              <span className="text-xs md:text-sm font-medium text-foreground hidden sm:inline">
                Warning
              </span>
            </>
          )}
        </div>
        <div className="h-8 w-px bg-border hidden md:block" />
        <Avatar className="h-10 w-10 cursor-pointer flex-shrink-0">
          <AvatarImage src="https://github.com/shadcn.png" alt="User" />
          <AvatarFallback>
            <User className="h-6 w-6" />
          </AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
