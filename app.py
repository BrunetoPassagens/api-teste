from flask import Flask, request, jsonify
from PIL import Image, ExifTags
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import os
import magic

app = Flask(__name__)

# Função para tornar os dados EXIF serializáveis em JSON
def make_serializable(exif_data):
    serializable_data = {}
    for tag, value in exif_data.items():
        if isinstance(value, bytes):
            value = value.decode(errors='ignore')  # Converta bytes para string
        elif isinstance(value, tuple):
            value = tuple(float(v) if isinstance(v, IFDRational) else v for v in value)  # Converta IFDRational em float
        elif isinstance(value, IFDRational):
            value = float(value)  # Converta IFDRational diretamente em float
        serializable_data[ExifTags.TAGS.get(tag)] = value
    return serializable_data

# Função para extrair EXIF de imagens
def extract_image_exif(image_path):
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if exif_data:
            return make_serializable(exif_data)  # Use a função para serializar
        return {"error": "No EXIF data found"}
    except Exception as e:
        return {"error": str(e)}

# Função para extrair metadados de vídeos
def extract_video_metadata(video_path):
    try:
        parser = createParser(video_path)
        if not parser:
            return {"error": "Unable to parse video"}
        
        with parser:
            metadata = extractMetadata(parser)
            if not metadata:
                return {"error": "No metadata found"}
            return metadata.exportDictionary()
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
    elif mime_type.startswith('video'):
        exif_data = extract_video_metadata(file_path)
    else:
        return jsonify({"error": "Unsupported file type"}), 400
    
    os.remove(file_path)  # Limpar o arquivo após o processamento
    return jsonify(exif_data)

if __name__ == '__main__':
    app.run(debug=True)
