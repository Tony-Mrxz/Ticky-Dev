import os
import shutil

def package():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(base_dir, "dist")
    app_dir = os.path.join(dist_dir, "Ticky.app")
    zip_out = os.path.join(dist_dir, "Ticky-macOS")
    
    if os.path.exists(app_dir):
        print(f"Packaging {app_dir} into {zip_out}.zip...")
        shutil.make_archive(zip_out, 'zip', dist_dir, "Ticky.app")
        print(f"Successfully created: {zip_out}.zip")
    else:
        print("dist/Ticky.app does not exist yet.")

if __name__ == "__main__":
    package()
