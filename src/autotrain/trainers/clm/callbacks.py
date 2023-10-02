import os
import torch
from peft import set_peft_model_state_dict
from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments
from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR
from transformers import TrainerCallback, TrainingArguments, Trainer
from sklearn.metrics import mean_squared_error
from scipy.spatial.distance import cosine
import torch.nn.functional as F


class SavePeftModelCallback(TrainerCallback):
    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        checkpoint_folder = os.path.join(args.output_dir, f"{PREFIX_CHECKPOINT_DIR}-{state.global_step}")

        kwargs["model"].save_pretrained(checkpoint_folder)

        pytorch_model_path = os.path.join(checkpoint_folder, "pytorch_model.bin")
        torch.save({}, pytorch_model_path)
        return control


class LoadBestPeftModelCallback(TrainerCallback):
    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        print(f"Loading best peft model from {state.best_model_checkpoint} (score: {state.best_metric}).")
        best_model_path = os.path.join(state.best_model_checkpoint, "adapter_model.bin")
        adapters_weights = torch.load(best_model_path)
        model = kwargs["model"]
        set_peft_model_state_dict(model, adapters_weights)
        return control

class EvaluateOnEveryPercentCallback(TrainerCallback):
    def __init__(self) -> None:
        super().__init__()
        steps_done = set([0])

    def on_step_begin(self, args: TrainingArguments, state: TrainerState, control: TrainerControl, **kwargs):
        curr_step = state.global_step
        max_steps = state.max_steps
        percent = int(100*(curr_step//max_steps))
        if percent not in self.steps_done:
            self.steps_done.add(percent)
            control.should_evaluate = True
        return control
