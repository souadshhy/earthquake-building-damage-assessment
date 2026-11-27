export type NativeDamageClass =
  | "no-damage"
  | "minor-damage"
  | "major-damage"
  | "destroyed";

export type DisplayCategory =
  | "no_apparent_damage"
  | "damaged"
  | "destroyed";

export type SuggestedTier = "high" | "medium" | "lower";

export type FootprintSource =
  | "predicted"
  | "reference"
  | "synthetic_fixture";

export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface PolygonGeometry {
  type: "Polygon";
  coordinates: number[][][];
}

export interface CropUrls {
  before: string;
  after: string;
}

export interface BuildingProperties {
  building_id: string;
  object_kind: "building" | "building_group" | string;
  footprint_source: FootprintSource;
  pixel_geometry?: PolygonGeometry;
  native_probabilities: [number, number, number, number];
  native_class: NativeDamageClass;
  display_probabilities: [number, number, number];
  display_category: DisplayCategory;
  suggested_tier: SuggestedTier;
  crop_box?: [number, number, number, number];
  crop_urls?: CropUrls | null;
}

export interface BuildingFeature {
  type: "Feature";
  geometry: PolygonGeometry;
  properties: BuildingProperties;
}

export interface BuildingFeatureCollection {
  type: "FeatureCollection";
  features: BuildingFeature[];
}

export interface AssessmentCounts {
  total: number;
  no_apparent_damage: number;
  damaged: number;
  destroyed: number;
}

export interface AssessmentResult {
  schema_version: string;
  is_fixture: boolean;
  job_id: string;
  pair_id: string;
  model_version: string;
  status?: JobStatus;
  error?: string | null;
  image_ids: {
    before: string;
    after: string;
  };
  counts: AssessmentCounts;
  buildings: BuildingFeatureCollection;
}

export const DISPLAY_CATEGORY_META: Record<
  DisplayCategory,
  { label: string; color: string; tier: SuggestedTier }
> = {
  destroyed: { label: "Destroyed", color: "#dc2626", tier: "high" },
  damaged: { label: "Damaged (Minor + Major)", color: "#d97706", tier: "medium" },
  no_apparent_damage: {
    label: "No Apparent Damage",
    color: "#16a34a",
    tier: "lower",
  },
};

export const TIER_LABELS: Record<SuggestedTier, string> = {
  high: "High Priority",
  medium: "Medium Priority",
  lower: "Lower Priority",
};

const TIER_RANK: Record<SuggestedTier, number> = {
  high: 0,
  medium: 1,
  lower: 2,
};

export function sortFeaturesByTier(
  features: BuildingFeature[]
): BuildingFeature[] {
  return [...features].sort(
    (a, b) =>
      TIER_RANK[a.properties.suggested_tier] -
      TIER_RANK[b.properties.suggested_tier]
  );
}
