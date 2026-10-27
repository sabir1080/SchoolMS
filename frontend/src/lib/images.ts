/**
 * Shrink an uploaded image so its longer side is at most ``size`` px and return a data URL under ``maxChars``.
 * ``keepTransparency`` tries PNG first (logos); photos go straight to JPEG.
 */
export function resizeImage(
  file: File,
  size: number,
  maxChars: number,
  keepTransparency = false,
): Promise<string> {
  return new Promise((resolve, reject) => {
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      reject(new Error("Please choose a PNG, JPG or WebP image."));
      return;
    }
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      const scale = Math.min(1, size / Math.max(img.width, img.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(img.width * scale));
      canvas.height = Math.max(1, Math.round(img.height * scale));
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Could not read this image."));
        return;
      }
      if (!keepTransparency) {
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      let data = keepTransparency ? canvas.toDataURL("image/png") : "";
      for (const quality of [0.85, 0.7, 0.55]) {
        if (data && data.length <= maxChars) break;
        data = canvas.toDataURL("image/jpeg", quality);
      }
      if (data.length > maxChars) {
        reject(
          new Error("This image is too large. Please choose a smaller one."),
        );
        return;
      }
      resolve(data);
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error("Could not read this image."));
    };
    img.src = url;
  });
}
