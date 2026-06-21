import Image from "next/image";

import { cn } from "@/lib/utils";

export function VizoraIcon({ className }: { className?: string }) {
  return (
    <Image
      src="/vizora-icon-generated.png"
      alt=""
      aria-hidden="true"
      width={256}
      height={256}
      className={cn("block shrink-0", className)}
    />
  );
}
