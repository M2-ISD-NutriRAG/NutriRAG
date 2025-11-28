import pandas as pd
import numpy as np
import re
import math

VULGAR_TO_ASCII = {
    '¼':'1/4','½':'1/2','¾':'3/4','⅐':'1/7','⅑':'1/9','⅒':'1/10',
    '⅓':'1/3','⅔':'2/3','⅕':'1/5','⅖':'2/5','⅗':'3/5','⅘':'4/5',
    '⅙':'1/6','⅚':'5/6','⅛':'1/8','⅜':'3/8','⅝':'5/8','⅞':'7/8'
}

CONV_VOLUME = {'teaspoon':4.93,'tablespoon':14.79,'cup':236.588,'pint':473.176,'quart':946.353,
               'gallon':3785.41,'fluid ounce':29.5735,'dash':0.625,'splash':5.91,'pony':29.57,
               'jigger':44.36,'shot':44.36,'snit':88.72,'wineglass':118.29,'split':177.44,
               'gill':118.294,'fluid scruple':1.184,'drop':0.05,'smidgen':0.15,'scoop':56}
CONV_WEIGHT = {'ounce':28.3495,'lb':453.59237,'pound':453.59237}

def normalize_fractions(s: str) -> str:
    if not isinstance(s, str): return s
    for k,v in VULGAR_TO_ASCII.items(): s = s.replace(k,v)
    return s.replace('⁄','/')

def parse_single_expr(expr: str) -> None | int | float:
    if not isinstance(expr, str): return None
    expr = expr.strip()
    if expr == "": return None
    m = re.match(r'^(-?\d+)\s+(\d+)/(\d+)$', expr)
    if m: return int(m.group(1)) + int(m.group(2))/int(m.group(3))
    m = re.match(r'^(-?\d+)/(\d+)$', expr)
    if m: return int(m.group(1))/int(m.group(2))
    m = re.match(r'^-?\d+(?:[.,]\d+)?$', expr)
    if m: return float(expr.replace(',','.'))
    return None

def parse_quantity_string(s: str | None | float) -> float:
    if s is None or (isinstance(s,float) and math.isnan(s)) or s=='': return None
    s = normalize_fractions(str(s))
    s = s.replace('–','-').replace('—','-')
    s = re.sub(r'\s*-\s*',' - ',s)
    parts = [p.strip() for p in s.split(' - ') if p.strip()]
    
    vals = [parse_single_expr(p) for p in parts[:2]]
    for i,v in enumerate(vals):
        if v is None:
            m = re.search(r'(?:(\d+)\s+(\d+/\d+))|(\d+/\d+)|(-?\d+(?:[.,]\d+)?)', parts[i])
            if m: vals[i] = parse_single_expr(m.group(0))
    parsed_vals = [v for v in vals if v is not None]
    if not parsed_vals: return None
    return sum(parsed_vals)/len(parsed_vals)

def clean_list_column(col: pd.Series) -> pd.Series:
    def _clean(l):
        if l is None or isinstance(l, list): return l
        return [s.strip() for s in l.replace('[','').replace(']','').replace("'",'').split(",")]
    return col.apply(_clean)

def normalize_units(col: pd.Series) -> pd.Series:
    units = {'cup','dash','drop','fluid ounce','gallon','gill','lb','ounce','pinch','pint',
             'pound','quart','scoop','smidgen','tablespoon','teaspoon'}
    plural_to_singular = {u+'s':u for u in units}
    plural_to_singular.update({'lbs':'lb','fluid ounces':'fluid ounce','gills':'gill'})
    return col.str.strip().replace(plural_to_singular)

def convert_units(df: pd.DataFrame) -> pd.DataFrame:
    unit_norm = df['unit'].astype(str).str.lower().str.strip()
    df['qty_ml'] = np.where(unit_norm.isin(CONV_VOLUME),
                             df['quantity'].astype(float)*unit_norm.map(CONV_VOLUME),
                             np.nan)
    df['qty_g'] = np.where(unit_norm.isin(CONV_WEIGHT),
                            df['quantity'].astype(float)*unit_norm.map(CONV_WEIGHT),
                            np.nan)
    return df

# --- Pipeline finale ---
def process_ingredients_with_enrich(raw_csv_path: str, enrich_csv_path: str, output_csv_path: str) -> pd.DataFrame:
    df_raw = pd.read_csv(raw_csv_path, index_col='id')
    
    df_enrich = pd.read_csv(enrich_csv_path, index_col='id')
    df_enrich = df_enrich[['ingredients','quantities']]
    
    df = df_raw.drop(columns=['ingredients'], errors='ignore').join(df_enrich, how='inner')
    
    df.replace({'[]':None,'':None}, inplace=True)
    
    df_ing = df[['ingredients','quantities']].copy()
    df_ing['ingredients'] = clean_list_column(df_ing['ingredients'])
    df_ing['quantities'] = clean_list_column(df_ing['quantities'])
    df_ing = df_ing[df_ing['ingredients'].str.len() == df_ing['quantities'].str.len()]
    df_ing = df_ing.explode(['ingredients','quantities'])
    df_ing.rename(columns={'quantities':'quantity_raw_str'}, inplace=True)
    
    df_ing['unit'] = normalize_units(df_ing['quantity_raw_str'].str.extract(r'([A-Za-z]+(?:\s[A-Za-z]+)?)')[0])
    df_ing['quantity'] = df_ing['quantity_raw_str'].str.replace(r'([A-Za-z]+(?:\s[A-Za-z]+)?)','',regex=True)
    df_ing['quantity'] = df_ing['quantity'].apply(lambda x: round(parse_quantity_string(x),3) if parse_quantity_string(x) is not None else "")
    
    df_ing.replace({'':None}, inplace=True)

    df_ing = convert_units(df_ing)
    
    df_ing.to_csv(output_csv_path, index=False)
    return df_ing

if __name__ == "__main__":
    df_final = process_ingredients_with_enrich(
        './data/RAW_recipes.csv',
        './data/enrich/recipe_enhanced_v2.csv',
        './output/ingredients_exploded.csv'
    )
