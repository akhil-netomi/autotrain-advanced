from dataclasses import dataclass
from typing import Optional

import pandas as pd
from datasets import ClassLabel, Dataset
from sklearn.model_selection import train_test_split


RESERVED_COLUMNS = ["autotrain_text", "autotrain_label"]
LLM_RESERVED_COLUMNS = [
    "autotrain_prompt",
    "autotrain_context",
    "autotrain_rejected_text",
    "autotrain_prompt_start",
]


@dataclass
class TextBinaryClassificationPreprocessor:
    train_data: pd.DataFrame
    text_column: str
    label_column: str
    username: str
    project_name: str
    token: str
    valid_data: Optional[pd.DataFrame] = None
    test_size: Optional[float] = 0.2
    seed: Optional[int] = 42
    convert_to_class_label: Optional[bool] = False

    def __post_init__(self):
        # check if text_column and label_column are in train_data
        if self.text_column not in self.train_data.columns:
            raise ValueError(f"{self.text_column} not in train data")
        if self.label_column not in self.train_data.columns:
            raise ValueError(f"{self.label_column} not in train data")
        # check if text_column and label_column are in valid_data
        if self.valid_data is not None:
            if self.text_column not in self.valid_data.columns:
                raise ValueError(f"{self.text_column} not in valid data")
            if self.label_column not in self.valid_data.columns:
                raise ValueError(f"{self.label_column} not in valid data")

        # make sure no reserved columns are in train_data or valid_data
        for column in RESERVED_COLUMNS:
            if column in self.train_data.columns:
                raise ValueError(f"{column} is a reserved column name")
            if self.valid_data is not None:
                if column in self.valid_data.columns:
                    raise ValueError(f"{column} is a reserved column name")

    def split(self):
        if self.valid_data is not None:
            return self.train_data, self.valid_data
        else:
            train_df, valid_df = train_test_split(
                self.train_data,
                test_size=self.test_size,
                random_state=self.seed,
                stratify=self.train_data[self.label_column],
            )
            train_df = train_df.reset_index(drop=True)
            valid_df = valid_df.reset_index(drop=True)
            return train_df, valid_df

    def prepare_columns(self, train_df, valid_df):
        train_df.loc[:, "autotrain_text"] = train_df[self.text_column]
        train_df.loc[:, "autotrain_label"] = train_df[self.label_column]
        valid_df.loc[:, "autotrain_text"] = valid_df[self.text_column]
        valid_df.loc[:, "autotrain_label"] = valid_df[self.label_column]

        # drop text_column and label_column
        train_df = train_df.drop(columns=[self.text_column, self.label_column])
        valid_df = valid_df.drop(columns=[self.text_column, self.label_column])
        return train_df, valid_df

    def prepare(self):
        train_df, valid_df = self.split()
        train_df, valid_df = self.prepare_columns(train_df, valid_df)

        label_names = sorted(set(train_df["autotrain_label"].unique().tolist()))

        train_df = Dataset.from_pandas(train_df)
        valid_df = Dataset.from_pandas(valid_df)

        if self.convert_to_class_label:
            train_df = train_df.cast_column("autotrain_label", ClassLabel(names=label_names))
            valid_df = valid_df.cast_column("autotrain_label", ClassLabel(names=label_names))

        train_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="train",
            private=True,
            token=self.token,
        )
        valid_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="validation",
            private=True,
            token=self.token,
        )
        return train_df, valid_df


class TextMultiClassClassificationPreprocessor(TextBinaryClassificationPreprocessor):
    pass


class TextSingleColumnRegressionPreprocessor(TextBinaryClassificationPreprocessor):
    def split(self):
        if self.valid_data is not None:
            return self.train_data, self.valid_data
        else:
            train_df, valid_df = train_test_split(
                self.train_data,
                test_size=self.test_size,
                random_state=self.seed,
            )
            train_df = train_df.reset_index(drop=True)
            valid_df = valid_df.reset_index(drop=True)
            return train_df, valid_df


@dataclass
class LLMPreprocessor:
    train_data: pd.DataFrame
    username: str
    project_name: str
    token: str
    valid_data: Optional[pd.DataFrame] = None
    test_size: Optional[float] = 0.2
    seed: Optional[int] = 42
    text_column: Optional[str] = None
    prompt_column: Optional[str] = None
    rejected_text_column: Optional[str] = None

    def __post_init__(self):
        # user can either provide text_column or prompt_column and rejected_text_column
        if self.text_column is not None and (self.prompt_column is not None or self.rejected_text_column is not None):
            raise ValueError("Please provide either text_column or prompt_column and rejected_text_column")

        if self.text_column is not None:
            # if text_column is provided, use it for prompt_column and rejected_text_column
            self.prompt_column = self.text_column
            self.rejected_text_column = self.text_column

        # check if text_column and rejected_text_column are in train_data
        if self.prompt_column not in self.train_data.columns:
            raise ValueError(f"{self.prompt_column} not in train data")
        if self.rejected_text_column not in self.train_data.columns:
            raise ValueError(f"{self.rejected_text_column} not in train data")
        # check if text_column and rejected_text_column are in valid_data
        if self.valid_data is not None:
            if self.prompt_column not in self.valid_data.columns:
                raise ValueError(f"{self.prompt_column} not in valid data")
            if self.rejected_text_column not in self.valid_data.columns:
                raise ValueError(f"{self.rejected_text_column} not in valid data")

        # make sure no reserved columns are in train_data or valid_data
        for column in RESERVED_COLUMNS + LLM_RESERVED_COLUMNS:
            if column in self.train_data.columns:
                raise ValueError(f"{column} is a reserved column name")
            if self.valid_data is not None:
                if column in self.valid_data.columns:
                    raise ValueError(f"{column} is a reserved column name")

    def split(self):
        if self.valid_data is not None:
            return self.train_data, self.valid_data
        # no validation is done in llm training if validation data is not provided
        return self.train_data, self.train_data
        # else:
        #     train_df, valid_df = train_test_split(
        #         self.train_data,
        #         test_size=self.test_size,
        #         random_state=self.seed,
        #     )
        #     train_df = train_df.reset_index(drop=True)
        #     valid_df = valid_df.reset_index(drop=True)
        #     return train_df, valid_df

    def prepare_columns(self, train_df, valid_df):
        if self.text_column is not None:
            train_df.loc[:, "autotrain_text"] = train_df[self.text_column]
            valid_df.loc[:, "autotrain_text"] = valid_df[self.text_column]

            # drop text_column and label_column
            train_df = train_df.drop(columns=[self.text_column])
            valid_df = valid_df.drop(columns=[self.text_column])
            return train_df, valid_df
        else:
            train_df.loc[:, "autotrain_prompt"] = train_df[self.prompt_column]
            valid_df.loc[:, "autotrain_prompt"] = valid_df[self.prompt_column]

            train_df.loc[:, "autotrain_rejected_text"] = train_df[self.rejected_text_column]
            valid_df.loc[:, "autotrain_rejected_text"] = valid_df[self.rejected_text_column]

            train_df = train_df.drop(columns=[self.prompt_column, self.rejected_text_column])
            valid_df = valid_df.drop(columns=[self.prompt_column, self.rejected_text_column])

            return train_df, valid_df

    def prepare(self):
        train_df, valid_df = self.split()
        train_df, valid_df = self.prepare_columns(train_df, valid_df)
        train_df = Dataset.from_pandas(train_df)
        valid_df = Dataset.from_pandas(valid_df)
        train_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="train",
            private=True,
            token=self.token,
        )
        valid_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="validation",
            private=True,
            token=self.token,
        )
        return train_df, valid_df


@dataclass
class Seq2SeqPreprocessor:
    train_data: pd.DataFrame
    text_column: str
    label_column: str
    username: str
    project_name: str
    token: str
    valid_data: Optional[pd.DataFrame] = None
    test_size: Optional[float] = 0.2
    seed: Optional[int] = 42

    def __post_init__(self):
        # check if text_column and label_column are in train_data
        if self.text_column not in self.train_data.columns:
            raise ValueError(f"{self.text_column} not in train data")
        if self.label_column not in self.train_data.columns:
            raise ValueError(f"{self.label_column} not in train data")
        # check if text_column and label_column are in valid_data
        if self.valid_data is not None:
            if self.text_column not in self.valid_data.columns:
                raise ValueError(f"{self.text_column} not in valid data")
            if self.label_column not in self.valid_data.columns:
                raise ValueError(f"{self.label_column} not in valid data")

        # make sure no reserved columns are in train_data or valid_data
        for column in RESERVED_COLUMNS:
            if column in self.train_data.columns:
                raise ValueError(f"{column} is a reserved column name")
            if self.valid_data is not None:
                if column in self.valid_data.columns:
                    raise ValueError(f"{column} is a reserved column name")

    def split(self):
        if self.valid_data is not None:
            return self.train_data, self.valid_data
        else:
            train_df, valid_df = train_test_split(
                self.train_data,
                test_size=self.test_size,
                random_state=self.seed,
                stratify=self.train_data[self.label_column],
            )
            train_df = train_df.reset_index(drop=True)
            valid_df = valid_df.reset_index(drop=True)
            return train_df, valid_df

    def prepare_columns(self, train_df, valid_df):
        train_df.loc[:, "autotrain_text"] = train_df[self.text_column]
        train_df.loc[:, "autotrain_label"] = train_df[self.label_column]
        valid_df.loc[:, "autotrain_text"] = valid_df[self.text_column]
        valid_df.loc[:, "autotrain_label"] = valid_df[self.label_column]

        # drop text_column and label_column
        train_df = train_df.drop(columns=[self.text_column, self.label_column])
        valid_df = valid_df.drop(columns=[self.text_column, self.label_column])
        return train_df, valid_df

    def prepare(self):
        train_df, valid_df = self.split()
        train_df, valid_df = self.prepare_columns(train_df, valid_df)

        train_df = Dataset.from_pandas(train_df)
        valid_df = Dataset.from_pandas(valid_df)

        train_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="train",
            private=True,
            token=self.token,
        )
        valid_df.push_to_hub(
            f"{self.username}/autotrain-data-{self.project_name}",
            split="validation",
            private=True,
            token=self.token,
        )
        return train_df, valid_df
