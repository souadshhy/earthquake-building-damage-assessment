import { useCallback, useMemo, useState } from "react";
import rawFixture from "./data/result.fixture.json";
import InspectionMap from "./components/InspectionMap";
import FeatureDetailPanel from "./components/FeatureDetailPanel";
import BackendJobPanel, { DataSourceMode } from "./components/BackendJobPanel";
import {
  AssessmentResult,
  DISPLAY_CATEGORY_META,
  DisplayCategory,
  SuggestedTier,
  TIER_LABELS,
  sortFeaturesByTier,
} from "./types/assessment";

const fixtureAssessment = rawFixture as unknown as AssessmentResult;

export default function App() {
  const [mode, setMode] = useState<DataSourceMode>("fixture");
  const [liveAssessment, setLiveAssessment] = useState<AssessmentResult | null>(
    null
  );
  const [categoryFilter, setCategoryFilter] = useState<DisplayCategory | "all">(
    "all"
  );
  const [tierFilter, setTierFilter] = useState<SuggestedTier | "all">("all");
  const [selectedId, setSelectedId] = useState<string | null>(
    fixtureAssessment.buildings.features[0]?.properties.building_id ?? null
  );

  const assessment: AssessmentResult | null =
    mode === "fixture" ? fixtureAssessment : liveAssessment;

  const handleModeChange = useCallback(
    (nextMode: DataSourceMode) => {
      setMode(nextMode);
      setCategoryFilter("all");
      setTierFilter("all");
      const target =
        nextMode === "fixture" ? fixtureAssessment : liveAssessment;
      setSelectedId(
        target?.buildings.features[0]?.properties.building_id ?? null
      );
    },
    [liveAssessment]
  );

  const handleLiveResultLoaded = useCallback((result: AssessmentResult) => {
    setLiveAssessment(result);
    setCategoryFilter("all");
    setTierFilter("all");
    setSelectedId(
      result.buildings.features[0]?.properties.building_id ?? null
    );
  }, []);

  const visibleFeatures = useMemo(() => {
    if (!assessment) return [];
    const filtered = assessment.buildings.features.filter((feature) => {
      const matchesCategory =
        categoryFilter === "all" ||
        feature.properties.display_category === categoryFilter;
      const matchesTier =
        tierFilter === "all" ||
        feature.properties.suggested_tier === tierFilter;
      return matchesCategory && matchesTier;
    });
    return sortFeaturesByTier(filtered);
  }, [assessment, categoryFilter, tierFilter]);

  const visibleCounts = useMemo(() => {
    const counts = {
      total: visibleFeatures.length,
      no_apparent_damage: 0,
      damaged: 0,
      destroyed: 0,
    };
    for (const f of visibleFeatures) {
      counts[f.properties.display_category] += 1;
    }
    return counts;
  }, [visibleFeatures]);

  const selectedFeature = useMemo(
    () =>
      visibleFeatures.find((f) => f.properties.building_id === selectedId) ??
      null,
    [visibleFeatures, selectedId]
  );

  return (
    <div className="app-shell">
      {mode === "fixture" ? (
        <div className="fixture-banner" role="status">
          <strong>SYNTHETIC DEVELOPER FIXTURE MODE:</strong> Displaying{" "}
          <code>{fixtureAssessment.job_id}</code> (
          {fixtureAssessment.model_version}). Not genuine model predictions.
        </div>
      ) : assessment ? (
        <div className="live-banner" role="status">
          <strong>LIVE BACKEND RESULT:</strong> Displaying job{" "}
          <code>{assessment.job_id}</code> ({assessment.model_version}).
        </div>
      ) : (
        <div className="live-banner" role="status">
          <strong>LIVE BACKEND MODE:</strong> No live assessment loaded yet.
        </div>
      )}

      <header className="top-bar">
        <div>
          <h1>Building Damage &amp; Inspection Map</h1>
          <p className="subtitle">
            {assessment ? (
              <>
                Pair: <strong>{assessment.pair_id}</strong> &middot; Model:{" "}
                <code>{assessment.model_version}</code> &middot; Job Total:{" "}
                <strong>{assessment.counts.total}</strong>
              </>
            ) : (
              <>No live assessment loaded — submit a prepared pair or upload</>
            )}
          </p>
        </div>

        <div className="summary-strip" aria-label="Visible region counts">
          <div className="stat-box">
            <span className="stat-num">{visibleCounts.total}</span>
            <span className="stat-label">Visible</span>
          </div>
          <div className="stat-box stat-destroyed">
            <span className="stat-num">{visibleCounts.destroyed}</span>
            <span className="stat-label">Destroyed</span>
          </div>
          <div className="stat-box stat-damaged">
            <span className="stat-num">{visibleCounts.damaged}</span>
            <span className="stat-label">Damaged</span>
          </div>
          <div className="stat-box stat-nodamage">
            <span className="stat-num">{visibleCounts.no_apparent_damage}</span>
            <span className="stat-label">No Apparent</span>
          </div>
        </div>
      </header>

      <BackendJobPanel
        mode={mode}
        onModeChange={handleModeChange}
        activeAssessment={assessment}
        visibleCount={visibleCounts.total}
        onLiveResultLoaded={handleLiveResultLoaded}
      />

      {!assessment ? (
        <section className="detail-card" role="status">
          <h3>No Live Assessment Loaded</h3>
          <p className="muted">
            Select a registered prepared pair or upload a matching before/after
            GeoTIFF pair above to run live inference, or switch back to{" "}
            <strong>Fixture Mode (Demo)</strong> to explore the synthetic
            sample dataset.
          </p>
        </section>
      ) : (
        <>
          <section className="filter-bar" aria-label="Map and list filters">
            <label>
              <span>Display Category:</span>
              <select
                value={categoryFilter}
                onChange={(e) =>
                  setCategoryFilter(e.target.value as DisplayCategory | "all")
                }
              >
                <option value="all">All categories</option>
                <option value="destroyed">Destroyed</option>
                <option value="damaged">Damaged (Minor + Major)</option>
                <option value="no_apparent_damage">No Apparent Damage</option>
              </select>
            </label>

            <label>
              <span>Suggested Inspection Tier:</span>
              <select
                value={tierFilter}
                onChange={(e) =>
                  setTierFilter(e.target.value as SuggestedTier | "all")
                }
              >
                <option value="all">All tiers</option>
                <option value="high">High priority</option>
                <option value="medium">Medium priority</option>
                <option value="lower">Lower priority</option>
              </select>
            </label>

            {(categoryFilter !== "all" || tierFilter !== "all") && (
              <button
                type="button"
                className="reset-btn"
                onClick={() => {
                  setCategoryFilter("all");
                  setTierFilter("all");
                }}
              >
                Reset Filters
              </button>
            )}
          </section>

          <main className="workspace-grid">
            <div className="map-column">
              <InspectionMap
                features={visibleFeatures}
                selectedId={selectedId}
                onSelectFeature={setSelectedId}
              />
            </div>

            <aside className="sidebar-column">
              <section
                className="list-card"
                aria-label="Inspection priority list"
              >
                <div className="list-header">
                  <h2>Inspection Targets ({visibleFeatures.length})</h2>
                  <span className="muted-small">
                    Ordered: High &rarr; Medium &rarr; Lower (within-tier ties)
                  </span>
                </div>

                {visibleFeatures.length === 0 ? (
                  <p className="muted">
                    {assessment.counts.total === 0
                      ? "Assessment completed with 0 detected buildings."
                      : "No regions match the active category/tier filters."}
                  </p>
                ) : (
                  <ul className="target-list">
                    {visibleFeatures.map((feature) => {
                      const props = feature.properties;
                      const isSelected = props.building_id === selectedId;
                      const catMeta =
                        DISPLAY_CATEGORY_META[props.display_category];

                      return (
                        <li key={props.building_id}>
                          <button
                            type="button"
                            className={`target-row ${
                              isSelected ? "target-row-selected" : ""
                            }`}
                            onClick={() => setSelectedId(props.building_id)}
                          >
                            <div className="target-row-top">
                              <strong>{props.building_id}</strong>
                              <span
                                className={`tier-badge tier-${props.suggested_tier}`}
                              >
                                {TIER_LABELS[props.suggested_tier]}
                              </span>
                            </div>
                            <div className="target-row-bottom">
                              <span style={{ color: catMeta.color }}>
                                &#9679; {catMeta.label}
                              </span>
                              <span className="muted-small">
                                {props.object_kind} &middot;{" "}
                                {props.footprint_source}
                              </span>
                            </div>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </section>

              <FeatureDetailPanel feature={selectedFeature} />
            </aside>
          </main>
        </>
      )}
    </div>
  );
}
