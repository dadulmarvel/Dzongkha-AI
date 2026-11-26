import csv, torch
from transformers import (AutoTokenizer, AutoModelForSeq2SeqLM, DataCollatorForSeq2Seq,
                          Seq2SeqTrainer, Seq2SeqTrainingArguments)

BASE = "facebook/nllb-200-distilled-600M"
tok = AutoTokenizer.from_pretrained(BASE, src_lang="eng_Latn", tgt_lang="dzo_Tibt")
model = AutoModelForSeq2SeqLM.from_pretrained(BASE)

def load(path):
    with open(path, encoding="utf-8") as f:
        return [dict(tok(r["english"], text_target=r["dzongkha"],
                         max_length=128, truncation=True))
                for r in csv.DictReader(f)]

train, val = load("train.csv"), load("val.csv")

args = Seq2SeqTrainingArguments(
    output_dir="checkpoints",
    per_device_train_batch_size=8,        # use 4 if Colab runs out of memory
    per_device_eval_batch_size=8,
    num_train_epochs=6,
    learning_rate=2e-5,                   # low on purpose: small dataset, avoid forgetting
    warmup_ratio=0.1,
    weight_decay=0.01,
    label_smoothing_factor=0.1,
    eval_strategy="epoch",
    save_strategy="epoch",
    save_total_limit=2,
    load_best_model_at_end=True,          # keeps the epoch with the lowest validation loss
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    logging_steps=20,
    fp16=torch.cuda.is_available(),       # if the loss shows "nan", change this to False
    report_to="none",
)
trainer = Seq2SeqTrainer(model=model, args=args, train_dataset=train, eval_dataset=val,
                         data_collator=DataCollatorForSeq2Seq(tok, model=model),
                         processing_class=tok)
trainer.train()
trainer.save_model("nllb-dz")
tok.save_pretrained("nllb-dz")
print("Saved to nllb-dz")