import rasterio
import numpy as np
import os
from scipy.signal import fftconvolve
import matplotlib.pyplot as plt


def cross_fft(img1, img2, mask=None):
    if mask is not None:
        img1 = np.where(mask, img1, 0).astype(float)
        img2 = np.where(mask, img2, 0).astype(float)
    img1 -= np.mean(img1)
    img2 -= np.mean(img2)
    corr = fftconvolve(img1, img2[::-1, ::-1], mode='full')
    y_max, x_max = np.unravel_index(np.argmax(corr), corr.shape)
    shift_y = y_max - (img1.shape[0] - 1)
    shift_x = x_max - (img1.shape[1] - 1)
    print(shift_y, shift_x)
    plt.imshow(corr)
    plt.show()
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

def read(path):
    with rasterio.open(path) as src:
        data = src.read()  # shape: (bands, rows, cols)
        profile = src.profile
        mask = data[0] != nodata  # usa prima banda per mask
    return profile, mask, data

folder = r"D:\Saocom_test"
asc_path = r"asc.tif"
des_path = r"desc.tif"
ref_path = r"S1_ref.tif"
nodata = -9999

# Read multiband
profile_asc, asc_mask, asc = read(os.path.join(folder, asc_path))
profile_des, des_mask, des = read(os.path.join(folder, des_path))
profile_ref, ref_mask, ref = read(os.path.join(folder, ref_path))

# Calcola lo shift usando solo la prima banda
shift_y_asc, shift_x_asc   = cross_fft(asc[0], ref[0], mask=asc_mask & ref_mask)
shift_y_des, shift_x_des = cross_fft(des[0], ref[0], mask=des_mask & ref_mask)

# Applica lo shift a tutte le bande
asc_aligned = np.zeros_like(asc)
des_aligned = np.zeros_like(des)
for b in range(asc.shape[0]):
    asc_aligned[b] = apply_shift(asc[b], [shift_y_asc, shift_x_asc], nodata)
for b in range(des.shape[0]):
    des_aligned[b] = apply_shift(des[b], [shift_y_des, shift_x_des], nodata)

# Percorsi output
asc_out = os.path.join(folder, "asc_aligned.tif")
des_out = os.path.join(folder, "des_aligned.tif")

# Salvataggio multibanda
with rasterio.open(asc_out, 'w', **profile_asc) as dst:
    dst.write(asc_aligned)

with rasterio.open(des_out, 'w', **profile_des) as dst:
    dst.write(des_aligned)
