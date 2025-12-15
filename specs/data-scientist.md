# Skill Specification Template

Use this template to create a new skill specification. Save as specs/{skill-name}.md.

---

## 1. Executive Summary

**Skill Name**: data-scientist  
**Role**: The **Agentic Data Scientist** for Autonomous Statistical Analysis and Optimization—an architect of self-correcting analytical systems that transcends artisanal manual analysis to become the guardian of statistical rigor and experimental validity.  
**Mandate**: Design and orchestrate autonomous agents that execute complex reasoning loops for Deep Statistical Analysis, Advanced A/B Testing, and Feature Selection Optimization, leveraging Mage.ai for orchestration, H2O.ai for distributed AutoML, and PostgreSQL for state management, while eliminating cognitive bias and enforcing scientifically rigorous, reproducible analytical workflows.

---

## 2. Superpowers

List the specialized detection/analysis capabilities this skill provides.

### Superpower 1: Statistical Inference Arbiter
The ability to navigate the dialectical tension between Frequentist and Bayesian inference paradigms. The Agent perceives when p-values and confidence intervals serve regulatory rigor versus when posterior probabilities and credible intervals accelerate learning. It enforces strict stopping rules for Frequentist tests (preventing the "peeking problem" that inflates false positives) while enabling Optional Stopping in Bayesian frameworks where mathematically valid.

### Superpower 2: Data Leakage Sentinel
The capability to detect and prevent the insidious forms of information contamination that invalidate model performance. The Agent identifies Target Leakage (features causally downstream of the target), Train-Test Contamination (global scaling before splits), and Temporal Leakage (future values predicting present). It enforces pipeline boundaries where transformation parameters are fit only on training data.

### Superpower 3: Distribution Drift Monitor
The power to detect when the statistical properties of incoming data deviate from the "Golden Dataset" reference. The Agent calculates Population Stability Index (PSI) and Kullback-Leibler Divergence to identify Covariate Shift and Concept Drift, automatically triggering retraining workflows when drift exceeds defined thresholds before model degradation impacts business outcomes.

### Superpower 4: Assumption Validator
The ability to verify statistical test prerequisites before applying parametric methods. The Agent executes Shapiro-Wilk (normality), Levene's (homogeneity of variance), and Augmented Dickey-Fuller (stationarity) tests, dynamically routing analysis to non-parametric alternatives (Mann-Whitney U, Kruskal-Wallis) when assumptions are violated, preventing invalid statistical conclusions.

### Superpower 5: Uplift Architect
The capability to move beyond average treatment effects to identify heterogeneous treatment responses. The Agent implements H2O Uplift Random Forest with KL/Euclidean divergence splitting criteria, segmenting users into Persuadables (respond only if treated), Sure Things (respond regardless), Lost Causes (never respond), and Sleeping Dogs (respond negatively)—maximizing incremental ROI.

### Superpower 6: Feature Space Optimizer
The power to distill signal from noise through multi-stage feature selection. The Agent orchestrates the Funnel Approach: Filter methods (correlation, variance) for high-throughput reduction, Embedded methods (tree-based importance) for interaction detection, and Wrapper methods (Recursive Feature Elimination) for final optimization—all parallelized via Dynamic Blocks.

### Superpower 7: Self-Healing Pipeline Designer
The ability to construct data pipelines that detect, diagnose, and autonomously correct data quality issues. The Agent defines Expectations (validation rules), captures failures, leverages LLM-powered analysis to generate corrective transformers, and re-executes pipelines—shifting the Data Scientist from fixing bugs to defining acceptable bounds.

---

## 3. Architectural Context (4+1 Views)

Define constraints for each architectural view.

### 3.1 Logical View
- **Hybrid Schema Mandate**: Core entities (`user_id`, `event_timestamp`) in relational columns with enforced keys; experimental features in JSONB for schema-on-read flexibility
- **Global Data Products**: Mage blocks exposing complex transformations as read-only sources for downstream pipelines; "write once, read many" pattern
- **H2O Frame Abstraction**: Operations on distributed frames are lazy expressions; prohibit row-iteration patterns that force client-cluster data transfer
- **Pydantic Contracts**: All feature vectors validated against shared schemas consumed by training and inference pipelines

### 3.2 Process View
- **Event Loop Protection**: CPU-intensive statistical computations (correlation matrices, permutation tests) must use `asyncio.run_in_executor` or standard `def` blocks
- **Dynamic Fan-Out**: Hyperparameter tuning and RFE parallelized via Dynamic Blocks; fan-out generates configs, fan-in aggregates results
- **Stopping Rule Enforcement**: Frequentist tests require pre-defined sample sizes; Bayesian tests allow optional stopping with probability thresholds
- **Assumption-First Routing**: Statistical test selection conditional on normality/variance/stationarity checks; parametric → non-parametric fallback

### 3.3 Development View
- **Monorepo Structure**: `/src/pipeline` for orchestration logic, `/src/service` for inference, `/src/shared/stats_utils` for verified statistical implementations
- **Strict Version Pinning**: H2O Python client synchronized with cluster JAR version; `requirements.txt` locked to prevent serialization drift
- **Block Atomicity**: Mage blocks designed as idempotent, modular units; Data Loaders, Transformers, Exporters with single responsibilities
- **Reusable Statistical Modules**: Shared implementations of hypothesis tests, effect size calculations, and visualization utilities

### 3.4 Physical View
- **Split Memory Formula**: JVM `-Xmx` = 60-70% of container limit; 30-40% reserved for XGBoost native memory + Python overhead
- **H2O Cluster Topology**: StatefulSets with Headless Services for stable network identity; all nodes in same subnet to prevent split-brain
- **Artifact Storage**: Model MOJOs, statistical reports, and feature importance plots persisted to versioned artifact store (S3/GCS)
- **Resource Isolation**: Training containers sized for burst workloads; inference containers sized for steady-state prediction serving

### 3.5 Scenario View
- **Self-Correcting Pipeline**: Drift detection triggers re-analysis → Bayesian evaluation of impact → automatic retraining with optimized feature set
- **Time-Series Walk-Forward**: Training window rolls forward; validation always follows training; no look-ahead bias in temporal data
- **Zero-Downtime Model Swap**: MOJO artifact exported to shared volume; inference service hot-reloads without dropping active requests
- **Experiment Lifecycle**: Hypothesis defined → assumptions validated → test executed → effect size computed → decision logged → stakeholders notified

---

## 4. JTBD Task List

### Epic: DS-LOG-01 (Agentic EDA & Data Integrity)

**T-Shirt Size**: L  
**Objective**: Establish automated protocols for data quality assessment, statistical profiling, and leakage prevention to ensure robust ML inputs.  
**Dependencies**: None  
**Risk**: HIGH - Undetected data leakage invalidates all downstream model performance metrics.

#### Job Story (SPIN Format)
> When new data arrives with unknown quality characteristics and potential leakage vectors [Circumstance],  
> I want to apply my **Data Leakage Sentinel** and **Distribution Drift Monitor** superpowers to automatically profile, validate, and flag issues [New Ability],  
> So that I can trust my model performance estimates reflect true generalization, feeling confident that no information contamination corrupts my experiments [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-LOG-01 | Automated Statistical Profiling | Tool: `ydata-profiling` or `skrub` in Mage Transformer. Output: HTML report + JSON summary. Auto-detect numerical/categorical types | ✅ Report generated for any DataFrame. ✅ Columns >50% missing flagged. ✅ Correlation matrix computed automatically |
| DS-LOG-02 | Data Leakage Detection | Pattern: Validation Sensor checking train/test overlap, high target correlation (>0.99), temporal ordering | ✅ Pipeline fails if `intersection(train_ids, test_ids) != ∅`. ✅ Suspected leakage features flagged. ✅ Scaling parameters fit only on train |
| DS-LOG-03 | Drift Detection Agent | Metric: PSI and KL Divergence against Golden Dataset reference. Threshold: Alert if PSI > 0.25 | ✅ Drift detected within 24h of batch arrival. ✅ Affected features identified. ✅ Retraining workflow triggered if threshold exceeded |

#### Spike
**Spike ID**: SPK-DS-LOG-01  
**Question**: How to distinguish MCAR, MAR, and MNAR missingness patterns to select appropriate imputation strategies?  
**Hypothesis**: Little's MCAR test combined with correlation analysis of missingness indicators can classify patterns  
**Timebox**: 2 Days  
**Outcome**: Missingness classification utility with imputation strategy recommendations

---

### Epic: DS-PROC-01 (Automated Hypothesis Testing Engine)

**T-Shirt Size**: XL  
**Objective**: Automate statistical validation of experiments using rigorous Frequentist and Bayesian methods with proper assumption checking.  
**Dependencies**: DS-LOG-01  
**Risk**: CRITICAL - False positives (Type I error) from improper p-value handling or "peeking" invalidate business decisions.

#### Job Story (SPIN Format)
> When stakeholders need statistically valid conclusions about A/B test variants but lack understanding of test assumptions [Circumstance],  
> I want to use my **Statistical Inference Arbiter** and **Assumption Validator** superpowers to automatically select and execute appropriate tests [New Ability],  
> So that business decisions are grounded in rigorous statistics, and I can provide intuitive "Probability to be Best" metrics rather than confusing p-values [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-PROC-01 | Assumption Validation Pipeline | Tests: Shapiro-Wilk (normality), Levene's (variance homogeneity), ADF (stationarity). Library: `scipy.stats` | ✅ If Shapiro p < 0.05, route to non-parametric. ✅ Time-series data checked for stationarity. ✅ Assumption results logged |
| DS-PROC-02 | Frequentist Test Suite | Tests: T-test, Z-test, ANOVA, Chi-Square, Mann-Whitney U, Kruskal-Wallis. Output: Test statistic, p-value, effect size (Cohen's d) | ✅ Correct test selected based on assumptions. ✅ Effect size computed alongside significance. ✅ Natural language summary generated |
| DS-PROC-03 | Bayesian A/B Analyzer | Library: `pymc` or `scipy`. Pattern: Beta-Binomial conjugate priors for conversion rates. Output: P(B>A), 95% Credible Intervals | ✅ Posterior distributions visualized. ✅ "Probability to be Best" computed. ✅ Optional stopping mathematically valid |

#### Spike
**Spike ID**: SPK-DS-PROC-01  
**Question**: How to implement Sequential Testing with proper alpha-spending functions to allow early stopping in Frequentist framework?  
**Hypothesis**: O'Brien-Fleming or Pocock boundaries can control Type I error while enabling interim analyses  
**Timebox**: 3 Days  
**Outcome**: Sequential testing module with configurable spending functions

---

### Epic: DS-PROC-02 (Uplift Modeling Implementation)

**T-Shirt Size**: L  
**Objective**: Identify heterogeneous treatment effects to optimize targeting and maximize incremental ROI.  
**Dependencies**: DS-LOG-01  
**Risk**: HIGH - Standard A/B testing misses user-level variation, leading to suboptimal resource allocation.

#### Job Story (SPIN Format)
> When marketing needs to identify which users will respond to treatment versus those who convert regardless [Circumstance],  
> I want to use my **Uplift Architect** superpower to train models that estimate individual treatment effects [New Ability],  
> So that campaigns target only Persuadables, avoiding wasted spend on Sure Things and preventing churn from Sleeping Dogs [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-PROC-04 | H2O Uplift DRF Training | Estimator: `H2OUpliftRandomForestEstimator`. Splitting: `uplift_metric="KL"` or `"euclidean"`. Treatment column required | ✅ Model segments users into four quadrants. ✅ Individual uplift scores computed. ✅ Training completes without memory errors |
| DS-PROC-05 | Uplift Evaluation Metrics | Metrics: AUUC (Area Under Uplift Curve), Qini Coefficient. Visualization: Uplift curves, cumulative gains | ✅ AUUC computed and logged. ✅ Qini curve visualized. ✅ Incremental ROI calculated for targeting thresholds |
| DS-PROC-06 | Persuadable Targeting | Output: Scored user list ranked by uplift. Integration: Export to campaign platform with treatment recommendations | ✅ Top N% Persuadables identified. ✅ Sleeping Dogs excluded from treatment. ✅ Expected lift quantified |

#### Spike
**Spike ID**: SPK-DS-PROC-02  
**Question**: How to handle class imbalance in uplift modeling when treatment/control groups have different sizes?  
**Hypothesis**: Stratified sampling or SMOTE variants adapted for uplift context can balance without introducing bias  
**Timebox**: 2 Days  
**Outcome**: Class balancing strategy for uplift models

---

### Epic: DS-DEV-01 (Feature Selection & Optimization)

**T-Shirt Size**: XL  
**Objective**: Implement scalable, automated feature selection using the Funnel Approach to maximize model performance while minimizing complexity.  
**Dependencies**: DS-LOG-01  
**Risk**: HIGH - Overfitting from feature selection on full dataset (Train-Test Contamination in RFE).

#### Job Story (SPIN Format)
> When a dataset has thousands of features with unknown relevance and potential redundancy [Circumstance],  
> I want to use my **Feature Space Optimizer** superpower to systematically reduce dimensionality through multi-stage selection [New Ability],  
> So that the final model uses only the most predictive features, improving interpretability and generalization while reducing training time [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-DEV-01 | Filter Stage Implementation | Methods: Variance threshold, Pearson/Spearman correlation, Chi-Square, ANOVA F-test. Tool: `sklearn.feature_selection` | ✅ Constant columns removed. ✅ High-correlation pairs flagged (>0.95). ✅ Feature count reduced by 50%+ |
| DS-DEV-02 | Embedded Stage (H2O Importance) | Method: Random Forest / XGBoost variable importance. Metric: Reduction in Gini impurity / squared error. Normalized 0-1 | ✅ Importance scores computed for all features. ✅ Variable importance plot generated. ✅ Top N features selected for wrapper stage |
| DS-DEV-03 | Parallel RFE via Dynamic Blocks | Pattern: Fan-out generates feature subsets; parallel H2O training; reducer aggregates metrics. Constraint: RFE inside CV loop only | ✅ Dynamic blocks spawn N parallel jobs. ✅ No train-test contamination. ✅ Optimal feature subset identified |

#### Spike
**Spike ID**: SPK-DS-DEV-01  
**Question**: How to implement Stability Selection to ensure selected features are robust across bootstrap samples?  
**Hypothesis**: Running feature selection on multiple bootstrap samples and keeping only features selected >80% of time reduces false discoveries  
**Timebox**: 2 Days  
**Outcome**: Stability selection wrapper for RFE

---

### Epic: DS-PHY-01 (Resource & Artifact Management)

**T-Shirt Size**: M  
**Objective**: Ensure efficient computational resource allocation and proper artifact versioning for reproducibility.  
**Dependencies**: None  
**Risk**: CRITICAL - OOM kills from improper JVM/native memory split; unreproducible results from unversioned artifacts.

#### Job Story (SPIN Format)
> When H2O training jobs fail with cryptic "Killed" messages and experiments cannot be reproduced months later [Circumstance],  
> I want to configure proper memory allocation and artifact persistence [New Ability],  
> So that training completes reliably and any historical experiment can be exactly reproduced, maintaining scientific integrity [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-PHY-01 | H2O Memory Configuration | Constraint: `-Xmx` = 70% of container limit. Formula: 64GB container → `max_mem_size='44G'`. Reserve 30% for XGBoost native | ✅ XGBoost training completes without OOM. ✅ Memory usage dashboarded. ✅ Configuration documented in deployment manifests |
| DS-PHY-02 | Artifact Versioning | Storage: S3/GCS with versioning enabled. Artifacts: MOJO files, feature importance plots, statistical reports, config YAMLs | ✅ Every training run produces versioned artifacts. ✅ Artifacts linked to git commit SHA. ✅ Historical experiments reproducible |
| DS-PHY-03 | H2O Cluster Stability | Topology: StatefulSet with Headless Service. Network: All nodes in same subnet. Reconnection: try/except with exponential backoff | ✅ Cluster forms on startup. ✅ Node failure triggers clean rejoin. ✅ No split-brain scenarios |

#### Spike
**Spike ID**: SPK-DS-PHY-01  
**Question**: How to dynamically adjust H2O cluster size based on dataset size to optimize cost?  
**Hypothesis**: Dataset row count and column count can predict memory requirements; cluster can auto-scale before training  
**Timebox**: 2 Days  
**Outcome**: Cluster sizing calculator based on data dimensions

---

### Epic: DS-SCN-01 (End-to-End Validation Scenarios)

**T-Shirt Size**: L  
**Objective**: Validate complete analytical workflows under realistic conditions including drift, failures, and model updates.  
**Dependencies**: DS-LOG-01, DS-PROC-01, DS-DEV-01  
**Risk**: MEDIUM - Integration failures between components not caught by unit tests.

#### Job Story (SPIN Format)
> When the production environment experiences data drift, model degradation, or infrastructure failures [Circumstance],  
> I want the system to automatically detect, diagnose, and recover without manual intervention [New Ability],  
> So that analytical workflows remain operational and accurate 24/7, and I can trust the system to self-correct [Emotion].

#### User Stories

| Story ID | Title | Technical Specifications | Acceptance Criteria |
|----------|-------|-------------------------|---------------------|
| DS-SCN-01 | Self-Correcting Pipeline | Trigger: PSI > 0.25 on key features. Reaction: Re-analyze impact → retrain with RFE → deploy new model | ✅ Drift detected automatically. ✅ Retraining triggered without human intervention. ✅ New model deployed within SLA |
| DS-SCN-02 | Time-Series Walk-Forward | Pattern: Rolling training window; validation always follows training; no future data in training | ✅ No look-ahead bias. ✅ Performance stable across time splits. ✅ Backtesting metrics logged |
| DS-SCN-03 | Zero-Downtime Model Swap | Process: MOJO exported → shared volume → inference service hot-reload → health check → traffic shift | ✅ No dropped requests during swap. ✅ Rollback possible if health check fails. ✅ A/B testing between model versions supported |

#### Spike
**Spike ID**: SPK-DS-SCN-01  
**Question**: How to implement automated model performance monitoring that detects degradation before business impact?  
**Hypothesis**: Tracking prediction distribution shift and outcome correlation can detect degradation 1-2 weeks before KPI impact  
**Timebox**: 3 Days  
**Outcome**: Model monitoring dashboard with early warning alerts

---

## 5. Implementation: Scripts

Define the validation/utility scripts this skill requires.

### 5.1 profile_dataset.py
**Purpose**: Generate comprehensive statistical profiles for any input DataFrame  
**Superpower**: Distribution Drift Monitor  
**Detection Logic**:
1. Detect column types (numerical, categorical, datetime)
2. Compute distribution statistics (mean, median, std, skewness, kurtosis)
3. Analyze missingness patterns (MCAR, MAR, MNAR indicators)
4. Generate correlation matrix with multicollinearity flags
5. Output HTML report and JSON summary to artifact store

**Usage**:
```bash
python scripts/profile_dataset.py --input data.parquet --output reports/profile.html --golden-ref golden.parquet
```

### 5.2 detect_leakage.py
**Purpose**: Identify target leakage, train-test contamination, and temporal leakage  
**Superpower**: Data Leakage Sentinel  
**Detection Logic**:
1. Check for ID/timestamp overlap between train and test sets
2. Compute feature-target correlations; flag if any > 0.99
3. Verify scaling parameters computed only on training data
4. For time-series: ensure no future values in training features
5. Generate leakage report with severity scores

**Usage**:
```bash
python scripts/detect_leakage.py --train train.parquet --test test.parquet --target target_column --output leakage_report.json
```

### 5.3 run_hypothesis_test.py
**Purpose**: Execute appropriate statistical test with automatic assumption validation  
**Superpower**: Statistical Inference Arbiter, Assumption Validator  
**Detection Logic**:
1. Check normality (Shapiro-Wilk) and variance homogeneity (Levene's)
2. Select test: parametric (T-test, ANOVA) vs. non-parametric (Mann-Whitney, Kruskal-Wallis)
3. Compute test statistic, p-value, and effect size
4. Generate natural language summary and visualization
5. Log decision path for reproducibility

**Usage**:
```bash
python scripts/run_hypothesis_test.py --control control.csv --treatment treatment.csv --metric conversion_rate --alpha 0.05
```

### 5.4 train_uplift_model.py
**Purpose**: Train H2O Uplift Random Forest and generate evaluation metrics  
**Superpower**: Uplift Architect  
**Detection Logic**:
1. Validate treatment column and response variable
2. Configure Uplift DRF with KL divergence splitting
3. Train model with cross-validation
4. Compute AUUC and Qini coefficient
5. Generate uplift curve visualization and user scores

**Usage**:
```bash
python scripts/train_uplift_model.py --data experiment.parquet --treatment treatment_flag --response converted --output models/uplift_v1.mojo
```

### 5.5 run_feature_selection.py
**Purpose**: Execute multi-stage Funnel Approach feature selection  
**Superpower**: Feature Space Optimizer  
**Detection Logic**:
1. Stage 1 (Filter): Remove constant columns, high-correlation pairs
2. Stage 2 (Embedded): Compute H2O Random Forest importance scores
3. Stage 3 (Wrapper): Parallel RFE via Dynamic Blocks (inside CV only)
4. Aggregate results and select optimal feature subset
5. Generate importance plot and selection report

**Usage**:
```bash
python scripts/run_feature_selection.py --data features.parquet --target target --method funnel --max-features 50
```

---

## 6. Technical Reference

Deep technical context for the superpowers.

### 6.1 Frequentist vs. Bayesian Inference: The Dialectical Framework
The choice between Frequentist and Bayesian methods is not merely technical—it reflects fundamentally different philosophies of probability. Frequentist probability is the long-run frequency of events; parameters are fixed but unknown constants. Bayesian probability is a degree of belief updated by evidence; parameters are random variables with distributions.

Frequentist methods (p-values, confidence intervals) excel in regulatory environments requiring strict error control. However, they suffer from the "peeking problem": checking results before reaching the pre-determined sample size inflates the false positive rate. The stopping rule must be fixed in advance.

Bayesian methods (posterior probabilities, credible intervals) allow Optional Stopping—checking results at any time without inflating error rates. They provide intuitive "Probability to be Best" metrics that stakeholders understand more readily than p-values. However, they require specifying priors, which can be controversial.

The recommended Hybrid Strategy: use Frequentist methods for high-stakes "Go/No-Go" decisions where error control is paramount; use Bayesian methods for continuous optimization where speed and learning are prioritized.

### 6.2 Data Leakage: The Silent Model Killer
Data leakage is the most insidious failure mode in machine learning—models appear excellent in validation but fail catastrophically in production. Three primary forms exist:

**Target Leakage**: Features that are causal consequences of the target variable. Example: including "Discharge Date" when predicting "Length of Stay." The feature perfectly predicts the target but is unavailable at prediction time.

**Train-Test Contamination**: Information from the test set influencing training. Common culprit: applying global normalization (computing mean/std on full dataset) before splitting. The test set's statistics leak into the training normalization.

**Temporal Leakage**: In time-series, using future values to predict current values. Example: including "next_month_revenue" as a feature for "this_month_churn." The solution is strict Walk-Forward Validation where the training window always precedes the validation window.

### 6.3 Uplift Modeling: Beyond Average Treatment Effects
Standard A/B testing answers: "Does the treatment work on average?" Uplift modeling answers: "For whom does the treatment work?" This distinction is crucial for personalization.

The Conditional Average Treatment Effect (CATE) segments users into four quadrants: **Persuadables** respond only when treated (target these), **Sure Things** respond regardless (don't waste budget), **Lost Causes** never respond (don't bother), **Sleeping Dogs** respond negatively when treated (avoid at all costs—they may churn due to annoyance).

H2O's Uplift Random Forest uses divergence-based splitting criteria (KL Divergence, Squared Euclidean Distance) rather than Gini impurity. The goal is maximizing the difference in response distributions between treatment and control, not maximizing prediction accuracy. Evaluation uses AUUC (Area Under Uplift Curve) and Qini Curves, not standard AUC.

### 6.4 Recursive Feature Elimination: The Overfitting Trap
RFE is powerful but dangerous. The algorithm iteratively trains models, removes the least important features, and repeats until reaching the desired count. The trap: performing RFE on the full dataset before train-test split means the test set influences feature selection, causing overfitting.

The correct pattern: RFE must occur **inside** the cross-validation loop or strictly on the training set. Each CV fold performs its own RFE; only features consistently selected across folds are retained. This "Stability Selection" approach dramatically reduces false discoveries.

Parallelization via Dynamic Blocks transforms RFE from hours to minutes. The fan-out block generates feature subsets; N parallel training jobs execute simultaneously; the reducer aggregates performance metrics and identifies the optimal subset.

### 6.5 H2O Memory Architecture: JVM vs. Native
H2O runs on the JVM, but many algorithms (particularly XGBoost) use native C++ code with off-heap memory allocation. This creates a dangerous interaction in containerized environments.

When a container has 64GB limit and the JVM is configured with `-Xmx60g`, Java reserves nearly all memory. When XGBoost starts, it requests native memory from the OS. The allocation fails, and the Linux OOM Killer terminates the process—often with no useful error message.

The 70/30 split formula provides safety: for 64GB containers, set `-Xmx44g`, leaving 20GB for native allocation, Python interpreter, and OS buffers. XGBoost's memory requirements scale with tree depth, number of trees, and dataset size—empirical tuning may be required for specific workloads.

---

## 7. Extracted Components Summary

This section is auto-populated during workflow execution.

```yaml
skill_name: data-scientist
description: Agentic Data Scientist for Autonomous Statistical Analysis and Optimization
superpowers:
  - statistical-inference-arbiter
  - data-leakage-sentinel
  - distribution-drift-monitor
  - assumption-validator
  - uplift-architect
  - feature-space-optimizer
  - self-healing-pipeline-designer
triggers:
  - "statistical analysis"
  - "hypothesis testing"
  - "a/b testing"
  - "bayesian inference"
  - "feature selection"
  - "uplift modeling"
  - "data leakage"
  - "drift detection"
  - "eda automation"
  - "rfe optimization"
  - "experiment design"
epics:
  - id: DS-LOG-01
    name: Agentic EDA & Data Integrity
    size: L
    stories: 3
    spike: SPK-DS-LOG-01
  - id: DS-PROC-01
    name: Automated Hypothesis Testing Engine
    size: XL
    stories: 3
    spike: SPK-DS-PROC-01
  - id: DS-PROC-02
    name: Uplift Modeling Implementation
    size: L
    stories: 3
    spike: SPK-DS-PROC-02
  - id: DS-DEV-01
    name: Feature Selection & Optimization
    size: XL
    stories: 3
    spike: SPK-DS-DEV-01
  - id: DS-PHY-01
    name: Resource & Artifact Management
    size: M
    stories: 3
    spike: SPK-DS-PHY-01
  - id: DS-SCN-01
    name: End-to-End Validation Scenarios
    size: L
    stories: 3
    spike: SPK-DS-SCN-01
scripts:
  - name: profile_dataset.py
    superpower: distribution-drift-monitor
  - name: detect_leakage.py
    superpower: data-leakage-sentinel
  - name: run_hypothesis_test.py
    superpower: statistical-inference-arbiter
  - name: train_uplift_model.py
    superpower: uplift-architect
  - name: run_feature_selection.py
    superpower: feature-space-optimizer
checklists:
  - logical_view_data_scientist.md
  - process_view_data_scientist.md
  - development_view_data_scientist.md
  - physical_view_data_scientist.md
  - scenario_view_data_scientist.md
references:
  - frequentist_bayesian_inference.md
  - data_leakage_patterns.md
  - uplift_modeling_cate.md
  - recursive_feature_elimination.md
  - h2o_memory_architecture.md
```
