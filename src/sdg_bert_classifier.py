"""SDG BERT Classifier Module.

Integrates the sadickam/sdgBERT model for SDG classification alongside
the sentence transformer approach. Provides ensemble capabilities.

Reference:
- Model: https://huggingface.co/sadickam/sdgBERT
- Paper: Sadick et al. (2026), Journal of Construction Engineering and Management
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import warnings

import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from src.exceptions import ModelLoadError


# SDG definitions (matching the sdgBERT model's output classes)
# Note: sdgBERT only covers SDG 1-16, not SDG 17
SDG_BERT_MAPPING = {
    0: {"sdg": 1, "name": "No Poverty", "color": "#E5243B"},
    1: {"sdg": 2, "name": "Zero Hunger", "color": "#DDA63A"},
    2: {"sdg": 3, "name": "Good Health and Well-being", "color": "#4C9F38"},
    3: {"sdg": 4, "name": "Quality Education", "color": "#C5192D"},
    4: {"sdg": 5, "name": "Gender Equality", "color": "#FF3A21"},
    5: {"sdg": 6, "name": "Clean Water and Sanitation", "color": "#26BDE2"},
    6: {"sdg": 7, "name": "Affordable and Clean Energy", "color": "#FCC30B"},
    7: {"sdg": 8, "name": "Decent Work and Economic Growth", "color": "#A21942"},
    8: {"sdg": 9, "name": "Industry, Innovation and Infrastructure", "color": "#FD6925"},
    9: {"sdg": 10, "name": "Reduced Inequalities", "color": "#DD1367"},
    10: {"sdg": 11, "name": "Sustainable Cities and Communities", "color": "#FD9D24"},
    11: {"sdg": 12, "name": "Responsible Consumption and Production", "color": "#BF8B2E"},
    12: {"sdg": 13, "name": "Climate Action", "color": "#3F7E44"},
    13: {"sdg": 14, "name": "Life Below Water", "color": "#0A97D9"},
    14: {"sdg": 15, "name": "Life on Land", "color": "#56C02B"},
    15: {"sdg": 16, "name": "Peace, Justice and Strong Institutions", "color": "#00689D"},
}


class SDGBERTClassifier:
    """
    SDG BERT Classifier using sadickam/sdgBERT model.
    
    Provides single-label classification for SDG 1-16.
    SDG 17 (Partnerships) is not covered by this model.
    
    Performance (from model card):
    - Accuracy: 90%
    - Matthews Correlation: 0.89
    
    Reference:
        Sadick, A.-M., Hasan, A. and Ahiaga-Dagbui, D.D. (2026),
        "Modeling sustainability discourse in the construction industry: 
        A deep-learning approach". Journal of Construction Engineering and 
        Management, 152(4). DOI: 10.1061/JCEMD4.COENG-16205
    """
    
    MODEL_NAME = "sadickam/sdgBERT"
    
    def __init__(self, model_name: Optional[str] = None, device: Optional[str] = None):
        """
        Initialize the SDG BERT classifier.

        Args:
            model_name: HuggingFace model name (default: sadickam/sdgBERT)
            device: Device to use ('cuda', 'mps', 'cpu', or None for auto)
        """
        self.model_name = model_name or self.MODEL_NAME

        # Auto-detect best device: CUDA > MPS > CPU
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

        print(f"Loading sdgBERT model: {self.model_name}")
        print(f"Device: {self.device}")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()
            print("✓ sdgBERT model loaded successfully")
        except Exception as e:
            raise ModelLoadError(f"Failed to load sdgBERT model: {e}. "
                                 f"Ensure transformers and torch are installed.") from e
        
        self.num_labels = len(SDG_BERT_MAPPING)
        
    def predict(self, text: str, return_all_scores: bool = False) -> Union[int, Dict]:
        """
        Predict SDG for a single text.
        
        Args:
            text: Input text to classify
            return_all_scores: If True, return probabilities for all SDGs
            
        Returns:
            If return_all_scores=False: predicted SDG number (1-16)
            If return_all_scores=True: dict with 'sdg', 'confidence', 'all_scores'
        """
        if not text or not text.strip():
            if return_all_scores:
                return {
                    'sdg': None,
                    'confidence': 0.0,
                    'all_scores': {i: 0.0 for i in range(1, 17)}
                }
            return None
        
        # Tokenize
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=512
        ).to(self.device)
        
        # Predict
        with torch.no_grad():
            outputs = self.model(**inputs)
            probabilities = torch.softmax(outputs.logits, dim=1)
            probabilities = probabilities.cpu().numpy()[0]
        
        # Get predicted class
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])
        
        # Map to SDG number
        predicted_sdg = SDG_BERT_MAPPING[predicted_class]['sdg']
        
        if not return_all_scores:
            return predicted_sdg
        
        # Build scores dict for all SDGs
        all_scores = {}
        for class_idx, prob in enumerate(probabilities):
            sdg_num = SDG_BERT_MAPPING[class_idx]['sdg']
            all_scores[sdg_num] = float(prob)
        
        # Add SDG 17 with 0 score (not covered by model)
        all_scores[17] = 0.0
        
        return {
            'sdg': predicted_sdg,
            'confidence': confidence,
            'all_scores': all_scores
        }
    
    def predict_batch(self, texts: List[str], batch_size: int = 16, show_progress: bool = False) -> List[Dict]:
        """
        Predict SDGs for a batch of texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            show_progress: Whether to show progress bar

        Returns:
            List of prediction dicts
        """
        results = []

        # Create iterator with optional progress bar
        batches = list(range(0, len(texts), batch_size))
        if show_progress:
            from tqdm import tqdm
            batches = tqdm(batches, desc="sdgBERT", unit="batch")

        for i in batches:
            batch = texts[i:i + batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(self.device)
            
            # Predict
            with torch.no_grad():
                outputs = self.model(**inputs)
                probabilities = torch.softmax(outputs.logits, dim=1)
                probabilities = probabilities.cpu().numpy()
            
            # Process each prediction
            for probs in probabilities:
                predicted_class = int(np.argmax(probs))
                confidence = float(probs[predicted_class])
                predicted_sdg = SDG_BERT_MAPPING[predicted_class]['sdg']
                
                # Build all scores
                all_scores = {}
                for class_idx, prob in enumerate(probs):
                    sdg_num = SDG_BERT_MAPPING[class_idx]['sdg']
                    all_scores[sdg_num] = float(prob)
                all_scores[17] = 0.0  # Not covered
                
                results.append({
                    'sdg': predicted_sdg,
                    'confidence': confidence,
                    'all_scores': all_scores
                })
        
        return results
    
    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        return {
            'model_name': self.model_name,
            'device': self.device,
            'num_parameters': sum(p.numel() for p in self.model.parameters()),
            'num_trainable_parameters': sum(p.numel() for p in self.model.parameters() if p.requires_grad),
            'coverage': 'SDG 1-16 (excludes SDG 17)',
            'performance': {
                'accuracy': 0.90,
                'matthews_correlation': 0.89
            },
            'citation': 'Sadick et al. (2026), Journal of Construction Engineering and Management'
        }


class EnsembleSDGClassifier:
    """
    Ensemble classifier combining Sentence Transformer and sdgBERT.
    
    Uses weighted combination of both models for improved accuracy.
    
    Weights based on observed performance:
    - Sentence Transformer (fine-tuned): 87.6% accuracy
    - sdgBERT: 90.0% accuracy
    
    Recommended weights:
    - sdgBERT: 0.55 (higher accuracy)
    - Sentence Transformer: 0.45 (complementary approach)
    """
    
    def __init__(
        self,
        sentence_transformer_engine,
        sdg_bert_classifier: Optional[SDGBERTClassifier] = None,
        sdg_bert_weight: float = 0.55,
        st_weight: float = 0.45
    ):
        """
        Initialize ensemble classifier.
        
        Args:
            sentence_transformer_engine: AlignmentEngine instance
            sdg_bert_classifier: SDGBERTClassifier instance (auto-created if None)
            sdg_bert_weight: Weight for sdgBERT predictions (default: 0.55)
            st_weight: Weight for Sentence Transformer predictions (default: 0.45)
        """
        self.st_engine = sentence_transformer_engine
        self.sdg_bert = sdg_bert_classifier or SDGBERTClassifier()
        self.sdg_bert_weight = sdg_bert_weight
        self.st_weight = st_weight
        
        # Validate weights sum to 1.0
        total_weight = sdg_bert_weight + st_weight
        if abs(total_weight - 1.0) > 0.001:
            warnings.warn(f"Weights should sum to 1.0, got {total_weight}")
        
        print(f"Ensemble weights: sdgBERT={sdg_bert_weight}, SentenceTransformer={st_weight}")
    
    def predict(self, text: str) -> Dict:
        """
        Predict SDG using ensemble of both models.
        
        Args:
            text: Input text to classify
            
        Returns:
            Dict with ensemble predictions and individual model outputs
        """
        # Get sentence transformer prediction
        st_alignment = self.st_engine.align_activity(text, return_top_n=1)
        st_top_sdg = st_alignment['top_sdg']
        st_top_score = st_alignment['top_score']
        
        # Get sdgBERT prediction
        sdg_bert_result = self.sdg_bert.predict(text, return_all_scores=True)
        
        # Combine scores using weighted average
        ensemble_scores = {}
        for sdg_num in range(1, 18):
            st_score = 0.0
            # Normalize ST score to probability-like (assume max score ~0.6)
            st_score_raw = st_alignment['all_scores'].get(sdg_num, {}).get('score', 0)
            st_score = min(st_score_raw / 0.6, 1.0)  # Normalize
            
            sdg_bert_score = sdg_bert_result['all_scores'].get(sdg_num, 0)
            
            # Weighted ensemble
            ensemble_scores[sdg_num] = (
                self.sdg_bert_weight * sdg_bert_score + 
                self.st_weight * st_score
            )
        
        # Get top prediction from ensemble
        ensemble_top_sdg = max(ensemble_scores.keys(), key=lambda k: ensemble_scores[k])
        ensemble_top_score = ensemble_scores[ensemble_top_sdg]
        
        # Check for model agreement
        models_agree = (st_top_sdg == sdg_bert_result['sdg'])
        
        return {
            'ensemble': {
                'predicted_sdg': ensemble_top_sdg,
                'score': ensemble_top_score,
                'all_scores': ensemble_scores
            },
            'sentence_transformer': {
                'predicted_sdg': st_top_sdg,
                'score': st_top_score,
                'raw_score': st_alignment['all_scores'].get(st_top_sdg, {}).get('score', 0)
            },
            'sdg_bert': sdg_bert_result,
            'models_agree': models_agree,
            'agreement_sdg': st_top_sdg if models_agree else None
        }
    
    def predict_with_fallback(self, text: str, confidence_threshold: float = 0.5) -> Dict:
        """
        Predict using fallback strategy.
        
        Strategy:
        1. If Sentence Transformer confidence is high (>threshold), use ST
        2. If Sentence Transformer confidence is low, use sdgBERT
        3. Return both predictions and indicate which was used
        
        Args:
            text: Input text
            confidence_threshold: Threshold for ST confidence (default: 0.5)
            
        Returns:
            Dict with prediction and metadata
        """
        # Get both predictions
        st_alignment = self.st_engine.align_activity(text, return_top_n=1)
        st_top_sdg = st_alignment['top_sdg']
        st_top_score = st_alignment['top_score']
        
        sdg_bert_result = self.sdg_bert.predict(text, return_all_scores=True)
        sdg_bert_sdg = sdg_bert_result['sdg']
        sdg_bert_confidence = sdg_bert_result['confidence']
        
        # Determine which model to trust
        if st_top_score >= confidence_threshold:
            primary_model = 'sentence_transformer'
            predicted_sdg = st_top_sdg
            confidence = st_top_score
        else:
            primary_model = 'sdg_bert'
            predicted_sdg = sdg_bert_sdg
            confidence = sdg_bert_confidence
        
        return {
            'predicted_sdg': predicted_sdg,
            'confidence': confidence,
            'primary_model': primary_model,
            'sentence_transformer': {
                'predicted_sdg': st_top_sdg,
                'score': st_top_score
            },
            'sdg_bert': {
                'predicted_sdg': sdg_bert_sdg,
                'confidence': sdg_bert_confidence
            },
            'models_agree': st_top_sdg == sdg_bert_sdg,
            'threshold_used': confidence_threshold
        }


def compare_classifiers(
    texts: List[str],
    st_engine,
    sdg_bert_classifier: SDGBERTClassifier,
    true_labels: Optional[List[int]] = None
) -> Dict:
    """
    Compare Sentence Transformer and sdgBERT on a set of texts.
    
    Args:
        texts: List of texts to classify
        st_engine: Sentence Transformer AlignmentEngine
        sdg_bert_classifier: SDGBERT classifier
        true_labels: Optional true labels for accuracy calculation
        
    Returns:
        Comparison statistics
    """
    results = {
        'sentence_transformer': [],
        'sdg_bert': [],
        'agreement_count': 0,
        'disagreement_count': 0
    }
    
    for i, text in enumerate(texts):
        # Get predictions
        st_alignment = st_engine.align_activity(text, return_top_n=1)
        st_sdg = st_alignment['top_sdg']
        
        sdg_bert_result = sdg_bert_classifier.predict(text, return_all_scores=True)
        sdg_bert_sdg = sdg_bert_result['sdg']
        
        result = {
            'text': text[:100] + "..." if len(text) > 100 else text,
            'sentence_transformer_sdg': st_sdg,
            'sdg_bert_sdg': sdg_bert_sdg,
            'agree': st_sdg == sdg_bert_sdg
        }
        
        if true_labels:
            result['true_label'] = true_labels[i]
            result['st_correct'] = st_sdg == true_labels[i]
            result['sdg_bert_correct'] = sdg_bert_sdg == true_labels[i]
        
        results['sentence_transformer'].append(st_sdg)
        results['sdg_bert'].append(sdg_bert_sdg)
        
        if st_sdg == sdg_bert_sdg:
            results['agreement_count'] += 1
        else:
            results['disagreement_count'] += 1
    
    # Calculate agreement rate
    total = len(texts)
    results['agreement_rate'] = results['agreement_count'] / total if total > 0 else 0
    
    # Calculate accuracies if true labels provided
    if true_labels:
        st_correct = sum(1 for i, pred in enumerate(results['sentence_transformer']) 
                        if pred == true_labels[i])
        sdg_bert_correct = sum(1 for i, pred in enumerate(results['sdg_bert']) 
                              if pred == true_labels[i])
        
        results['sentence_transformer_accuracy'] = st_correct / total
        results['sdg_bert_accuracy'] = sdg_bert_correct / total
    
    return results
