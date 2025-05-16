import argparse









def main():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest_dir", type=str, default="/itet-stor/spfisterer/net_scratch/Downloading/countries/upload_dataset/manifests")
    parser.add_argument("--country", type=str, default="all")
    args = parser.parse_args()
    main(args)
