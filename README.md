# Admin-Tareas

App de escritorio (Python + customtkinter) para organizar notas, tareas y gastos.
Tus datos se guardan en tu PC, en `datos/`.

## Cómo correrla
pip install -r requirements.txt
python main.py

## Foto → texto (OCR)
En **Notas**, botón **Foto → texto**: eliges una imagen y el texto se pega donde está el cursor.
Usa [EasyOCR](https://github.com/JaidedAI/EasyOCR) sobre PyTorch:
- **CRAFT** (detector) encuentra cada letra y la unión entre letras vecinas, y arma las palabras.
- **CRNN** (reconocedor: CNN + BiLSTM + CTC) lee cada palabra letra por letra.

La primera vez descarga los modelos (~100 MB) a `modelos/`. Código: `m/ocr.py`.

## Entrenar con tus datos (ampliar la muestra)
1. **Junta fotos** parecidas a lo que vas a leer (tu letra, tus apuntes, pizarrón…).
2. **Recórtalas en palabras**:
   `python herramientas/crear_dataset.py carpeta_con_fotos/`
   Crea `dataset/entrenamiento/` y `dataset/validacion/` con un `.png` por palabra y un `labels.csv`.
3. **Corrige `labels.csv`**: la columna `words` debe decir exactamente lo que dice cada recorte.
   Borra los recortes malos. Cientos de palabras ya ayudan; miles es mejor.
4. **Entrena** con el trainer oficial de EasyOCR:
   - `git clone https://github.com/JaidedAI/EasyOCR` y entra a `EasyOCR/trainer/`.
   - Copia `dataset/entrenamiento` → `trainer/all_data/mi_train` y `dataset/validacion` → `trainer/all_data/mi_val`.
   - Copia `config_files/en_filtered_config.yaml` como `mi_config.yaml` y cambia:
     `experiment_name: 'propio'`, `train_data: 'all_data'`, `valid_data: 'all_data/mi_val'`,
     `select_data: 'mi_train'`, `batch_ratio: '1'`,
     `lang_char:` con las letras del español (incluye `áéíóúüñÁÉÍÓÚÜÑ¿¡`),
     `saved_model: 'ruta/a/Admin-Tareas/modelos/latin_g2.pth'`, `FT: True`, `new_prediction: True`,
     `num_iter: 3000`, `valInterval: 500`, `workers: 0` (Windows).
   - Abre `trainer.ipynb`, pon `mi_config.yaml` y ejecútalo. Sale `saved_models/propio/best_accuracy.pth`.
5. **Úsalo en la app**: en `modelos/` pon
   - `propio.pth` (el `best_accuracy.pth`),
   - `propio.py` (la definición de la red, del ejemplo `custom_example.zip` de la doc de EasyOCR: *custom_model.md*),
   - `propio.yaml` con `network_params` (input_channel 1, output_channel 256, hidden_size 256), `imgH: 64`,
     `lang_list: ['es', 'en']` y `character_list:` = `number + symbol + lang_char` de tu config, en el mismo orden.

   Si están los tres archivos, `m/ocr.py` usa tu modelo en vez del de fábrica.
