import { FileX2 } from "lucide-react"
import React from "react"
import { cn } from "@/shared/lib/utils"

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  title: string
  description?: string
  icon?: React.ReactNode
}

export function EmptyState({ title, description, icon, className, ...props }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex min-h-[300px] flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center animate-in fade-in-50",
        className
      )}
      {...props}
    >
      <div className="mx-auto flex max-w-[420px] flex-col items-center justify-center text-center">
        {icon ? (
          <div className="mb-4 text-muted-foreground">{icon}</div>
        ) : (
          <FileX2 className="mb-4 h-10 w-10 text-muted-foreground" />
        )}
        <h3 className="mt-4 text-lg font-semibold">{title}</h3>
        {description && <p className="mb-4 mt-2 text-sm text-muted-foreground">{description}</p>}
      </div>
    </div>
  )
}
