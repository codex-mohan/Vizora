"use client";

import { useEffect, useRef, useState } from "react";
import { Layers, MapPin, Route } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { HotspotMapResponse } from "@/lib/types";

type GeoJsonData = Parameters<import("maplibre-gl").GeoJSONSource["setData"]>[0];
type MapInstance = import("maplibre-gl").Map;
type MapLibreModule = typeof import("maplibre-gl");

const POINT_SOURCE_ID = "violation-points";
const ROAD_SOURCE_ID = "violation-road-segments";
const FALLBACK_CENTER: [number, number] = [77.5946, 12.9716];

const DEFAULT_RASTER_STYLE = {
  version: 8 as const,
  sources: {
    osm: {
      type: "raster" as const,
      tiles: [
        "https://a.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://b.tile.openstreetmap.org/{z}/{x}/{y}.png",
        "https://c.tile.openstreetmap.org/{z}/{x}/{y}.png",
      ],
      tileSize: 256,
      attribution: "\u00a9 OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster" as const, source: "osm" }],
};

const EMPTY_POINTS: HotspotMapResponse["points"] = {
  type: "FeatureCollection",
  features: [],
};

const EMPTY_ROADS: HotspotMapResponse["road_segments"] = {
  type: "FeatureCollection",
  features: [],
};

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatPercent(value: unknown) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "n/a";
  return `${Math.round(number * 100)}%`;
}

function getMapStyle(): string | import("maplibre-gl").StyleSpecification {
  const envStyle = process.env.NEXT_PUBLIC_MAP_STYLE_URL;
  if (envStyle) return envStyle;
  return DEFAULT_RASTER_STYLE as import("maplibre-gl").StyleSpecification;
}

function addMapLayers(map: MapInstance) {
  if (!map.getSource(POINT_SOURCE_ID)) {
    map.addSource(POINT_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_POINTS as GeoJsonData,
    });
  }

  if (!map.getSource(ROAD_SOURCE_ID)) {
    map.addSource(ROAD_SOURCE_ID, {
      type: "geojson",
      data: EMPTY_ROADS as GeoJsonData,
    });
  }

  if (!map.getLayer("violation-road-glow")) {
    map.addLayer({
      id: "violation-road-glow",
      type: "line",
      source: ROAD_SOURCE_ID,
      paint: {
        "line-color": "#f97316",
        "line-opacity": 0.24,
        "line-width": ["interpolate", ["linear"], ["get", "weight"], 1, 8, 20, 18, 100, 30],
        "line-blur": 8,
      },
    });
  }

  if (!map.getLayer("violation-road-segments")) {
    map.addLayer({
      id: "violation-road-segments",
      type: "line",
      source: ROAD_SOURCE_ID,
      paint: {
        "line-color": [
          "case",
          ["==", ["get", "dominant_violation"], "red_light"],
          "#ef4444",
          ["==", ["get", "dominant_violation"], "wrong_side"],
          "#fb923c",
          ["==", ["get", "dominant_violation"], "illegal_parking"],
          "#38bdf8",
          "#facc15",
        ],
        "line-opacity": 0.86,
        "line-width": ["interpolate", ["linear"], ["get", "weight"], 1, 2.5, 20, 7, 100, 12],
      },
    });
  }

  if (!map.getLayer("violation-heat")) {
    map.addLayer({
      id: "violation-heat",
      type: "heatmap",
      source: POINT_SOURCE_ID,
      maxzoom: 16,
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "weight"], 0, 0, 5, 0.45, 50, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 5, 0.75, 14, 2.2],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 5, 18, 14, 42],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 12, 0.9, 16, 0.25],
        "heatmap-color": [
          "interpolate",
          ["linear"],
          ["heatmap-density"],
          0,
          "rgba(15,23,42,0)",
          0.2,
          "rgba(56,189,248,0.55)",
          0.45,
          "rgba(250,204,21,0.72)",
          0.72,
          "rgba(249,115,22,0.85)",
          1,
          "rgba(239,68,68,0.95)",
        ],
      },
    });
  }

  if (!map.getLayer("violation-points")) {
    map.addLayer({
      id: "violation-points",
      type: "circle",
      source: POINT_SOURCE_ID,
      minzoom: 9,
      paint: {
        "circle-color": "#f97316",
        "circle-radius": ["interpolate", ["linear"], ["get", "weight"], 1, 5, 20, 14, 100, 24],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#fff7ed",
        "circle-opacity": 0.88,
      },
    });
  }
}

function updateMapData(map: MapInstance, data: HotspotMapResponse | null) {
  const pointSource = map.getSource(POINT_SOURCE_ID) as import("maplibre-gl").GeoJSONSource | undefined;
  const roadSource = map.getSource(ROAD_SOURCE_ID) as import("maplibre-gl").GeoJSONSource | undefined;
  pointSource?.setData((data?.points ?? EMPTY_POINTS) as GeoJsonData);
  roadSource?.setData((data?.road_segments ?? EMPTY_ROADS) as GeoJsonData);
}

function collectCoordinates(data: HotspotMapResponse | null) {
  const coordinates: [number, number][] = [];
  for (const feature of data?.points.features ?? []) {
    coordinates.push(feature.geometry.coordinates);
  }
  for (const feature of data?.road_segments.features ?? []) {
    coordinates.push(...feature.geometry.coordinates);
  }
  return coordinates;
}

function fitMapToData(map: MapInstance, data: HotspotMapResponse | null) {
  const coordinates = collectCoordinates(data);
  if (!coordinates.length) return;

  if (coordinates.length === 1) {
    map.easeTo({ center: coordinates[0], zoom: 13, duration: 450 });
    return;
  }

  const lngs = coordinates.map((coordinate) => coordinate[0]);
  const lats = coordinates.map((coordinate) => coordinate[1]);
  map.fitBounds(
    [
      [Math.min(...lngs), Math.min(...lats)],
      [Math.max(...lngs), Math.max(...lats)],
    ],
    { padding: 52, maxZoom: 14, duration: 500 },
  );
}

function pointPopupHtml(properties: Record<string, unknown>) {
  return `
    <div class="space-y-1 text-xs">
      <div class="font-semibold text-white">${escapeHtml(properties.location_name)}</div>
      <div>Violations: <strong>${escapeHtml(properties.violation_count)}</strong></div>
      <div>Confidence: <strong>${formatPercent(properties.avg_confidence)}</strong></div>
      <div>Dominant type: <strong>${escapeHtml(properties.dominant_violation || "mixed")}</strong></div>
    </div>
  `;
}

function roadPopupHtml(properties: Record<string, unknown>) {
  return `
    <div class="space-y-1 text-xs">
      <div class="font-semibold text-white">${escapeHtml(properties.label)}</div>
      <div>${escapeHtml(properties.location_name)}</div>
      <div>Violations: <strong>${escapeHtml(properties.violation_count)}</strong></div>
      <div>Dominant type: <strong>${escapeHtml(properties.dominant_violation || "mixed")}</strong></div>
    </div>
  `;
}

function attachPopupHandlers(maplibregl: MapLibreModule, map: MapInstance) {
  const showPopup = (
    event: import("maplibre-gl").MapMouseEvent & {
      features?: import("maplibre-gl").MapGeoJSONFeature[];
    },
    htmlBuilder: (properties: Record<string, unknown>) => string,
  ) => {
    const feature = event.features?.[0];
    if (!feature) return;
    new maplibregl.Popup({ closeButton: false, maxWidth: "260px" })
      .setLngLat(event.lngLat)
      .setHTML(htmlBuilder(feature.properties ?? {}))
      .addTo(map);
  };

  map.on("click", "violation-points", (event) => showPopup(event, pointPopupHtml));
  map.on("click", "violation-road-segments", (event) => showPopup(event, roadPopupHtml));
  for (const layer of ["violation-points", "violation-road-segments"]) {
    map.on("mouseenter", layer, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layer, () => {
      map.getCanvas().style.cursor = "";
    });
  }
}

export function ViolationHotspotMap({
  data,
  loading,
}: {
  data: HotspotMapResponse | null;
  loading: boolean;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const dataRef = useRef<HotspotMapResponse | null>(data);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState<string | null>(null);

  const hasPoints = Boolean(data?.points.features.length);
  const hasRoads = Boolean(data?.road_segments.features.length);
  useEffect(() => {
    dataRef.current = data;
    if (!mapRef.current || !mapReady) return;
    updateMapData(mapRef.current, data);
    fitMapToData(mapRef.current, data);
  }, [data, mapReady]);

  useEffect(() => {
    let cancelled = false;

    async function initialiseMap() {
      if (!containerRef.current || mapRef.current) return;
      try {
        const maplibregl = await import("maplibre-gl");
        if (cancelled || !containerRef.current) return;
        const initialData = dataRef.current;
        const initialCenter: [number, number] = initialData?.center
          ? [initialData.center.longitude, initialData.center.latitude]
          : FALLBACK_CENTER;

        const map = new maplibregl.Map({
          container: containerRef.current,
          style: getMapStyle(),
          center: initialCenter,
          zoom: initialData?.center ? 11 : 4,
          attributionControl: false,
        });

        mapRef.current = map;
        map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "bottom-right");
        map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-left");
        attachPopupHandlers(maplibregl, map);

        map.on("load", () => {
          addMapLayers(map);
          updateMapData(map, dataRef.current);
          fitMapToData(map, dataRef.current);
          setMapReady(true);
        });
      } catch (error) {
        setMapError(error instanceof Error ? error.message : "Map could not be loaded.");
      }
    }

    initialiseMap();

    return () => {
      cancelled = true;
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" className="border-white/15 text-slate-300">
          <Layers className="mr-1 size-3" /> MapLibre native layers
        </Badge>
        <Badge variant="outline" className="border-white/15 text-slate-300">
          <MapPin className="mr-1 size-3" /> {data?.totals.point_count ?? 0} hotspots
        </Badge>
        <Badge variant="outline" className="border-white/15 text-slate-300">
          <Route className="mr-1 size-3" /> {data?.totals.road_segment_count ?? 0} road segments
        </Badge>
      </div>

      <div className="relative h-[440px] overflow-hidden rounded-lg border border-white/10 bg-slate-950">
        <div ref={containerRef} className="absolute inset-0" />

        {(loading || !mapReady) && (
          <div className="absolute inset-0 z-10 bg-slate-950/70 p-4 backdrop-blur-sm">
            <Skeleton className="h-full w-full rounded-lg" />
          </div>
        )}

        {!loading && mapReady && !hasPoints && (
          <div className="absolute inset-x-4 bottom-4 z-10 rounded-lg border border-white/10 bg-slate-950/90 p-3 text-sm text-slate-300 shadow-xl">
            No geocoded violations yet. Add camera latitude/longitude or scene coordinates to power the map.
          </div>
        )}

        {!loading && mapReady && hasPoints && !hasRoads && (
          <div className="absolute inset-x-4 bottom-4 z-10 rounded-lg border border-amber-300/20 bg-slate-950/90 p-3 text-xs text-amber-100 shadow-xl">
            Point heatmap is active. Add `road_segments` in camera scene config to show heat directly on roads.
          </div>
        )}

        {mapError && (
          <div className="absolute inset-x-4 top-4 z-10 rounded-lg border border-red-300/20 bg-red-950/90 p-3 text-xs text-red-100 shadow-xl">
            {mapError}
          </div>
        )}
      </div>

      <div className="grid gap-2 text-xs text-slate-500 sm:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
          Red/orange zones show dense violation points.
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
          Road lines use weighted counts when segment geometry exists.
        </div>
        <div className="rounded-lg border border-white/10 bg-white/[0.03] p-3">
          Use Mappls/MapmyIndia as the production India basemap via style URL.
        </div>
      </div>
    </div>
  );
}
