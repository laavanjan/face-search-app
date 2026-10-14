// Low-bandwidth support (SOC-08): shrink large photos on the device before
// upload. The server downsizes to 1600 px anyway, so nothing useful is lost,
// and a 12 MB phone photo becomes a few hundred KB.
const MAX_DIM = 1600;

export async function shrinkForUpload(file: File): Promise<File> {
  if (typeof createImageBitmap !== "function" || file.size < 600_000) return file;
  try {
    const bmp = await createImageBitmap(file, { imageOrientation: "from-image" });
    const scale = Math.min(1, MAX_DIM / Math.max(bmp.width, bmp.height));
    if (scale === 1 && file.size < 2_000_000) return file;
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bmp.width * scale);
    canvas.height = Math.round(bmp.height * scale);
    canvas.getContext("2d")!.drawImage(bmp, 0, 0, canvas.width, canvas.height);
    const blob: Blob | null = await new Promise((r) => canvas.toBlob(r, "image/jpeg", 0.9));
    if (!blob || blob.size >= file.size) return file;
    return new File([blob], file.name.replace(/\.\w+$/, "") + ".jpg", { type: "image/jpeg" });
  } catch {
    return file; // unsupported format in this browser: upload as-is
  }
}

export const fmtSize = (n: number) => (n > 1_000_000 ? `${(n / 1_000_000).toFixed(1)} MB` : `${Math.round(n / 1000)} KB`);
