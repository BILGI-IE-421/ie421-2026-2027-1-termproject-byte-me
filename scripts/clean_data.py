import os
import pandas as pd

def clean_billboard(input_path, output_path):
    print("Billboard verisi işleniyor ve temizleniyor...")
    df = pd.read_csv(input_path)
    
    # Tarih formatını standartlaştır
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    
    # Eşleştirme için temiz sütunlar oluştur
    df['song_clean'] = df['song'].str.lower().str.strip()
    df['artist_clean'] = df['artist'].str.lower().str.strip()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Billboard kaydedildi: {output_path} ({len(df)} satır)")

def clean_spotify(input_path, output_path):
    print("Spotify verisi işleniyor ve temizleniyor...")
    df = pd.read_csv(input_path)
    
    # Tarih ve eksik ülke dönüşümleri
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'])
    df['country'] = df['country'].fillna('GLOBAL')
    
    df['song_clean'] = df['name'].str.lower().str.strip()
    df['artist_clean'] = df['artists'].str.lower().str.strip()
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Spotify kaydedildi: {output_path} ({len(df)} satır)")

if __name__ == "__main__":
    pass
