import {
  Accessibility,
  Activity,
  Baby,
  Bug,
  Car,
  Flame,
  HardHat,
  House,
  PawPrint,
  PencilLine,
  PersonStanding,
  type LucideIcon,
} from "lucide-react";

/**
 * Pack identity table (redesign spec 3.7). The ONLY place pack colors
 * live; colors are identity only (icon tile + pack chip dot), never
 * verdicts.
 */
export interface PackIdentity {
  name: string;
  icon: LucideIcon;
  color: string;
}

export const PACKS: Record<string, PackIdentity> = {
  falls_older_adults: { name: "Parent's home (falls)", icon: PersonStanding, color: "#4F46E5" },
  babyproofing: { name: "Baby's home", icon: Baby, color: "#DB2777" },
  home_safety_inspection: { name: "Home safety inspection", icon: House, color: "#0F766E" },
  workplace_safety: { name: "Workplace safety", icon: HardHat, color: "#4D7C0F" },
  pet_safety: { name: "Pet-safe home", icon: PawPrint, color: "#7C3AED" },
  fire_safety: { name: "Fire safety", icon: Flame, color: "#EA580C" },
  car_seat_check: { name: "Car seat check", icon: Car, color: "#C026D3" },
  earthquake_ready: { name: "Earthquake-ready home", icon: Activity, color: "#78716C" },
  home_from_hospital: { name: "Home from hospital", icon: Accessibility, color: "#0369A1" },
  mosquito_breeding: { name: "Mosquito breeding sites", icon: Bug, color: "#334155" },
};

export const CUSTOM_PACK: PackIdentity = {
  name: "Your own checklist",
  icon: PencilLine,
  color: "#6B7280",
};

export function packIdentity(packId: string): PackIdentity {
  if (packId.startsWith("custom")) return CUSTOM_PACK;
  return PACKS[packId] ?? CUSTOM_PACK;
}
