import os
import kagglehub

def download_datasets():
    # Ham verilerin saklanacağı dizin
    raw_dir = "data/raw"
    os.makedirs(raw_dir, exist_ok=True)
    
    print("Billboard Hot 100 veri seti indiriliyor...")
    path_bb = kagglehub.dataset_download("dhruvildave/billboard-the-hot-100-songs")
    print(f"Billboard indirildi: {path_bb}")
    
    print("Top Spotify Songs veri seti indiriliyor...")
    path_sp = kagglehub.dataset_download("asaniczka/top-spotify-songs-in-73-countries-daily-updated")
    print(f"Spotify indirildi: {path_sp}")
    
    print("İndirme işlemi tamamlandı. Lütfen ham CSV dosyalarını data/raw/ altına taşıyın/bağlayın.")

if __name__ == "__main__":
    download_datasets()
