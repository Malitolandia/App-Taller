/**
 * Comprime una imagen en el navegador antes de guardarla como base64 en
 * Google Sheets (cada celda soporta hasta ~50.000 caracteres). Reduce
 * tamaño y calidad progresivamente hasta quedar por debajo del límite.
 *
 * Devuelve un data URL "data:image/jpeg;base64,..." o null si el archivo
 * no es una imagen soportada.
 */
async function compressImageFile(file, { maxBytes = 42000 } = {}) {
  if (!file || !/^image\/(jpeg|png|jpg)$/.test(file.type)) {
    throw new Error('Solo se aceptan imágenes JPG o PNG.');
  }

  const dataUrl = await readFileAsDataUrl(file);
  const img = await loadImage(dataUrl);

  const attempts = [
    { maxDim: 700, quality: 0.7 },
    { maxDim: 550, quality: 0.6 },
    { maxDim: 420, quality: 0.5 },
    { maxDim: 320, quality: 0.4 },
  ];

  let result = null;
  for (const attempt of attempts) {
    result = drawToJpeg(img, attempt.maxDim, attempt.quality);
    if (result.length <= maxBytes) return result;
  }

  throw new Error('La imagen es demasiado pesada incluso comprimida. Prueba con otra foto más simple.');
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('No se pudo leer el archivo.'));
    reader.readAsDataURL(file);
  });
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error('No se pudo cargar la imagen.'));
    img.src = src;
  });
}

function drawToJpeg(img, maxDim, quality) {
  const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
  const w = Math.max(1, Math.round(img.width * scale));
  const h = Math.max(1, Math.round(img.height * scale));

  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(img, 0, 0, w, h);

  return canvas.toDataURL('image/jpeg', quality);
}
