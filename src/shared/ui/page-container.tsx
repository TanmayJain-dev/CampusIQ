import React from "react"
import { cn } from "@/shared/lib/utils"

interface PageContainerProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

export function PageContainer({ children, className, ...props }: PageContainerProps) {
  return (
    <div className={cn("container mx-auto px-4 py-8 md:px-8", className)} {...props}>
      {children}
    </div>
  )
}

interface SectionHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  action?: React.ReactNode
}

export function SectionHeader({ title, description, action, className, ...props }: SectionHeaderProps) {
  return (
    <div className={cn("flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8", className)} {...props}>
      <div className="space-y-1">
        <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
        {description && <p className="text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center">{action}</div>}
    </div>
  )
}
