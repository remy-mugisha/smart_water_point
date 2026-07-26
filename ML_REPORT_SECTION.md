# Machine Learning Component — Report Section

This section documents the predictive-risk model for inclusion in the final
project report. It covers methodology, results, limitations, and future
work, and can be adapted directly into the corresponding chapter.

## 1. Methodology

### 1.1 Why Logistic Regression

Logistic Regression was chosen over more complex alternatives (Random
Forest, gradient boosting, neural networks) for three reasons specific to
this project's constraints:

1. **Interpretability.** Water officers and examiners need to understand
   *why* a water point is flagged, not just that it was flagged. Logistic
   Regression's coefficients directly show each feature's direction and
   relative strength of influence — a "black box" model would undermine
   the accountability goal that motivates the whole system.
2. **Performs adequately with small datasets.** District-level water point
   records number in the hundreds, not the millions. Logistic Regression
   has far fewer parameters than tree ensembles or neural networks, so it
   is less prone to overfitting on a small, imbalanced sample.
3. **Calibrated probability output.** The system's whole risk-tiering
   design (Functional / At Risk / Non-Functional) depends on a meaningful
   *probability*, not just a class label. `predict_proba()` gives a
   continuous 0–1 risk score that both the dashboard and the reporting
   module bucket into tiers, which a purely discriminative classifier
   would not provide as naturally.

### 1.2 Feature selection and hypothesized impact

| Feature | Hypothesis |
|---|---|
| `age` (current year − year installed) | Older infrastructure has had more time to accumulate wear; expected to increase failure risk. |
| `population_served` | Higher usage load accelerates mechanical wear; expected to increase risk. |
| `monthly_rainfall` | Rainfall affects groundwater recharge and usage patterns; low rainfall areas may see heavier reliance on a point (and more strain), so lower rainfall is expected to increase risk. |
| `tech_encoded` (technology type) | Different technologies (hand pump, borehole, solar pump, piped kiosk, protected spring) have different mechanical failure modes and expected service lives. |
| `catchment_pressure` | An aggregate industrial-usage-pressure score for the point's water catchment (from `WaterSource`), capturing competing demand on the same water source as a risk factor beyond the point's own attributes. |
| `interaction_age_pop` (age × population served) | Captures compounding wear: an old point serving a large population is disproportionately more strained than either factor alone suggests. |
| `interaction_age_rain` (age × monthly rainfall) | Captures how climate stress compounds with equipment age. |
| `rainy_season_flag` (rainfall > 50mm) | A simple seasonal indicator, since failure patterns may differ between wet and dry season regardless of the exact rainfall figure. |
| `population_density_category` (low/medium/high, by percentile) | A non-linear alternative view of usage load, in case the relationship between raw population and risk isn't strictly linear. |

### 1.3 Data preprocessing

1. **Missing data.** Rows missing more than 30% of their numeric fields
   (age, population served, rainfall) are dropped as too unreliable to
   impute confidently; the remainder are median-imputed. Medians are
   computed once at training time and persisted, so inference on a new,
   incomplete record uses the same reference values rather than silently
   drifting.
2. **Outlier removal.** Age and population-served outliers are removed
   using the 1.5×IQR rule, applied only at training time — inference never
   rejects a real water point for being unusual, it just predicts on it.
3. **Categorical encoding.** Technology type is lowercased/normalized and
   mapped to an integer code learned from the training data's category
   frequencies. A technology type never seen during training falls back to
   the most frequent training category rather than raising an error.
4. **Feature scaling.** All numeric features are standardized
   (zero mean, unit variance) via `StandardScaler`, fitted only on the
   training split and then applied unchanged to the test split and to all
   future inference, preventing test-set leakage.
5. **Class imbalance.** `class_weight="balanced"` reweights the loss
   function inversely proportional to class frequency, since
   non-functional water points are the minority class in most real
   districts and a naive model would otherwise default to always
   predicting "Functional."

### 1.4 Evaluation methodology

The labeled dataset is split 80/20 (train/test) with stratification on the
target, so both splits preserve the same Functional/Non-Functional ratio.
Because a false negative (missing a point that's actually failing) and a
false positive (flagging a working point) have different real-world costs,
the model is evaluated on accuracy, precision, recall, F1-score, and
ROC-AUC together rather than accuracy alone — accuracy alone can look good
on an imbalanced dataset while missing most real failures.

## 2. Results

Results below are from training on a synthetic-but-realistic labeled
sample (`data/raw/sample_training_data.csv`, 220 water points, ~38%
non-functional). **Replace this table with the actual metrics from
`models/training_metrics.json` once trained on the real district dataset**
— the admin "Model Performance" page (`/admin/model-performance`) renders
these live from that file.

| Metric | Value |
|---|---|
| Accuracy | 70.5% |
| Precision | 60.0% |
| Recall | 70.6% |
| F1-Score | 64.9% |
| ROC-AUC | 0.767 |

**Confusion matrix** (44-row test split): 19 true negatives, 8 false
positives, 5 false negatives, 12 true positives. The model catches most
real failures (recall 70.6%) at the cost of some false alarms (precision
60%) — a reasonable trade-off for a maintenance-triage tool, where a false
alarm costs a wasted inspection but a missed failure costs continued
service disruption for the community relying on that point.

**Feature importance** (logistic regression coefficients, positive =
pushes toward Non-Functional): `age` and `population_density_category` had
the strongest positive coefficients, confirming the age/usage-load
hypothesis; `monthly_rainfall` had a negative coefficient, confirming that
wetter conditions are associated with lower failure risk in this sample.
`catchment_pressure` had a near-zero coefficient in this run because the
synthetic training data doesn't encode a real catchment-pressure signal —
this feature is expected to gain importance once trained on real data
where industrial water competition is present.

## 3. Limitations

- **Inference-only in production, training on demand.** The deployed model
  is a static artifact (`models/water_point_model.pkl`) produced by an
  explicit `flask train-model` run (or the admin retrain button); the
  system does not continuously retrain itself as new outcomes arrive.
- **Training data quality.** The pipeline currently trains on a small
  synthetic sample rather than verified historical field records. Real
  WASAC maintenance records, once available, would materially change
  which features matter most and the model's real-world accuracy.
- **Limited feature set.** The model does not yet use maintenance history
  (past repair frequency, parts replaced), pump manufacturer/model,
  installation quality, or soil/groundwater conditions — all plausible
  failure predictors that were out of scope for this dataset.
- **No real-time sensor data.** Predictions are based on periodic
  CSV/Excel uploads, not continuous telemetry, so the model reflects the
  water point's state as of the last upload, not its current condition.
- **Binary ground truth, three-way display.** The model is trained on a
  binary Functional/Non-Functional label (there is no reliable historical
  "at risk" label to train on); the three-way Functional/At Risk/
  Non-Functional status shown in the dashboard is derived by bucketing the
  predicted probability, not a separately-trained "at risk" class.

## 4. Future Work

- **Real historical data.** Replace the synthetic training set with
  verified WASAC maintenance records once available, and re-evaluate all
  metrics.
- **Additional features.** Incorporate maintenance history (prior repair
  count and recency), pump manufacturer/model, and soil/groundwater data
  if/when those become available.
- **Ensemble methods.** Once more data is available, compare Logistic
  Regression against Random Forest or gradient boosting (e.g. XGBoost) —
  these can capture non-linear interactions the current hand-engineered
  interaction terms only approximate, at the cost of interpretability that
  would need to be recovered via feature importance / SHAP.
- **IoT sensor integration.** Real-time flow or usage sensors on
  high-priority water points would let the system move from periodic
  batch predictions to continuous monitoring, catching failures closer to
  when they occur rather than at the next data upload.
- **Scheduled retraining.** A periodic (e.g. quarterly) retraining job
  using accumulated maintenance-task outcomes as new labels, so the model
  improves as more real repair history accumulates.
