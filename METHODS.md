# The Project Flows

- Workflow diagram is provided in docs/pipeline_flow_diagram.md

- How to run CLI:
    cd to documents/github/claude3/sdg-alignment-analyzer, then run the following on the prompt:

    python scripts/run_analysis.py --input data/raw --output results/2026-04-26 --worker 8 

- How to run app server:
    

## Extract Sentences from PDF
src/activity_extractor.py

## Identify Activity Sentence

scripts/split_activity_data.py

scripts/finetune_activity_classifier.py =>  - Train: scripts/finetune_activity_classifier.py — loads base microsoft/deberta-v3-small, fine-tunes on 8,033 LLM-labeled

src/activity_classifier.py => Infer: src/activity_classifier.py — loads the saved model, model.eval(), no gradients, batch classify only                   

scripts/activity_extraction_quality_assessment.py




# Detailed explanantion of each script


## /Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/scripts/split_activity_data.py
Run script:
    python scripts/split_activity_data.py --inputs data/processed/sentence_labels_raw_deepseek-v4-pro-cloud-2026-05-03.csv data/processed/sentence_labels_raw_glm-5.1-cloud-2026-05-03.csv data/processed/sentence_labels_raw_kimi-k2.6-cloud-2026-05-03.csv data/processed/sentence_labels_raw_minimax-m2.7-cloud-2026-05-03.csv

Output:
    /Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/data/splits

## /Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/scripts/finetune_activity_classifier.py

⏺ scripts/finetune_activity_classifier.py

  Fine-tunes DeBERTa-v3-small as activity sentence classifier.
                       
  Two modes:
           
  - --binary: 2-class — ACTION vs NOT_ACTION (NEUTRAL + POLICY merged → 0, ACTION → 1)                                             
  - Default (no flag): 3-class — NEUTRAL=0, POLICY=1, ACTION=2. Merges to binary at inference time anyway.                         
                                                                                                                                   

  Input CSV files: data/splits/activity_train.csv, activity_val.csv, activity_test.csv.   

  Source chain:
  1. Raw sentences extracted from PDFs via scripts/extract_raw_sentences.py — pulls candidate sentences from stratified PDF sample, Jaccard-deduplicates
  2. LLM-labeled via scripts/label_sentences_batch.py — sends batches to deepseek/deepseek-v3.2 (OpenRouter), labels each as ACTION/POLICY/NEUTRAL                    
  3. Split via scripts/split_activity_data.py — 50/25/25 train/val/test split
                        
  The 8,000 sentences come from local government annual report PDFs in data/LGAcleannames/.     
                                                                                                                                   
  Data Flow          
  data/splits/activity_{train,val,test}.csv → load_split() → ActivityDataset → WeightedTrainer                                     
                                                                                                                                   
  CSV columns: text, label. load_split() reads CSV, maps string labels to ints via LABEL_MAP_3CLASS or LABEL_MAP_BINARY. Text      
  truncation+padding to 256 tokens via DebertaV2Tokenizer.                                                                         
                                                                                                                                   
  Key Design Decisions                                                                                                             
                              
  Label smoothing 0.15 (line 186-187): LLM labels have noise — the LLM sometimes labels borderline sentences inconsistently. Label 
  smoothing prevents the model from becoming overconfident on noisy labels. 0.15 means "be 85% sure, not 100%."                  
                                                                                                                                   
  Inverse-frequency class weights (line 88-93): weights = 1/counts, normalized so sum = num_classes. Handles class imbalance. If   
  ACTION is 30% of data, it gets higher weight per sample.
                                                                                                                                   
  WeightedTrainer (line 96-113): Custom HuggingFace Trainer override. Injects class_weights + label_smoothing into                 
  CrossEntropyLoss. Standard Trainer doesn't support both together.
                                                                                                                                   
  CPU eval (line 335): model.cpu() before test evaluation. Avoids MPS bugs in HuggingFace Trainer.predict(). Training uses GPU,    
  eval uses CPU.              
                                                                                                                                   
  fp16 only on CUDA (line 291): MPS fp16 is unstable for DeBERTa. Only enables mixed precision when device == "cuda".              
                              
  Training Config                                                                                                                  
                                                                                                                                 
  ┌────────────────┬─────────┬────────────────────────────────────┐                                                                
  │ Hyperparameter │ Default │              Purpose               │                                                              
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ epochs         │ 5       │ Best epoch at 3 per cerebrum       │                                                              
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ lr             │ 2e-5    │ Standard for DeBERTa fine-tune     │                                                                
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ batch size     │ 32      │ Fits in 16GB MPS                   │                                                                
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ warmup ratio   │ 0.1     │ Linear warmup first 10% of steps   │                                                              
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ weight decay   │ 0.01    │ L2 regularization                  │                                                              
  ├────────────────┼─────────┼────────────────────────────────────┤                                                                
  │ max length     │ 256     │ Covers ~98% of extracted sentences │                                                              
  └────────────────┴─────────┴────────────────────────────────────┘                                                                
                                                                                                                                 
  Metrics (make_compute_metrics, line 116)                                                                                         
                                                                                                                                 
  Uses eval_strategy="epoch" + load_best_model_at_end=True with metric_for_best_model="f1_macro".                                  
                                                                                                                                 
  For 3-class: reports per-class F1 (NEUTRAL/POLICY/ACTION) + binary F1 (ACTION vs rest). For binary: F1 per class + macro.        
                                                                                                                                 
  Output                                                                                                                           
                                                                                                                                 
  - Model saved to models/activity-classifier/activity-classifier-{mode}-{timestamp}/                                              
  - training_metadata.json with full hyperparams + metrics                                                                       
  - Symlink models/activity-classifier/latest → best model (used by ActivityClassifier at inference)                               

Consensus retraining task complete. Summary of what was updated:                                                     
                                                        
  - docs/pipeline_workflow.md: Activity Classifier Details — training data changed from "8,033 LLM-labeled (deepseek-v3.2)" to     
  "8,000 consensus-labeled (4-model majority vote)", metrics updated to F1 macro=0.868, ACTION P=0.849 R=0.858                     
  - docs/activity_classifier_comparison.md: Added Consensus Retraining section with side-by-side comparison table (original vs     
  consensus metrics)                                                                                                                                 
  All 13 tests pass. Model symlink models/activity-classifier/latest → activity-classifier-binary-20260504_074923.                 

                                                                                    

# /Users/alfonspalangkaraya/Documents/GitHub/claude3/sdg-alignment-analyzer/src/activity_classifier.py
⏺ Binary DeBERTa-v3-small classifier. 2 labels: NOT_ACTION (0) and ACTION (1).

  Training: 8,033 LLM-labeled sentences from local government annual reports. Test F1 macro: 0.872, ACTION precision: 0.862,
  recall: 0.889.

  Architecture:
  - DebertaV2Tokenizer + AutoModelForSequenceClassification (44M params)
  - Max sequence length 256 tokens, batch size 16
  - Auto-detects device: CUDA > MPS > CPU

  Methods:

  classify(text) — single sentence. Tokenize → softmax over logits → argmax wins. Returns {label, label_name, confidence,
  is_activity}. is_activity is label == 1.

  classify_batch(texts) — same but in chunks of 16. Avoids re-tokenizing per sentence.

  Key details:
  - Model path: models/activity-classifier/latest (symlink to best checkpoint)
  - Relative paths resolved against PROJECT_ROOT, symlinks followed via .resolve()
  - cleanup() moves model to CPU, clears MPS cache — prevents SIGBUS at process exit
  - Falls back gracefully: if model load fails, caller (ActivityExtractor) catches and falls back to spaCy

  Why DeBERTa-v3-small over alternatives:
  - Better accuracy than DistilBERT (88.2% MNLI vs ~82%)
  - Smaller file size (44M vs 66M params)               
  - Only marginally slower inference     
