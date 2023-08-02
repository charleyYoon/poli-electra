"""
Reference: https://colab.research.google.com/github/huggingface/notebooks/blob/main/examples/text_classification-tf.ipynb#scrollTo=P_qHpojde5gp
"""
from datasets import load_dataset
import evaluate
from transformers import ElectraTokenizer, TFAutoModelForSequenceClassification, create_optimizer
from transformers.keras_callbacks import KerasMetricCallback, PushToHubCallback
from tensorflow.keras.callbacks import TensorBoard, ModelCheckpoint
import tensorflow as tf
import numpy as np
import argparse
import os
import json


metric = evaluate.load("accuracy")
tokenizer = ElectraTokenizer.from_pretrained("model")


def preprocess_function(examples):
    return tokenizer(examples["text"], truncation=True)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    return metric.compute(predictions=predictions, references=labels)


def load_label(path):
    with open(path, "r", encoding="utf-8") as f:
        id2label = json.load(f)

    return id2label


def main():
    # Load
    dataset = load_dataset("json", data_files={"train": f"data/police/train.json", "test": "data/police/test.json"}, field="data")
    id2label = load_label("data/police/id2law.json")
    label2id = {val: key for key, val in id2label.items()}

    # Encode Data
    encoded_dataset = dataset.map(preprocess_function, batched=True)

    # Create Optimizer
    batch_size = 8
    num_epochs = 5
    batches_per_epoch = len(encoded_dataset["train"]) // batch_size
    total_train_steps = int(batches_per_epoch * num_epochs)
    optimizer, schedule = create_optimizer(init_lr=2e-5, num_warmup_steps=0, num_train_steps=total_train_steps)

    # Build Model & Compile
    model = TFAutoModelForSequenceClassification.from_pretrained("model", num_labels=len(id2label), id2label=id2label, label2id=label2id)
    model.compile(optimizer=optimizer)

    # Preprocess Data
    tf_train_dataset = model.prepare_tf_dataset(
        encoded_dataset["train"],
        shuffle=True,
        batch_size=batch_size,
        tokenizer=tokenizer
    )

    tf_validation_dataset = model.prepare_tf_dataset(
        encoded_dataset["test"],
        shuffle=False,
        batch_size=batch_size,
        tokenizer=tokenizer,
    )

    # Train
    metric_callback = KerasMetricCallback(metric_fn=compute_metrics, eval_dataset=tf_validation_dataset)
    # push_to_hub_callback = PushToHubCallback(
    #     output_dir="result/police",
    #     tokenizer=tokenizer,
    # )

    callbacks = [metric_callback]

    model.fit(
        tf_train_dataset,
        validation_data=tf_validation_dataset,
        epochs=num_epochs,
        callbacks=callbacks,
    )

    model.save_pretrained("result/tuned_tokenizer/police")


if __name__ == '__main__':
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--model", type=str, required=True, help="path/to/model")
    # args = parser.parse_args()
    #
    # main(args.model)
    main()
