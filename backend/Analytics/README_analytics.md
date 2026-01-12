
--

# Récapitulatif Final : Clustering Ingrédients & Recettes (Équipe 4)

Ce projet transforme un dataset nutritionnel brut en une structure exploitable permettant de regrouper les ingrédients par similarité nutritionnelle, et les recettes par similarité sémantique, facilitant ainsi les substitutions et la recommandation.

## 🎯 Objectifs Globaux

* **Structuration Nutritionnelle** : Transformer les données brutes en clusters d'ingrédients cohérents.
* **Recommandation Sémantique** : Analyser le texte des recettes (ingrédients + étapes) pour regrouper les plats par similarité culinaire et contextuelle.
* **Substitution** : Permettre l'identification d'alternatives via le calcul de distances mathématiques.
* **Insights** : Fournir des profils types et des catégories culinaires aux autres équipes.

---

## 💻 Description des Codes Source

### 1. `clustering_PCA_Macro.py` (Ingrédients)

Ce script traite le profil énergétique des aliments en se basant sur les macronutriments.

* **Logique de données** : Sélectionne 7 variables clés (`Energy_kcal`, `Protein_g`, `Fat_g`, etc.).
* **Réduction de dimension** : Utilise une **PCA** pour condenser ces variables en 3 axes ().
* **Segmentation** : Applique **K-Means** pour diviser les ingrédients en 3 groupes homogènes.

### 2. `clustering_UMAP_Micro.py` (Ingrédients)

Ce script analyse la qualité nutritionnelle profonde via les micronutriments.

* **Logique de données** : Isole 20 colonnes de vitamines et minéraux.
* **Réduction de dimension** : Utilise **UMAP** pour créer une carte 2D () des similarités fines.
* **Segmentation** : Applique **K-Means** pour générer 4 clusters basés sur la densité micronutritionnelle.

### 3. `clustering_UMAP_Total.py` (Ingrédients)

Ce script offre la vue la plus complète (27 features).

* **Logique de données** : Fusionne les micronutriments et les macronutriments.
* **Réduction de dimension** : Utilise **UMAP** (2D) pour projeter la complexité nutritionnelle.
* **Segmentation** : Utilise le **Clustering Agglomératif** (, linkage complete).

### 4. `clustering_Recipes_Semantic.py` (Recettes)

Ce script gère la segmentation sémantique de 50 000 recettes via une approche **AI-Native** sur Snowflake.

* **Vectorisation (LLM)** : Utilisation de **Snowflake Cortex** (modèle `e5-base-v2`) pour transformer le texte concaténé (Nom + Ingrédients + Étapes) en vecteurs de 768 dimensions.
* **Optimisation** : Application d'une **PCA** guidée par la **Méthode du Coude (Elbow Method)** pour réduire le bruit et isoler les dimensions explicatives.
* **Benchmark** : Comparaison rigoureuse de trois algorithmes (DBSCAN, HDBSCAN, K-Means).
* **Segmentation** : Sélection finale de **K-Means ()** pour sa robustesse et son score de silhouette, générant des clusters thématiques clairs (ex: Desserts, Plats mijotés, etc.).

---

## 🛠 Stratégie Méthodologique : 4 Vues Complémentaires

### 1. Clustering MACRO – Profil Énergétique

Focus sur les nutriments fournissant l'énergie structurelle.

* **Algorithmes** : Standardisation → **PCA (3 composantes)** → **K-Means (K=3)**.
* **Typologie** : Équilibré / Glucidique / Gras.

### 2. Clustering MICRO – Qualité Micronutritionnelle

Focus sur la densité en vitamines et minéraux.

* **Algorithmes** : Standardisation → **UMAP (2D)** → **K-Means (K=4)**.
* **Typologie** : Très nutritifs / Profil animal / Faibles en micros / Modérément nutritifs.

### 3. Clustering TOTAL – Vue Nutritionnelle Globale

La vue de référence pour la substitution globale d'ingrédients.

* **Algorithmes** : Standardisation → **UMAP (2D)** → **Clustering Agglomératif**.

### 4. Clustering RECETTES – Approche Sémantique

Focus sur le contexte culinaire et la préparation, complémentaire à l'approche nutritionnelle.

* **Input** : Texte non structuré (Instructions et listes d'ingrédients).
* **Technologie** : Embeddings LLM  PCA  K-Means.
* **Usage** : Permet de recommander une recette "similaire" en goût et en style, même si les micronutriments diffèrent.

---

## 🤖 Interprétation et Labellisation (IA)

L'intelligence artificielle est utilisée à deux niveaux dans ce projet :

1. **Génération d'Embeddings (Snowflake Cortex)** : Transformation du texte brut des recettes en vecteurs mathématiques avant le clustering.
2. **Labellisation Post-hoc (LLM)** : Analyse des moyennes nutritionnelles par cluster (via ChatGPT-4) pour nommer les groupes d'ingrédients de manière intelligible (ex: "Très protéiné, low carb").

---

## 📂 Livrables Finaux

### Données Ingrédients

* **`clustered_ingredients.csv`** : Dataset enrichi (Clusters Macro/Micro/Total, Coordonnées PCA/UMAP).
* **`cluster_macro_means.csv`** & **`cluster_profiles_micro_means.csv`** : Profils moyens.

### Données Recettes

* **`RECIPES_SAMPLE_50K_WITH_CLUSTER`** (Table Snowflake) : Catalogue enrichi avec `Cluster_ID` et coordonnées de projection.

### Scripts

* Pipelines Python complets pour la reproduction des analyses.

---

*Projet réalisé par l'Équipe 4.*