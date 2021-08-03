import os
from os.path import exists, join
from pathlib import Path
from typing import Optional, Tuple

from pytorch_lightning import LightningDataModule
from torch.utils.data import ConcatDataset, DataLoader, Dataset, random_split

from src.datamodules.datasets.musdb import MusdbTrainDataset, MusdbValidDataset


class MusdbDataModule(LightningDataModule):
    """
    LightningDataModule for Musdb18-HQ dataset.
    A DataModule implements 5 key methods:
        - prepare_data (things to do on 1 GPU/TPU, not on every GPU/TPU in distributed mode)
        - setup (things to do on every accelerator in distributed mode)
        - train_dataloader (the training dataloader)
        - val_dataloader (the validation dataloader(s))
        - test_dataloader (the test dataloader(s))
    This allows you to share a full dataset without explaining how to download,
    split, transform and process the data
    Read the docs:
        https://pytorch-lightning.readthedocs.io/en/latest/extensions/datamodules.html
    """

    def __init__(
            self,
            data_dir: str,
            aug_params,
            target_name: str,
            n_fft: int,
            hop_length: int,
            dim_c: int,
            dim_f: int,
            dim_t: int,
            sample_rate: int,
            batch_size: int,
            num_workers: int,
            pin_memory: bool,
            **kwargs,
    ):
        super().__init__()

        self.data_dir = Path(data_dir)
        self.target_name = target_name
        self.aug_params = aug_params
        self.batch_size = batch_size
        self.num_workers = num_workers
        self.pin_memory = pin_memory

        # audio-related
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.dim_c = dim_c
        self.dim_f = dim_f
        self.dim_t = dim_t
        self.sample_rate = sample_rate

        # derived
        self.n_bins = n_fft // 2 + 1
        self.chunk_size = hop_length * (dim_t - 1)
        self.overlap = n_fft // 2

        self.data_train: Optional[Dataset] = None
        self.data_val: Optional[Dataset] = None
        self.data_test: Optional[Dataset] = None

        trainset_path = self.data_dir.joinpath('train')
        validset_path = self.data_dir.joinpath('valid')

        # create validation split
        if not exists(validset_path):
            from shutil import move
            os.mkdir(validset_path)
            for track in kwargs['validation_set']:
                if trainset_path.joinpath(track).exists():
                    move(trainset_path.joinpath(track), validset_path.joinpath(track))
        else:
            valid_files = os.listdir(validset_path)
            assert set(valid_files) == set(kwargs['validation_set'])

    def setup(self, stage: Optional[str] = None):
        """Load data. Set variables: self.data_train, self.data_val, self.data_test."""
        self.data_train = MusdbTrainDataset(self.data_dir,
                                            self.chunk_size,
                                            self.target_name,
                                            self.aug_params)

        self.data_val = MusdbValidDataset(self.data_dir,
                                          self.chunk_size,
                                          self.target_name,
                                          self.overlap,
                                          self.batch_size)

    def train_dataloader(self):
        return DataLoader(
            dataset=self.data_train,
            batch_size=self.batch_size,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            shuffle=True,
        )

    def val_dataloader(self):
        return DataLoader(
            dataset=self.data_val,
            batch_size=1,
            num_workers=self.num_workers,
            pin_memory=self.pin_memory,
            shuffle=False,
        )