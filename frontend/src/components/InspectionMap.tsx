import { useEffect } from "react";
import { MapContainer, TileLayer, GeoJSON, useMap } from "react-leaflet";
import L from "leaflet";
import {
  BuildingFeature,
  DISPLAY_CATEGORY_META,
  DisplayCategory,
} from "../types/assessment";

interface InspectionMapProps {
  features: BuildingFeature[];
  selectedId: string | null;
  onSelectFeature: (buildingId: string) => void;
}

function FitBoundsToFeatures({ features }: { features: BuildingFeature[] }) {
  const map = useMap();

  useEffect(() => {
    if (features.length === 0) return;

    const latLngs: [number, number][] = [];
    for (const feature of features) {
      for (const ring of feature.geometry.coordinates) {
        for (const [lng, lat] of ring) {
          latLngs.push([lat, lng]);
        }
      }
    }

    if (latLngs.length > 0) {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [48, 48], maxZoom: 18 });
    }
  }, [features, map]);

  return null;
}

export default function InspectionMap({
  features,
  selectedId,
  onSelectFeature,
}: InspectionMapProps) {
  const featureCollection = {
    type: "FeatureCollection" as const,
    features,
  };

  const layerKey = `${features.map((f) => f.properties.building_id).join(",")}|${
    selectedId ?? "none"
  }`;

  return (
    <div className="map-wrapper">
      <MapContainer
        center={[18.55, -72.34]}
        zoom={16}
        className="leaflet-container-box"
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <FitBoundsToFeatures features={features} />

        {features.length > 0 && (
          <GeoJSON
            key={layerKey}
            data={featureCollection}
            style={(feature) => {
              const props = feature?.properties as
                | BuildingFeature["properties"]
                | undefined;
              const category: DisplayCategory =
                props?.display_category ?? "no_apparent_damage";
              const isSelected = props?.building_id === selectedId;
              const isReference = props?.footprint_source === "reference";
              const color = DISPLAY_CATEGORY_META[category].color;

              return {
                color: isSelected ? "#0f172a" : color,
                weight: isSelected ? 4 : 2,
                dashArray: isReference ? "5, 5" : undefined,
                fillColor: color,
                fillOpacity: isSelected ? 0.65 : 0.4,
              };
            }}
            onEachFeature={(feature, layer) => {
              const props = feature.properties as BuildingFeature["properties"];
              layer.on({
                click: () => onSelectFeature(props.building_id),
              });
              layer.bindTooltip(
                `${props.building_id} — ${
                  DISPLAY_CATEGORY_META[props.display_category].label
                }`
              );
            }}
          />
        )}
      </MapContainer>

      <div className="map-legend" aria-label="Damage category legend">
        <strong>Map Legend (3-Category Overview)</strong>
        <div className="legend-items">
          {(Object.keys(DISPLAY_CATEGORY_META) as DisplayCategory[]).map(
            (cat) => (
              <span key={cat} className="legend-item">
                <span
                  className="legend-swatch"
                  style={{ backgroundColor: DISPLAY_CATEGORY_META[cat].color }}
                />
                {DISPLAY_CATEGORY_META[cat].label}
              </span>
            )
          )}
        </div>
      </div>
    </div>
  );
}
