import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const getAvatarColor = (name: string) => {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  // HSL: Hue (0-360), Saturation (65%), Lightness (45%) 
  // This keeps the colors distinct but visually balanced
  return `hsl(${Math.abs(hash) % 360}, 65%, 45%)`;
};

export const getInitials = (name: string) => {
  if (!name) return "??";
  const parts = name.split(/[\s._-]+/); // Split by space, dot, or dash
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};