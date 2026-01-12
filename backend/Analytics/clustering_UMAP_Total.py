# =========================================================
# clustering_UMAP_AGGLO_SAVE.py
# UMAP + Agglomerative Clustering + Export + Heatmap
# =========================================================

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import AgglomerativeClustering
import matplotlib.pyplot as plt
import seaborn as sns
import umap

# ---------------------------------------------------------
# 1. LOAD
# ---------------------------------------------------------

# df = pd.read_csv("RAW Data/cleaned_ingredients.csv", encoding="utf-8-sig", delimiter=';')

df = pd.read_csv("dataset/cleaned_ingredients.csv")
# ---------------------------------------------------------
# 2. MICRO FEATURES (colonnes numériques uniquement)
# ---------------------------------------------------------
micro_features = [
    'Calcium_mg','Iron_mg','Magnesium_mg','Phosphorus_mg',
    'Potassium_mg','Zinc_mg','Copper_mcg','Manganese_mg',
    'Selenium_mcg','VitC_mg','Thiamin_mg','Riboflavin_mg',
    'Niacin_mg','VitB6_mg','Folate_mcg','VitB12_mcg',
    'VitA_mcg','VitE_mg','VitD2_mcg','Sodium_mg','Energy_kcal',
    'Protein_g','Fat_g','Saturated_fats_g','Carb_g','Sugar_g',
    'Fiber_g'
]

df[micro_features] = df[micro_features].apply(pd.to_numeric, errors='coerce').fillna(0)

# ---------------------------------------------------------
# 3. STANDARDIZATION
# ---------------------------------------------------------
X = df[micro_features]
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ---------------------------------------------------------
# 4. UMAP WITH YOUR PARAMETERS
# ---------------------------------------------------------
reducer = umap.UMAP(
    n_neighbors=15,
    min_dist=0.0,
    n_components=2,
    random_state=42,
    n_epochs=200
)

X_umap = reducer.fit_transform(X_scaled)
print("UMAP → DONE, shape :", X_umap.shape)

df["Cluster_total_X"] = X_umap[:, 0]
df["Cluster_total_Y"] = X_umap[:, 1]

# ---------------------------------------------------------
# 5. AGGLOMERATIVE CLUSTERING (K = 3)
# ---------------------------------------------------------
best_model = AgglomerativeClustering(
    n_clusters=3,
    linkage="complete"
)

labels = best_model.fit_predict(X_umap)
df["Cluster_total"] = labels

print("CLUSTERING → DONE")

# ---------------------------------------------------------
# 6. EXPORT
# ---------------------------------------------------------
df.to_csv("backend\Analytics\clustered_ingredients.csv", index=False, encoding="utf-8-sig")
print("✔ Fichier exporté : backend\Analytics\clustered_ingredients.csv")

# ---------------------------------------------------------
# 7. PLOT 2D CLUSTERS
# ---------------------------------------------------------
plt.figure(figsize=(9,7))
plt.scatter(df["Cluster_total_X"], df["Cluster_total_Y"], c=labels, cmap="tab10")
plt.title("Clusters Agglo (K=3) — UMAP 2D")
plt.xlabel("UMAP 1")
plt.ylabel("UMAP 2")
plt.colorbar()
plt.tight_layout()
plt.show()

# ---------------------------------------------------------
# 8. HEATMAP DES MOYENNES
# ---------------------------------------------------------
# summary_cols = [
#     'Energy_kcal','Protein_g','Fat_g','Saturated_fats_g',
#     'Carb_g','Sugar_g','Fiber_g'
# ]     

summary_cols = [  'Energy_kcal','Protein_g','Fat_g','Saturated_fats_g',
    'Carb_g','Sugar_g','Fiber_g' ,'Calcium_mg','Iron_mg','Magnesium_mg','Phosphorus_mg',
    'Potassium_mg','Zinc_mg','Copper_mcg','Manganese_mg',
    'Selenium_mcg','VitC_mg','Thiamin_mg','Riboflavin_mg',
    'Niacin_mg','VitB6_mg','Folate_mcg','VitB12_mcg',
    'VitA_mcg','VitE_mg','VitD2_mcg','Sodium_mg']

cluster_means = df.groupby("Cluster_total")[summary_cols].mean()

plt.figure(figsize=(10,5))
sns.heatmap(cluster_means, annot=True, cmap="viridis")
plt.title("Moyenne des principaux nutriments par cluster")
plt.xlabel("Features")
plt.ylabel("Cluster_total")
plt.tight_layout()
plt.show()

print("\nFIN DU SCRIPT ✔")
