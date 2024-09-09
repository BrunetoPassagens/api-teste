from flask import Flask, request, jsonify
from PIL import Image, ExifTags
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import os
import magic

app = Flask(__name__)

# Função para converter coordenadas GPS em um formato legível
def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1]
    seconds = dms[2]

    decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600

    if ref in ['S', 'W']:  # Sul e Oeste devem ser negativos
        decimal = -decimal

    return decimal

# Função para extrair apenas os dados EXIF desejados
def extract_desired_exif(exif_data):
    desired_data = {}
    gps_data = {}

    # Tags que queremos extrair
    desired_tags = {
        'DateTime': 'DateTime',
        'DateTimeDigitized': 'DateTimeDigitized',
        'DateTimeOriginal': 'DateTimeOriginal',
        'Make': 'Make',
        'Software': 'Software',
    }

    for tag, value in exif_data.items():
        decoded_tag = ExifTags.TAGS.get(tag)

        # Se o campo for um dos desejados
        if decoded_tag in desired_tags.values():
            desired_data[decoded_tag] = str(value)
        
        # Extraindo informações GPS, se disponíveis
        if decoded_tag == 'GPSInfo':
            for key in value:
                gps_tag = ExifTags.GPSTAGS.get(key)
                gps_data[gps_tag] = value[key]

            # Extrair latitude e longitude (se disponíveis)
            if 'GPSLatitude' in gps_data and 'GPSLongitude' in gps_data:
                lat = get_decimal_from_dms(gps_data['GPSLatitude'], gps_data['GPSLatitudeRef'])
                lon = get_decimal_from_dms(gps_data['GPSLongitude'], gps_data['GPSLongitudeRef'])
                desired_data['GPSLatitude'] = lat
                desired_data['GPSLongitude'] = lon

    return desired_data

# Função para extrair EXIF de imagens
def extract_image_exif(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            return extract_desired_exif(exif_data)  # Use a função para filtrar os campos desejados
        return {"error": "No EXIF data found"}
    except Exception as e:
        return {"error": str(e)}

# Rota para extrair dados EXIF de uma imagem ou vídeo
@app.route('/extract_exif', methods=['POST'])
def extract_exif():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    file_path = os.path.join('/tmp', file.filename)
    file.save(file_path)
    
    mime_type = magic.from_file(file_path, mime=True)
    
    if mime_type.startswith('image'):
        exif_data = extract_image_exif(file_path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400
    
    os.remove(file_path)  # Limpar o arquivo após o processamento
    return jsonify(exif_data)

if __name__ == '__main__':
    app.run(debug=True)
