import { useEffect, useState } from "react";
import { resolveApiAssetUrl } from "../api/client";
import {
  BuildingFeature,
  DISPLAY_CATEGORY_META,
  TIER_LABELS,
} from "../types/assessment";

interface FeatureDetailPanelProps {
  feature: BuildingFeature | null;
}

const NATIVE_LABELS = [
  "No damage",
  "Minor damage",
  "Major damage",
  "Destroyed",
];

function formatFootprintSource(source: string): string {
  if (source === "predicted") return "Model Predicted Footprint";
  if (source === "reference") return "Reference Footprint (Non-Prediction)";
  return "Synthetic Developer Fixture";
}

export default function FeatureDetailPanel({
  feature,
}: FeatureDetailPanelProps) {
  const [beforeImgFailed, setBeforeImgFailed] = useState(false);
  const [afterImgFailed, setAfterImgFailed] = useState(false);

  const beforeUrl = resolveApiAssetUrl(feature?.properties.crop_urls?.before);
  const afterUrl = resolveApiAssetUrl(feature?.properties.crop_urls?.after);

  useEffect(() => {
    setBeforeImgFailed(false);
    setAfterImgFailed(false);
  }, [beforeUrl, afterUrl, feature?.properties.building_id]);

  if (!feature) {
    return (
      <section className="detail-card" aria-label="Building details">
        <h3>Region Details</h3>
        <p className="muted">
          Click a polygon on the map or a row in the inspection list to view
          native four-class probabilities, display category, and imagery crops.
        </p>
      </section>
    );
  }

  const { properties } = feature;
  const displayMeta = DISPLAY_CATEGORY_META[properties.display_category];

  return (
    <section className="detail-card" aria-label="Building details">
      <div className="detail-header">
        <h3>{properties.building_id}</h3>
        <span className={`tier-badge tier-${properties.suggested_tier}`}>
          {TIER_LABELS[properties.suggested_tier]}
        </span>
      </div>

      <dl className="detail-meta">
        <div>
          <dt>Object Kind</dt>
          <dd>{properties.object_kind}</dd>
        </div>
        <div>
          <dt>Footprint Source</dt>
          <dd>{formatFootprintSource(properties.footprint_source)}</dd>
        </div>
        <div>
          <dt>Map Display Category</dt>
          <dd>
            <strong>{displayMeta.label}</strong> (
            {(
              properties.display_probabilities[
                properties.display_category === "no_apparent_damage"
                  ? 0
                  : properties.display_category === "damaged"
                    ? 1
                    : 2
              ] * 100
            ).toFixed(1)}
            % grouped probability)
          </dd>
        </div>
        <div>
          <dt>Native Winning Class</dt>
          <dd>{properties.native_class}</dd>
        </div>
      </dl>

      <h4>Native Four-Class Probabilities</h4>
      <ul className="prob-list">
        {properties.native_probabilities.map((prob, idx) => (
          <li key={NATIVE_LABELS[idx]} className="prob-row">
            <span>{NATIVE_LABELS[idx]}</span>
            <div className="prob-bar-track">
              <div
                className="prob-bar-fill"
                style={{ width: `${Math.round(prob * 100)}%` }}
              />
            </div>
            <span className="prob-val">{(prob * 100).toFixed(1)}%</span>
          </li>
        ))}
      </ul>

      <h4>Before / After Paired Crops</h4>
      {beforeUrl || afterUrl ? (
        <div className="crop-grid">
          <figure>
            {beforeUrl && !beforeImgFailed ? (
              <img
                src={beforeUrl}
                alt={`Before event crop for ${properties.building_id}`}
                onError={() => setBeforeImgFailed(true)}
              />
            ) : (
              <div className="crop-missing">Before crop unavailable</div>
            )}
            <figcaption>Pre-event</figcaption>
          </figure>
          <figure>
            {afterUrl && !afterImgFailed ? (
              <img
                src={afterUrl}
                alt={`After event crop for ${properties.building_id}`}
                onError={() => setAfterImgFailed(true)}
              />
            ) : (
              <div className="crop-missing">After crop unavailable</div>
            )}
            <figcaption>Post-event</figcaption>
          </figure>
        </div>
      ) : (
        <p className="muted">No paired crop URLs returned for this record.</p>
      )}

      <p className="disclaimer-note">
        Note: Model probability is not a physical damage percentage. Suggested
        tiers assist visual inspection planning only and do not certify
        structural safety.
      </p>
    </section>
  );
}
