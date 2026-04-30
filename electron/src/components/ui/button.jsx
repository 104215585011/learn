import { cn } from "@/lib/utils";

const variants = {
  primary: "bg-primary text-primary-foreground hover:bg-[#4F46E5] border-transparent",
  secondary: "bg-white text-foreground border-border hover:bg-[#F3F4F6]",
  danger: "bg-white text-[#EF4444] border-[#FECACA] hover:bg-[#FEF2F2]",
  ghost: "bg-transparent text-muted-foreground border-transparent hover:bg-muted",
};

export function Button({ className, variant = "secondary", ...props }) {
  return (
    <button
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-lg border-[1.5px] px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-[#E0E7FF]",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
