import pandas as pd
import kagglehub
import gdown
import os
import shutil


def load_from_drive(file_id, output_filename):
    output_folder = './data_cache'
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, output_filename)
    
    url = f'https://drive.google.com/uc?id={file_id}'
    
    print(f"Downloading {output_filename} to {output_path}...")
    
    if not os.path.exists(output_path):
        gdown.download(url, output_path, quiet=False, fuzzy=True)
    else:
        print("File already present, skipping.")

    # (Optional) Return the dataframe to use it immediately
    return os.path.abspath(output_path)


def load_from_kaggle(dataset: str, output_filename: str):
    """
    Télécharge un dataset, prend le premier fichier trouvé, 
    le renomme selon 'output_filename' et le place dans data_cache.
    """
    
    # 1. Dossier temporaire
    temp_cache_dir = './temp_kaggle_cache'
    os.environ['KAGGLEHUB_CACHE'] = temp_cache_dir

    print(f"Downloading {dataset}...")
    # Cela retourne le chemin vers un DOSSIER
    download_path = kagglehub.dataset_download(dataset)

    # 2. Dossier final
    final_output_dir = './data_cache'
    os.makedirs(final_output_dir, exist_ok=True)
    
    # Chemin complet de destination (ex: ./data_cache/mes_recettes.csv)
    final_file_path = os.path.join(final_output_dir, output_filename)

    # 3. L'astuce pour éviter la boucle : on prend le 1er fichier de la liste
    # Attention : Cela suppose qu'il n'y a qu'un seul fichier important dans le dataset
    files_found = os.listdir(download_path)
    
    if len(files_found) > 0:
        source_file = files_found[0] # On prend le premier fichier trouvé (ex: recipes.csv)
        source_path = os.path.join(download_path, source_file)
        
        # On déplace et on RENOMME en même temps
        if os.path.exists(final_file_path):
            os.remove(final_file_path) # Nettoyage si existe déjà
            
        shutil.move(source_path, final_file_path)
        print(f" -> Success! File saved as: {final_file_path}")
    else:
        print("Error: No file found in the downloaded dataset.")
        final_file_path = None

    # 4. Nettoyage
    print("Cleaning up...")
    shutil.rmtree(temp_cache_dir)

    return os.path.abspath(final_file_path) if final_file_path else None

    return os.path.abspath()

if __name__ == "__main__":
    raw_recipes = '1fxvf7ghbgH0xkvHkPFM_K8_JbeL9QX3L'
    raw_interactions = '10zdNLf2oKiMY30ZacdwdF1AEpkrbyoUN'
    cleaned_ingredients = '1HjT5RiZnxlg2PkcMLlqzxBjeeRGITYvx'

    load_from_drive(raw_recipes)
    load_from_drive(raw_interactions)
    load_from_drive(cleaned_ingredients)

    recipes_images = 'behnamrahdari/foodcom-enhanced-recipes-with-images'
    recipes_w_search_terms = 'shuyangli94/foodcom-recipes-with-search-terms-and-tags'

    load_from_kaggle(recipes_images)
    load_from_kaggle(recipes_w_search_terms)