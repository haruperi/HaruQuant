Excellent. We now move from a rule-based baseline workflow into **pattern discovery**.

## Module 1 — Building a Workflow for AI Trading

### Lesson 2 — Unsupervised Learning

This lesson is about using **unsupervised learning** to discover structure in financial data **without predefined labels**.

In trading, this is useful because markets often do not hand us clean labels like:

* “this stock is good”
* “this regime is bullish”
* “this factor will outperform”

Instead, we often need to **explore**, **group**, and **compress** data first.

That is where:

* **summary statistics**
* **K-Means clustering**
* **PCA**
* **risk factor analysis**
  come in.

---

# 1. What is unsupervised learning in trading?

Unsupervised learning means the model is given data **without target labels** and tries to find hidden patterns.

In finance, this is commonly used to:

* cluster similar assets
* detect market regimes
* reduce dimensionality
* uncover latent risk factors
* explore cross-sectional structure
* improve feature understanding before supervised learning

So instead of predicting directly, the model first helps answer:

* Which assets behave similarly?
* What dimensions explain most variation?
* Are there hidden groups of stocks?
* What risk structure drives returns?
* Can we adapt strategies based on cluster membership?

---

# 2. Why this lesson matters

Financial markets are noisy.
If you directly jump to prediction, you often miss the deeper structure.

Unsupervised learning helps you:

* understand the data before modeling
* reduce noise
* simplify large datasets
* discover hidden groupings
* identify factors behind outperformance
* create smarter downstream strategies

In practice, unsupervised learning often becomes the **research layer** before alpha modeling.

---

# 3. Core topics in this lesson

This lesson covers five key skills:

## A. Explore investment data

Before applying clustering or PCA, you should inspect the dataset.

Typical questions:

* What are the average returns?
* Which assets are more volatile?
* Are there missing values?
* How correlated are the features?
* Are there strong outliers?

Common statistics:

* mean return
* volatility
* skewness
* kurtosis
* min/max
* pairwise correlation

This gives the first map of the data.

---

## B. Summarize key statistics

Summary statistics help compare securities or features.

Examples:

* average daily return
* annualized volatility
* Sharpe-like ratio
* rolling drawdown
* volume stability
* sector-level means

These summaries themselves can become clustering inputs.

For example, instead of clustering on raw daily prices, you may cluster on:

* return
* volatility
* momentum
* beta
* turnover
* drawdown

That often gives cleaner groups.

---

## C. K-Means clustering

K-Means groups observations into **K clusters** based on similarity.

In trading, it can be used to cluster:

* stocks with similar behavior
* market days with similar characteristics
* time periods with similar regimes
* features into interpretable groups

Example use cases:

* group stocks into behavioral buckets
* detect low-vol / high-vol regimes
* separate trend vs mean-reversion environments
* create cluster-specific trading rules

Important point:
K-Means does not know finance. It only groups based on geometry in the feature space.

So feature design matters a lot.

---

## D. PCA (Principal Component Analysis)

PCA reduces many features into a smaller set of components that explain most variance.

In finance, PCA is useful for:

* dimensionality reduction
* noise filtering
* visualizing data
* factor discovery
* identifying common market drivers

Example:
If you have 30 correlated indicators, PCA may reveal that most variation is captured by:

* market direction
* volatility/risk-on-risk-off
* momentum/relative strength

This helps simplify the model.

---

## E. Identify risk factors and insights on outperformance

Once clustering and PCA are applied, the goal is not just visualization.

The real value is in asking:

* Which clusters outperform?
* Which factors explain return differences?
* Are some groups more volatile?
* Are some clusters more defensive?
* Do some clusters respond better to certain strategies?

This is where unsupervised learning becomes useful for portfolio construction and strategy adaptation.

---

# 4. Workflow of unsupervised learning in trading

Here is the practical workflow:

## Step 1 — Gather investment universe

Examples:

* stock returns
* factor values
* fundamentals
* technical features
* macro features

## Step 2 — Clean and standardize data

This is critical because clustering is sensitive to scale.

Typical preprocessing:

* handle missing values
* winsorize outliers
* standardize features
* align dates/assets

## Step 3 — Explore summary stats

Look at:

* means
* volatilities
* correlations
* distributions

## Step 4 — Apply PCA

Use PCA to:

* reduce dimensions
* inspect explained variance
* visualize assets/regimes

## Step 5 — Apply clustering

Use K-Means or another clustering method on:

* original standardized features
* PCA-transformed features

## Step 6 — Interpret clusters

Study each cluster:

* average return
* average risk
* sector composition
* factor exposure
* regime meaning

## Step 7 — Use findings in trading

Examples:

* adapt strategy per cluster
* select outperforming groups
* avoid high-risk clusters
* use PCA factors as model inputs

---

# 5. Key trading intuition

Unsupervised learning does not tell you directly:

> “Buy asset X tomorrow.”

Instead, it tells you things like:

* “These stocks belong to a similar behavior group.”
* “These time periods are structurally alike.”
* “These two features mostly measure the same thing.”
* “Most variation comes from a few underlying factors.”
* “This cluster tends to have better risk-adjusted performance.”

That makes it a **decision-support layer**.

---

# 6. K-Means intuition in finance

Suppose you calculate these features for each stock:

* annual return
* annual volatility
* momentum
* beta
* max drawdown

K-Means may separate them into clusters like:

* Cluster 0: low-vol defensive names
* Cluster 1: high-beta momentum names
* Cluster 2: weak performers with high drawdowns

You can then ask:

* Which cluster has better future returns?
* Which cluster fits my risk budget?
* Should I apply different strategies to different groups?

This turns unsupervised learning into practical trading logic.

---

# 7. PCA intuition in finance

Suppose you have many correlated variables:

* returns across many assets
* multiple technical indicators
* many macro features

PCA finds new synthetic variables called **principal components**.

These components:

* are linear combinations of the originals
* are orthogonal to each other
* explain variance in descending order

In markets, the first few PCs often reflect:

* broad market movement
* interest rate / macro sensitivity
* volatility regime
* sector rotation

This helps you understand what truly drives the data.

---

# 8. Practical example in Python

Below is a clean example that:

* loads multi-asset price data
* computes return-based summary features
* standardizes them
* runs PCA
* runs K-Means clustering
* evaluates cluster characteristics

## File: `lesson_2_unsupervised_learning.py`

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans


def load_price_data(filepath: str) -> pd.DataFrame:
    """
    Load wide-format price data.
    Expected format:
        Date, AAPL, MSFT, GOOG, ...
    """
    df = pd.read_csv(filepath)
    df.columns = [c.strip() for c in df.columns]
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").set_index("Date")
    df = df.ffill().dropna(how="all")
    return df


def compute_returns(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute daily percentage returns.
    """
    returns = price_df.pct_change().dropna(how="all")
    return returns


def summarize_assets(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Build per-asset summary features for clustering.
    """
    summary = pd.DataFrame(index=returns.columns)

    summary["mean_return"] = returns.mean() * 252
    summary["volatility"] = returns.std() * np.sqrt(252)
    summary["skew"] = returns.skew()
    summary["kurtosis"] = returns.kurtosis()
    summary["max_drawdown"] = returns.apply(compute_max_drawdown)
    summary["sharpe_like"] = summary["mean_return"] / summary["volatility"].replace(0, np.nan)

    return summary.dropna()


def compute_max_drawdown(asset_returns: pd.Series) -> float:
    """
    Compute max drawdown from returns series.
    """
    equity = (1 + asset_returns.fillna(0)).cumprod()
    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1
    return drawdown.min()


def standardize_features(feature_df: pd.DataFrame):
    """
    Standardize features before PCA / K-Means.
    """
    scaler = StandardScaler()
    scaled = scaler.fit_transform(feature_df)
    scaled_df = pd.DataFrame(scaled, index=feature_df.index, columns=feature_df.columns)
    return scaled_df, scaler


def apply_pca(feature_df: pd.DataFrame, n_components: int = 2):
    """
    Apply PCA and return transformed coordinates plus PCA model.
    """
    pca = PCA(n_components=n_components)
    transformed = pca.fit_transform(feature_df)

    pca_df = pd.DataFrame(
        transformed,
        index=feature_df.index,
        columns=[f"PC{i+1}" for i in range(n_components)]
    )
    return pca_df, pca


def apply_kmeans(feature_df: pd.DataFrame, n_clusters: int = 3, random_state: int = 42):
    """
    Cluster assets using K-Means.
    """
    model = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
    labels = model.fit_predict(feature_df)
    return labels, model


def analyze_clusters(summary_df: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """
    Add cluster labels and compute cluster-level summaries.
    """
    clustered = summary_df.copy()
    clustered["cluster"] = labels

    cluster_summary = clustered.groupby("cluster").agg(
        count=("mean_return", "count"),
        avg_return=("mean_return", "mean"),
        avg_volatility=("volatility", "mean"),
        avg_drawdown=("max_drawdown", "mean"),
        avg_sharpe_like=("sharpe_like", "mean"),
    )

    return clustered, cluster_summary


def plot_pca_clusters(pca_df: pd.DataFrame, labels: np.ndarray) -> None:
    """
    Scatter plot of PCA-reduced points colored by cluster.
    """
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(pca_df["PC1"], pca_df["PC2"], c=labels)
    for asset, row in pca_df.iterrows():
        plt.annotate(asset, (row["PC1"], row["PC2"]), fontsize=8)
    plt.title("PCA Projection with K-Means Clusters")
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.grid(True)
    plt.tight_layout()
    plt.show()


def print_explained_variance(pca: PCA) -> None:
    """
    Print explained variance ratio of PCA components.
    """
    print("\nExplained Variance Ratio:")
    for i, ratio in enumerate(pca.explained_variance_ratio_, start=1):
        print(f"PC{i}: {ratio:.4f}")


def main():
    filepath = "multi_asset_prices.csv"

    price_df = load_price_data(filepath)
    returns = compute_returns(price_df)

    summary_df = summarize_assets(returns)
    scaled_df, scaler = standardize_features(summary_df)

    pca_df, pca = apply_pca(scaled_df, n_components=2)
    labels, kmeans_model = apply_kmeans(scaled_df, n_clusters=3)

    clustered_assets, cluster_summary = analyze_clusters(summary_df, labels)

    print("\nAsset Summary:")
    print(summary_df.round(4))

    print("\nClustered Assets:")
    print(clustered_assets.sort_values("cluster"))

    print("\nCluster Summary:")
    print(cluster_summary.round(4))

    print_explained_variance(pca)
    plot_pca_clusters(pca_df, labels)


if __name__ == "__main__":
    main()
```

---

# 9. What this code teaches

This example follows the unsupervised trading workflow:

## Data preparation

* load price panel
* compute returns

## Statistical exploration

* average return
* volatility
* skewness
* kurtosis
* drawdown
* Sharpe-like measure

## Standardization

This is essential because clustering is scale-sensitive.

## PCA

* reduce many features to 2 dimensions
* inspect explained variance
* visualize relative structure

## K-Means

* group assets into clusters
* compare cluster-level behavior

## Interpretation

* identify clusters with stronger returns
* inspect risk profile differences
* turn discovered groups into trading insight

---

# 10. How to interpret the results

Suppose the cluster summary shows:

* Cluster 0: low return, low volatility, small drawdowns
* Cluster 1: high return, high volatility, strong momentum
* Cluster 2: weak return, high drawdown, poor Sharpe

Then possible trading decisions are:

* overweight Cluster 1 if risk budget allows
* use tighter controls on Cluster 1 due to volatility
* avoid Cluster 2
* use defensive allocation in Cluster 0 during uncertain regimes

This is where unsupervised learning becomes practical.

---

# 11. Choosing the right number of clusters

K-Means requires you to choose **K**.

Common methods:

* elbow method
* silhouette score
* domain interpretation

In finance, the “best” K is often not purely mathematical.
It must also produce clusters that are:

* stable
* interpretable
* useful for decision-making

A cluster model that is mathematically neat but economically meaningless is not helpful.

---

# 12. PCA caveats in finance

PCA is useful, but remember:

* it captures variance, not necessarily alpha
* high variance does not always mean predictive importance
* principal components may shift over time
* interpretation is sometimes ambiguous

Still, PCA is powerful for:

* de-noising
* compression
* risk structure analysis
* factor discovery

---

# 13. Common mistakes in unsupervised finance workflows

## A. Using unscaled features

If one variable has much larger magnitude, it dominates clustering.

## B. Clustering raw prices

Raw price levels are usually not appropriate.
Use returns or meaningful derived features.

## C. Ignoring regime changes

Clusters found over one period may not remain stable later.

## D. Over-interpreting clusters

A cluster is not a law of the market. It is just a pattern in the data.

## E. Treating PCA components as fixed truth

PCA loadings can change across time windows.

---

# 14. How this connects to outperformance

The lesson mentions identifying factors that enhance insight on outperformance.

This means:

1. Build features for each asset
2. Cluster assets or reduce dimensions with PCA
3. Compare forward returns or performance across groups
4. Study what characteristics are associated with better outcomes

For example:

* high momentum + moderate volatility cluster may outperform
* certain PCA factor exposures may align with stronger returns
* low-quality drawdown-heavy clusters may underperform

This helps transform raw data into **investable structure**.

---

# 15. How this connects to later machine learning

Unsupervised learning is often a precursor to later stages:

## Before supervised learning

Use PCA to reduce noisy features.

## Before reinforcement learning

Use clustering to define market regimes or states.

## Before portfolio optimization

Use PCA to identify common risk drivers.

## Before strategy design

Use clustering to create asset buckets with different trading logic.

So this lesson is not isolated.
It becomes part of the larger AI trading pipeline.

---

# 16. HaruQuant interpretation

For your HaruQuant system, this lesson maps well into a dedicated research subsystem:

* **data layer** → asset panel data, returns, factors
* **stats layer** → summary feature extraction
* **unsupervised layer** → PCA, clustering, regime grouping
* **evaluation layer** → cluster performance comparison
* **strategy layer** → adaptive rules by cluster/regime

A good HaruQuant module structure for this lesson would be:

* `data_loader.py`
* `feature_builder.py`
* `stats_summary.py`
* `pca_analysis.py`
* `clustering.py`
* `cluster_evaluation.py`
* `main.py`

---

# 17. Practical uses in trading

Here are strong real-world uses of unsupervised learning in finance:

## Asset clustering

Group similar stocks/currencies/ETFs and diversify across groups.

## Regime detection

Cluster market periods into trending, choppy, volatile, calm.

## Feature compression

Use PCA to reduce many correlated indicators into fewer dimensions.

## Risk factor extraction

Find common hidden factors affecting returns.

## Strategy adaptation

Apply different strategies depending on cluster or PCA regime.

---

# 18. Mini exercise

A good exercise after this lesson:

1. compute features for 20 assets
2. standardize the data
3. run PCA
4. plot PC1 vs PC2
5. run K-Means with K = 3, 4, 5
6. compare cluster summaries
7. test whether one cluster has stronger next-period returns

That last step is important because it connects exploration to investable action.

---

# 19. Lesson summary

## Main idea

Unsupervised learning helps discover hidden structure in financial data without needing labeled outcomes.

## Key skills from this lesson

* explore investment datasets
* summarize key asset statistics
* cluster assets using K-Means
* reduce dimensionality using PCA
* identify latent risk factors
* use clusters/factors to improve trading insight

## Why it matters

It helps you understand the market before trying to predict it.

---

# 20. What you should understand before moving on

By the end of this lesson, you should be comfortable with:

* why unsupervised learning matters in trading
* how to turn price data into clustering features
* why standardization is necessary
* how PCA helps reduce noise and reveal structure
* how K-Means groups similar assets or market states
* how cluster analysis can support outperformance research

---

