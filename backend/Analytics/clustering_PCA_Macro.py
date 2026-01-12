import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans

# -------------------------------------------
# 1. Chargement du fichier principal
# -------------------------------------------
df = pd.read_csv("dataset/cleaned_ingredients.csv")

# -------------------------------------------
# 2. MACRO FEATURES
# -------------------------------------------
macro_features = [
    'Energy_kcal',
    'Protein_g',
    'Fat_g',
    'Saturated_fats_g',
    'Carb_g',
    'Sugar_g',
    'Fiber_g'
]

# Conversion des colonnes numériques (sans toucher aux autres)
df[macro_features] = df[macro_features].apply(pd.to_numeric, errors='coerce').fillna(0)

X = df[macro_features]

# -------------------------------------------
# 3. STANDARDISATION
# -------------------------------------------
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# -------------------------------------------
# 4. PCA = 3 composants
# -------------------------------------------
pca = PCA(n_components=3)
X_pca = pca.fit_transform(X_scaled)

# Ajout des coordonnées PCA
df["Cluster_macro_X"] = X_pca[:, 0]   # PC1
df["Cluster_macro_Y"] = X_pca[:, 1]   # PC2
df["Cluster_macro_Z"] = X_pca[:, 2]   # PC3

# -------------------------------------------
# 5. KMeans = 3 clusters
# -------------------------------------------
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
labels = kmeans.fit_predict(X_pca)

df["Cluster_macro"] = labels

# -------------------------------------------
# 6. Sauvegarde des résultats
# -------------------------------------------
df.to_csv("clustered_ingredients.csv", index=False)

print("\n✔ Ajout des clusters MACRO effectué !")
print("Colonnes ajoutées : Cluster_macro, Cluster_macro_X/Y/Z")
print("Fichier mis à jour : clustered_ingredients.csv")


# -----------------------------------------------------------
# 7. Tableau des moyennes MACRO par cluster
# -----------------------------------------------------------

macro_means = df.groupby("Cluster_macro")[macro_features].mean()

print("\n===============================")
print(" MOYENNES DES MACRO PAR CLUSTER")
print("===============================\n")
print(macro_means)

# Sauvegarde dans un fichier séparé
macro_means.to_csv("backend\Analytics\clustered_ingredients.csv")
print("\n✔ Moyennes sauvegardées dans 'cluster_macro_means.csv'")
