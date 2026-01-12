import pandas as pd
import numpy as np
import umap
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

# -------------------------------------------
# 1. Chargement des données
# -------------------------------------------
df = pd.read_csv("dataset/cleaned_ingredients.csv")

# NE PAS convertir toutes les colonnes → on ne touche qu’aux features numériques
numeric_cols = [
    'Calcium_mg','Iron_mg','Magnesium_mg','Phosphorus_mg',
    'Potassium_mg','Zinc_mg','Copper_mcg','Manganese_mg',
    'Selenium_mcg','VitC_mg','Thiamin_mg','Riboflavin_mg',
    'Niacin_mg','VitB6_mg','Folate_mcg','VitB12_mcg',
    'VitA_mcg','VitE_mg','VitD2_mcg','Sodium_mg'
]

# Filtrer uniquement les colonnes présentes
valid_features = [col for col in numeric_cols if col in df.columns]

df[valid_features] = df[valid_features].apply(pd.to_numeric, errors='coerce').fillna(0)

# -------------------------------------------
# 2. Standardisation
# -------------------------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(df[valid_features])

# -------------------------------------------
# 3. UMAP
# -------------------------------------------
print("Exécution de UMAP...")

umap_model = umap.UMAP(
    n_neighbors=30,
    min_dist=0.0,
    n_components=2,
    random_state=42
)

X_umap = umap_model.fit_transform(X_scaled)

# -------------------------------------------
# 4. K-MEANS (4 Clusters)
# -------------------------------------------
n_clusters = 4
print(f"Exécution de K-Means avec {n_clusters} clusters...")

kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
labels = kmeans.fit_predict(X_umap)

# -------------------------------------------
# 5. AJOUT DES NOUVELLES COLONNES
# -------------------------------------------
df["Cluster_micro"] = labels
df["Cluster_micro_X"] = X_umap[:, 0]
df["Cluster_micro_Y"] = X_umap[:, 1]

# -------------------------------------------
# 6. Calcul des Moyennes par Cluster
# -------------------------------------------
print("-" * 30)
print("MOYENNES DES CLUSTERS (micro nutriments) :")
print("-" * 30)

cluster_means = df.groupby("Cluster_micro")[valid_features].mean()
print(cluster_means.T)

# Sauvegarde des moyennes
cluster_means.to_csv("cluster_profiles_micro_means.csv")
print("Profils sauvegardés dans cluster_profiles_micro_means.csv")

# -------------------------------------------
# 7. Sauvegarde du fichier final
# -------------------------------------------
df.to_csv("backend\Analytics\clustered_ingredients.csv", index=False)
print("\nMise à jour DU FICHIER PRINCIPAL ✔")
print("Ajout de : Cluster_micro | Cluster_micro_X | Cluster_micro_Y")
print("FICHIER : backend\Analytics\clustered_ingredients.csv")
