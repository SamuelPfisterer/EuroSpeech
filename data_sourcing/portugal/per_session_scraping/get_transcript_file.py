def download_txt_from_url(url, destination, file_name):
    import os
    import requests
    from urllib.parse import urlparse

    # Parse the URL to extract parameters
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split('/')

    # Extract parameters from URL path
    parameters = {
        "periodo": path_parts[2],
        "publicacao": path_parts[3],
        "serie": path_parts[4],
        "legis": path_parts[5],
        "sessao": path_parts[6],
        "numero": path_parts[7],
        "data": path_parts[8],
        "exportType": "txt",
        "exportControl": "documentoCompleto"
    }

    # Make the POST request
    response = requests.post("https://debates.parlamento.pt/pagina/export", data=parameters)

    # Check if request was successful
    if response.status_code == 200:
        file_path = os.path.join(destination, file_name)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(response.text)
        print(f"File saved successfully at {file_path}")
    else:
        print(f"Failed to download file. Status code: {response.status_code}")

# Example usage:
url = "https://debates.parlamento.pt/catalogo/r3/dar/01/16/01/055/2024-10-25"
destination = "."
file_name = "output.txt"
download_txt_from_url(url, destination, file_name)