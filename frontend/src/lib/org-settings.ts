export const ORG_SETTINGS_KEY = "vizora_org_settings";

export interface OrgDefaultLocation {
  locationName: string;
  latitude: number;
  longitude: number;
}

const FALLBACK_ORG_LOCATION: OrgDefaultLocation = {
  locationName: "Bengaluru Traffic Demo Zone",
  latitude: 12.9716,
  longitude: 77.5946,
};

function parseCoordinate(value: unknown) {
  const parsed = typeof value === "number" ? value : Number(String(value ?? "").trim());
  return Number.isFinite(parsed) ? parsed : null;
}

export function getStoredOrgDefaultLocation(): OrgDefaultLocation {
  if (typeof window === "undefined") return FALLBACK_ORG_LOCATION;

  try {
    const raw = localStorage.getItem(ORG_SETTINGS_KEY);
    if (!raw) return FALLBACK_ORG_LOCATION;
    const saved = JSON.parse(raw);
    const settings = saved.settings ?? {};
    const latitude = parseCoordinate(settings.default_location_latitude);
    const longitude = parseCoordinate(settings.default_location_longitude);

    if (latitude == null || longitude == null) return FALLBACK_ORG_LOCATION;

    return {
      locationName: String(settings.default_location_name || FALLBACK_ORG_LOCATION.locationName),
      latitude,
      longitude,
    };
  } catch {
    return FALLBACK_ORG_LOCATION;
  }
}
