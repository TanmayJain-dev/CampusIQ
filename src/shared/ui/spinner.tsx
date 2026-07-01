import { Loader2 } from "lucide-react"
import { cn } from "@/shared/lib/utils"

export interface SpinnerProps extends React.SVGAttributes<SVGSVGElement> {
  size?: number | string
}

export function Spinner({ className, size = 24, ...props }: SpinnerProps) {
  return (
    <Loader2
      size={size}
      className={cn("animate-spin text-muted-foreground", className)}
      {...props}
    />
  )
}
