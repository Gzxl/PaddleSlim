import os
import math
import random
import functools
import numpy as np
import paddle
from PIL import Image, ImageEnhance
from paddle.io import Dataset

random.seed(0)
np.random.seed(0)

DATA_DIM = 224

THREAD = 16
BUF_SIZE = 10240

DATA_DIR = 'data/ILSVRC2012/'
DATA_DIR = os.path.join(os.path.split(os.path.realpath(__file__))[0], DATA_DIR)

img_mean = np.array([0.485, 0.456, 0.406]).reshape((3, 1, 1))
img_std = np.array([0.229, 0.224, 0.225]).reshape((3, 1, 1))


def resize_short(img, target_size):
    percent = float(target_size) / min(img.size[0], img.size[1])
    resized_width = int(round(img.size[0] * percent))
    resized_height = int(round(img.size[1] * percent))
    img = img.resize((resized_width, resized_height), Image.LANCZOS)
    return img


def crop_image(img, target_size, center):
    width, height = img.size
    size = target_size
    if center == True:
        w_start = (width - size) / 2
        h_start = (height - size) / 2
    else:
        w_start = np.random.randint(0, width - size + 1)
        h_start = np.random.randint(0, height - size + 1)
    w_end = w_start + size
    h_end = h_start + size
    img = img.crop((w_start, h_start, w_end, h_end))
    return img


def random_crop(img, size, scale=[0.08, 1.0], ratio=[3. / 4., 4. / 3.]):
    aspect_ratio = math.sqrt(np.random.uniform(*ratio))
    w = 1. * aspect_ratio
    h = 1. / aspect_ratio

    bound = min((float(img.size[0]) / img.size[1]) / (w**2),
                (float(img.size[1]) / img.size[0]) / (h**2))
    scale_max = min(scale[1], bound)
    scale_min = min(scale[0], bound)

    target_area = img.size[0] * img.size[1] * np.random.uniform(scale_min,
                                                                scale_max)
    target_size = math.sqrt(target_area)
    w = int(target_size * w)
    h = int(target_size * h)

    i = np.random.randint(0, img.size[0] - w + 1)
    j = np.random.randint(0, img.size[1] - h + 1)

    img = img.crop((i, j, i + w, j + h))
    img = img.resize((size, size), Image.LANCZOS)
    return img


def rotate_image(img):
    angle = np.random.randint(-10, 11)
    img = img.rotate(angle)
    return img


def distort_color(img):
    def random_brightness(img, lower=0.5, upper=1.5):
        e = np.random.uniform(lower, upper)
        return ImageEnhance.Brightness(img).enhance(e)

    def random_contrast(img, lower=0.5, upper=1.5):
        e = np.random.uniform(lower, upper)
        return ImageEnhance.Contrast(img).enhance(e)

    def random_color(img, lower=0.5, upper=1.5):
        e = np.random.uniform(lower, upper)
        return ImageEnhance.Color(img).enhance(e)

    ops = [random_brightness, random_contrast, random_color]
    np.random.shuffle(ops)

    img = ops[0](img)
    img = ops[1](img)
    img = ops[2](img)

    return img


def process_image(sample, mode, color_jitter, rotate):
    img_path = sample[0]

    try:
        img = Image.open(img_path)
    except:
        print(img_path, "not exists!")
        return None
    if mode == 'train':
        if rotate: img = rotate_image(img)
        img = random_crop(img, DATA_DIM)
    else:
        img = resize_short(img, target_size=256)
        img = crop_image(img, target_size=DATA_DIM, center=True)
    if mode == 'train':
        if color_jitter:
            img = distort_color(img)
        if np.random.randint(0, 2) == 1:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img = np.array(img).astype('float32').transpose((2, 0, 1)) / 255
    img -= img_mean
    img /= img_std

    if mode == 'train' or mode == 'val':
        return img, sample[1]
    elif mode == 'test':
        return [img]


def _reader_creator(file_list,
                    mode,
                    shuffle=False,
                    color_jitter=False,
                    rotate=False,
                    data_dir=DATA_DIR,
                    batch_size=1):
    def reader():
        try:
            with open(file_list) as flist:
                full_lines = [line.strip() for line in flist]
                if shuffle:
                    np.random.shuffle(full_lines)
                lines = full_lines
                for line in lines:
                    if mode == 'train' or mode == 'val':
                        img_path, label = line.split()
                        img_path = os.path.join(data_dir, img_path)
                        yield img_path, int(label)
                    elif mode == 'test':
                        img_path = os.path.join(data_dir, line)
                        yield [img_path]
        except Exception as e:
            print("Reader failed!\n{}".format(str(e)))
            os._exit(1)

    mapper = functools.partial(
        process_image, mode=mode, color_jitter=color_jitter, rotate=rotate)

    return paddle.reader.xmap_readers(mapper, reader, THREAD, BUF_SIZE)


def train(data_dir=DATA_DIR):
    file_list = os.path.join(data_dir, 'train_list.txt')
    return _reader_creator(
        file_list,
        'train',
        shuffle=True,
        color_jitter=False,
        rotate=False,
        data_dir=data_dir)


def val(data_dir=DATA_DIR):
    file_list = os.path.join(data_dir, 'val_list.txt')
    return _reader_creator(file_list, 'val', shuffle=False, data_dir=data_dir)


def test(data_dir=DATA_DIR):
    file_list = os.path.join(data_dir, 'test_list.txt')
    return _reader_creator(file_list, 'test', shuffle=False, data_dir=data_dir)


class ImageNetDataset(Dataset):
    def __init__(self, data_dir=DATA_DIR, mode='train'):
        super(ImageNetDataset, self).__init__()
        train_file_list = os.path.join(data_dir, 'train_list.txt')
        val_file_list = os.path.join(data_dir, 'val_list.txt')
        test_file_list = os.path.join(data_dir, 'test_list.txt')
        self.mode = mode
        if mode == 'train':
            with open(train_file_list) as flist:
                full_lines = [line.strip() for line in flist]
                np.random.shuffle(full_lines)
                lines = full_lines
            self.data = [line.split() for line in lines]
        else:
            with open(val_file_list) as flist:
                lines = [line.strip() for line in flist]
                self.data = [line.split() for line in lines]

    def __getitem__(self, index):
        sample = self.data[index]
        data_path = os.path.join(DATA_DIR, sample[0])
        if self.mode == 'train':
            data, label = process_image(
                [data_path, sample[1]],
                mode='train',
                color_jitter=False,
                rotate=False)
            return data, np.array([label]).astype('int64')
        elif self.mode == 'val':
            data, label = process_image(
                [data_path, sample[1]],
                mode='val',
                color_jitter=False,
                rotate=False)
            return data, np.array([label]).astype('int64')
        elif self.mode == 'test':
            data = process_image(
                [data_path, sample[1]],
                mode='test',
                color_jitter=False,
                rotate=False)
            return data

    def __len__(self):
        return len(self.data)
