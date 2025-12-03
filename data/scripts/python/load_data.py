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

    return os.path.abspath(output_path)


def load_from_kaggle(dataset: str, output_filename: str):
    """
    Télécharge un dataset, prend le premier fichier trouvé, 
    le renomme selon 'output_filename' et le place dans data_cache.
    """
    
    temp_cache_dir = './temp_kaggle_cache'
    os.environ['KAGGLEHUB_CACHE'] = temp_cache_dir

    print(f"Downloading {dataset}...")
    download_path = kagglehub.dataset_download(dataset)

    final_output_dir = './data_cache'
    os.makedirs(final_output_dir, exist_ok=True)
    
    final_file_path = os.path.join(final_output_dir, output_filename)


    files_found = os.listdir(download_path)
    
    if len(files_found) > 0:
        source_file = files_found[0] 
        source_path = os.path.join(download_path, source_file)
        
        if os.path.exists(final_file_path):
            os.remove(final_file_path) 
            
        shutil.move(source_path, final_file_path)
        print(f" -> Success! File saved as: {final_file_path}")
    else:
        print("Error: No file found in the downloaded dataset.")
        final_file_path = None

    print("Cleaning up...")
    shutil.rmtree(temp_cache_dir)

    return os.path.abspath(final_file_path) if final_file_path else None


if __name__ == "__main__":
    raw_recipes = '1fxvf7ghbgH0xkvHkPFM_K8_JbeL9QX3L'
    raw_interactions = '10zdNLf2oKiMY30ZacdwdF1AEpkrbyoUN'
    cleaned_ingredients = '1HjT5RiZnxlg2PkcMLlqzxBjeeRGITYvx'

    raw_recipes_path = load_from_drive(raw_recipes,"RAW_recipes.csv")
    raw_interactions_path = load_from_drive(raw_interactions,"RAW_INTERACTIONS.csv")
    cleaned_ingredients_path = load_from_drive(cleaned_ingredients,"CLEANED_INGREDIENTS.csv")

    recipes_images = 'behnamrahdari/foodcom-enhanced-recipes-with-images'
    recipes_w_search_terms = 'shuyangli94/foodcom-recipes-with-search-terms-and-tags'

    recipes_images_path = load_from_kaggle(recipes_images,"recipes_enhanced_v2.csv")
    recipes_w_search_terms_path = load_from_kaggle(recipes_w_search_terms,"recipes_w_search_terms.csv")
   