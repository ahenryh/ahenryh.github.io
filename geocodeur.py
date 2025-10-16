from geopy.geocoders import Nominatim
import pandas as pd
import time
import os
import folium

# Test une adresse (fonction existante)
def test_une_adresse(adress="175 5th Avenue NYC"):
    geolocator = Nominatim(user_agent="test_christine")
    location = geolocator.geocode(adress)
    if location is not None:        
        print((location.latitude, location.longitude))
        return location.raw
    else:
        return None

# Ouverture des fichiers
with open(r"Usine complet_anonyme.xlsx", 'rb') as f:
    df = pd.read_excel(f, sheet_name='Feuil1')

print(df.shape)  
print(df.columns)

with open(r"019HexaSmal.csv", encoding="latin1") as f:
    laposte = pd.read_csv(f, sep=';')

print(laposte.shape)
print(laposte.columns)

# la jointure après harmonisation des données
df['Code postal INSEE'] = df['Code postal INSEE'].astype(str).str.strip()
laposte['#Code_commune_INSEE'] = laposte['#Code_commune_INSEE'].astype(str).str.strip()
laposte_unique = laposte[['#Code_commune_INSEE', 'Code_postal']].drop_duplicates(subset=['#Code_commune_INSEE'])

df_merged = df.merge(
    laposte_unique,
    how='left',
    left_on='Code postal INSEE',
    right_on='#Code_commune_INSEE'
)

# nouveau fichier avec les codes postaux, mais sans la colonne de jointure qui fait doublon
if '#Code_commune_INSEE' in df_merged.columns:
    df_merged.drop(columns=['#Code_commune_INSEE'], inplace=True)

df_merged.to_excel("Usine_complet_anonyme_avec_Code_postal.xlsx", index=False)

#géocodage final après test 
print(df_merged.columns)

if 'latitude' not in df_merged.columns:
    df_merged['latitude'] = None
if 'longitude' not in df_merged.columns:
    df_merged['longitude'] = None

# Chargement du cache
cache_file = "geocache.csv"
if os.path.exists(cache_file):
    cache_df = pd.read_csv(cache_file)
    geocache = dict(zip(cache_df['adresse'], zip(cache_df['latitude'], cache_df['longitude'])))
else:
    geocache = {}

# géocodeur
geolocator = Nominatim(user_agent="geo_christine")
def geocode_with_retry(address, retries=3):
    for _ in range(retries):
        try:
            return geolocator.geocode(address, timeout=10)
        except:
            time.sleep(2)
    return None

for i, row in df_merged.iterrows():
    if pd.notna(row['latitude']) and pd.notna(row['longitude']):
        continue

    adresse = f"{row['Adresse  ']} {row['Code_postal']}, France"
    if adresse in geocache:
        lat, lon = geocache[adresse]
        df_merged.at[i, 'latitude'] = lat
        df_merged.at[i, 'longitude'] = lon
        print(f"Ligne {i} - trouvé en cache")
    else:
        location = geocode_with_retry(adresse)
        if location:
            df_merged.at[i, 'latitude'] = location.latitude
            df_merged.at[i, 'longitude'] = location.longitude
            geocache[adresse] = (location.latitude, location.longitude)
            print(f"Ligne {i} - géocodé: {location.latitude}, {location.longitude}")
        else:
            df_merged.at[i, 'latitude'] = None
            df_merged.at[i, 'longitude'] = None
            print(f"Ligne {i} - géocodage échoué")

        time.sleep(1)

# Sauvegarde du fichier final
df_merged.to_excel("Usine_geocode_final.xlsx", index=False)
# Sauvegarde du cache pour les relances éventuelles
cache_df = pd.DataFrame([
    {'adresse': k, 'latitude': v[0], 'longitude': v[1]}
    for k, v in geocache.items()
])
cache_df.to_csv(cache_file, index=False)

##seulement 5 échecs au premier essai complet, liés à des coquilles. J'ai corrigé le fichier original de df à la main vue la brièveté du correctif.

# Correction des points hors de la Vienne après 1er essai de cartographie
def est_dans_vienne(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return False
    # coordonnées du 86
    return 46.0 <= lat <= 47.6 and -0.5 <= lon <= 1.5

for i, row in df_merged.iterrows():
    if pd.notna(row['latitude']) and pd.notna(row['longitude']) and est_dans_vienne(row['latitude'], row['longitude']):
        continue
    commune = row.get('Nom_de_la_commune', '').strip()
    code_postal = str(row['Code_postal']).strip()
    adresse_simple = f"{row['Adresse  '].strip()} {code_postal}, France"
    adresse_commune = f"{row['Adresse  '].strip()} {code_postal} {commune}, France" if commune else adresse_simple
    adresse_code_commune = f"{code_postal} {commune}, France" if commune else f"{code_postal}, France"
    adresses_tester = [adresse_commune, adresse_simple, adresse_code_commune]
    location = None
    for adresse in adresses_tester:
        if adresse in geocache:
            lat, lon = geocache[adresse]
            if est_dans_vienne(lat, lon):
                location = type('Loc', (), {'latitude': lat, 'longitude': lon})
                print(f"Ligne {i} - trouvé en cache avec adresse: {adresse}")
                break
        else:
            loc = geocode_with_retry(adresse)
            if loc and est_dans_vienne(loc.latitude, loc.longitude):
                location = loc
                geocache[adresse] = (loc.latitude, loc.longitude)
                print(f"Ligne {i} - géocodé avec adresse: {adresse}")
                break
            else:
                print(f"Ligne {i} - adresse {adresse} hors Vienne ou non trouvée")

        time.sleep(1) 
        
    if location:
        df_merged.at[i, 'latitude'] = location.latitude
        df_merged.at[i, 'longitude'] = location.longitude
    else:
        df_merged.at[i, 'latitude'] = None
        df_merged.at[i, 'longitude'] = None
        print(f"Ligne {i} - géocodage échoué ou hors zone")

df_merged.to_excel("Geocodage_corrige.xlsx", index=False)

#création d'une carte avec folium
center_lat = df_merged['latitude'].mean()
center_lon = df_merged['longitude'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=6)
for _, row in df_merged.iterrows():
    if pd.notna(row['latitude']) and pd.notna(row['longitude']):
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=f"{row['code_usine']} - {row['Adresse  ']}",
        ).add_to(m)
m.save("Carte_geocodage.html")