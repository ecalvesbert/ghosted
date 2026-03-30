"use client";

import { type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode } from "react";

// --- Button ---

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "destructive" | "ghost";
  size?: "sm" | "md" | "lg";
}

export function Button({ variant = "primary", size = "md", className = "", ...props }: ButtonProps) {
  const base = "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] disabled:pointer-events-none disabled:opacity-50";
  const variants: Record<string, string> = {
    primary: "bg-[var(--primary)] text-[var(--primary-foreground)] hover:bg-[var(--primary)]/90",
    secondary: "bg-[var(--muted)] text-[var(--foreground)] hover:bg-[var(--muted)]/80",
    destructive: "bg-[var(--destructive)] text-white hover:bg-[var(--destructive)]/90",
    ghost: "hover:bg-[var(--accent)] text-[var(--foreground)]",
  };
  const sizes: Record<string, string> = {
    sm: "h-8 px-3 text-sm",
    md: "h-10 px-4 text-sm",
    lg: "h-12 px-6 text-base",
  };
  return <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props} />;
}

// --- Input ---

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

export function Input({ label, className = "", id, ...props }: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && <label htmlFor={id} className="text-sm text-[var(--muted-foreground)]">{label}</label>}
      <input
        id={id}
        className={`flex h-10 w-full rounded-md border border-[var(--border)] bg-[var(--input)] px-3 py-2 text-sm text-[var(--foreground)] placeholder:text-[var(--muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] ${className}`}
        {...props}
      />
    </div>
  );
}

// --- Card ---

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div className={`rounded-lg border border-[var(--border)] bg-[var(--card)] p-6 ${className}`}>
      {children}
    </div>
  );
}

// --- Badge ---

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "success" | "warning" | "destructive";
  className?: string;
}

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  const variants: Record<string, string> = {
    default: "bg-[var(--muted)] text-[var(--muted-foreground)]",
    success: "bg-emerald-500/20 text-emerald-400",
    warning: "bg-amber-500/20 text-amber-400",
    destructive: "bg-red-500/20 text-red-400",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}
