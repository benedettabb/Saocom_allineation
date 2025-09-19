import rasterio
import numpy as np
import os
from scipy.signal import fftconvolve
import matplotlib.pyplot as plt
from pathlib import Path
import glob 
from scipy.stats import pearsonr
import sys
from multiprocessing import Pool, cpu_count
log_file = r"D:\Saocom_test\aligned\log.txt"

def cross_fft(img1, img2, mask=None):
    img1 = np.where(mask, img1, 0).astype(float)
    img2 = np.where(mask, img2, 0).astype(float)
    img1 -= np.mean(img1)
    img2 -= np.mean(img2)
    corr = fftconvolve(img1, img2[::-1, ::-1], mode='full')
    y_max, x_max = np.unravel_index(np.argmax(corr), corr.shape)
    shift_y = y_max - (img1.shape[0] - 1)
    shift_x = x_max - (img1.shape[1] - 1)
    return shift_y, shift_x

def apply_shift(img, shift, nodata=-9999):
    dy, dx = shift
    img_shifted = np.roll(img, dy, axis=0)
    img_shifted = np.roll(img_shifted, -dx, axis=1)
    # Imposta bordi a nodata
    if dy > 0:
        img_shifted[:dy, :] = nodata
    elif dy < 0:
        img_shifted[dy:, :] = nodata
    if dx > 0:
        img_shifted[:, :dx] = nodata
    elif dx < 0:
        img_shifted[:, dx:] = nodata
    return img_shifted

def read(path, nodata=-9999):
    with rasterio.open(path) as src:
        data = src.read()  # shape: (bands, rows, cols)
        profile = src.profile
        mask = data[0] != nodata  # usa prima banda per mask
    return profile, mask, data

def align(saocom, sentinel1, nodata = -9999):
    out = os.path.join(r"D:\Saocom_test\aligned", Path(saocom).name)
    if not os.path.isfile(out):
        try:
            profile_img, img_mask, img = read(saocom)
            _, ref_mask, ref = read(sentinel1)

            # Calcola cross-corr
            shift_y, shift_x = cross_fft(img[0], ref[0], mask=img_mask & ref_mask)
            aligned = np.zeros_like(img)
            for b in range(img.shape[0]):
                aligned[b] = apply_shift(img[b], [shift_y, shift_x], nodata)

            # Guarda correlazione
            valid_mask = (aligned[0] != -9999) & (ref[0] != -9999)
            r_before = pearsonr(img[0][valid_mask].ravel(), ref[0][valid_mask].ravel())[0]
            r_after = pearsonr(aligned[0][valid_mask].ravel(), ref[0][valid_mask].ravel())[0]

            # Scrivi direttamente sul file
            with open(log_file, "a") as f:
                f.write(f"{saocom} {shift_y} {shift_x} {r_before:.3f} {r_after:.3f}\n")

            with rasterio.open(out, 'w', **profile_img) as dst:
                dst.write(aligned)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    asc_imgs = glob.glob(r"D:\EOVeg\DEFINITIVE\Data\*ASC_E051N016T1.tif")
    des_imgs = glob.glob(r"D:\EOVeg\DEFINITIVE\Data\*DES_E051N016T1.tif")
    asc_ref = r"D:\Saocom_test\Sentine1\asc\asc_ref_E051N016T1.tif"
    des_ref = r"D:\Saocom_test\Sentine1\des\desc_ref_E051N016T1.tif"
    # Crea lista di coppie (file, ref)
    pairs = [(img, asc_ref) for img in asc_imgs] + [(img, des_ref) for img in des_imgs]
    # Lancia multiprocessing
    with Pool(2) as pool:
        pool.starmap(align, pairs)

sys.stdout.close()
sys.stdout = sys.__stdout__
