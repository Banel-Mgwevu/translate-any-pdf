#!/usr/bin/env python3
"""
Translation Evaluation Metrics Module

Provides various metrics to evaluate translation quality:
- BLEU: Bilingual Evaluation Understudy Score
- ChrF: Character n-gram F-score
- METEOR: Metric for Evaluation of Translation with Explicit ORdering
- BERTScore: Contextual embeddings-based metric
"""

import re
from collections import Counter
import math


class TranslationEvaluator:
    """Evaluate translation quality using multiple metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def tokenize(self, text):
        """Simple tokenization"""
        # Convert to lowercase and split by whitespace and punctuation
        tokens = re.findall(r'\w+', text.lower())
        return tokens
    
    def get_ngrams(self, tokens, n):
        """Get n-grams from tokens"""
        return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]
    
    def get_char_ngrams(self, text, n):
        """Get character n-grams"""
        text = text.lower().replace(' ', '')
        return [text[i:i+n] for i in range(len(text)-n+1)]
    
    def calculate_bleu(self, reference, hypothesis, max_n=4):
        """
        Calculate BLEU score
        
        Args:
            reference: Reference translation (ground truth)
            hypothesis: Hypothesis translation (system output)
            max_n: Maximum n-gram size (default: 4)
            
        Returns:
            BLEU score (0-100)
        """
        ref_tokens = self.tokenize(reference)
        hyp_tokens = self.tokenize(hypothesis)
        
        if not hyp_tokens:
            return 0.0
        
        # Brevity penalty
        ref_len = len(ref_tokens)
        hyp_len = len(hyp_tokens)
        
        if hyp_len > ref_len:
            bp = 1.0
        else:
            bp = math.exp(1 - ref_len / hyp_len) if hyp_len > 0 else 0
        
        # Calculate precision for each n-gram
        precisions = []
        
        for n in range(1, max_n + 1):
            ref_ngrams = Counter(self.get_ngrams(ref_tokens, n))
            hyp_ngrams = Counter(self.get_ngrams(hyp_tokens, n))
            
            if not hyp_ngrams:
                precisions.append(0.0)
                continue
            
            # Count matches
            matches = sum((hyp_ngrams & ref_ngrams).values())
            total = sum(hyp_ngrams.values())
            
            precision = matches / total if total > 0 else 0
            precisions.append(precision)
        
        # Calculate geometric mean
        if any(p == 0 for p in precisions):
            geo_mean = 0.0
        else:
            log_sum = sum(math.log(p) for p in precisions)
            geo_mean = math.exp(log_sum / len(precisions))
        
        bleu_score = bp * geo_mean * 100
        
        return round(bleu_score, 2)
    
    def calculate_chrf(self, reference, hypothesis, n=6, beta=2.0):
        """
        Calculate ChrF score (Character n-gram F-score)
        
        Args:
            reference: Reference translation
            hypothesis: Hypothesis translation
            n: Maximum character n-gram size (default: 6)
            beta: Beta parameter for F-score (default: 2.0)
            
        Returns:
            ChrF score (0-100)
        """
        # Get character n-grams
        chrf_scores = []
        
        for i in range(1, n + 1):
            ref_ngrams = Counter(self.get_char_ngrams(reference, i))
            hyp_ngrams = Counter(self.get_char_ngrams(hypothesis, i))
            
            if not hyp_ngrams or not ref_ngrams:
                continue
            
            # Calculate precision and recall
            matches = sum((hyp_ngrams & ref_ngrams).values())
            
            precision = matches / sum(hyp_ngrams.values()) if sum(hyp_ngrams.values()) > 0 else 0
            recall = matches / sum(ref_ngrams.values()) if sum(ref_ngrams.values()) > 0 else 0
            
            # Calculate F-score
            if precision + recall > 0:
                f_score = ((1 + beta**2) * precision * recall) / ((beta**2 * precision) + recall)
                chrf_scores.append(f_score)
        
        if not chrf_scores:
            return 0.0
        
        # Average across all n-gram sizes
        chrf = (sum(chrf_scores) / len(chrf_scores)) * 100
        
        return round(chrf, 2)
    
    def calculate_meteor(self, reference, hypothesis):
        """
        Calculate METEOR score (simplified version)
        
        This is a simplified implementation. Full METEOR requires:
        - WordNet for synonyms
        - Paraphrase tables
        - Stemming
        
        Args:
            reference: Reference translation
            hypothesis: Hypothesis translation
            
        Returns:
            METEOR score (0-100)
        """
        ref_tokens = self.tokenize(reference)
        hyp_tokens = self.tokenize(hypothesis)
        
        if not hyp_tokens or not ref_tokens:
            return 0.0
        
        # Find matches
        ref_matched = set()
        hyp_matched = set()
        matches = 0
        
        # Exact matching
        for i, hyp_token in enumerate(hyp_tokens):
            for j, ref_token in enumerate(ref_tokens):
                if hyp_token == ref_token and j not in ref_matched:
                    matches += 1
                    ref_matched.add(j)
                    hyp_matched.add(i)
                    break
        
        # Calculate precision and recall
        precision = matches / len(hyp_tokens) if len(hyp_tokens) > 0 else 0
        recall = matches / len(ref_tokens) if len(ref_tokens) > 0 else 0
        
        # Calculate F-mean
        if precision + recall == 0:
            f_mean = 0.0
        else:
            f_mean = (10 * precision * recall) / (9 * precision + recall)
        
        # Calculate fragmentation penalty (simplified)
        # Count chunks of consecutive matches
        chunks = 1
        prev_matched = False
        for i in sorted(hyp_matched):
            if prev_matched and i - 1 not in hyp_matched:
                chunks += 1
            prev_matched = True
        
        fragmentation = chunks / matches if matches > 0 else 0
        penalty = 0.5 * (fragmentation ** 3)
        
        # Final METEOR score
        meteor = f_mean * (1 - penalty) * 100
        
        return round(meteor, 2)
    
    def calculate_bertscore(self, reference, hypothesis):
        """
        Calculate BERTScore (simplified version using word overlap)
        
        Note: This is a simplified implementation. Real BERTScore requires:
        - BERT model for contextual embeddings
        - Cosine similarity between embeddings
        
        This version uses word overlap as a proxy.
        
        Args:
            reference: Reference translation
            hypothesis: Hypothesis translation
            
        Returns:
            Simplified BERTScore (0-100)
        """
        ref_tokens = set(self.tokenize(reference))
        hyp_tokens = set(self.tokenize(hypothesis))
        
        if not hyp_tokens or not ref_tokens:
            return 0.0
        
        # Calculate overlap-based similarity
        intersection = len(ref_tokens & hyp_tokens)
        union = len(ref_tokens | hyp_tokens)
        
        # Jaccard similarity as proxy
        if union == 0:
            similarity = 0.0
        else:
            similarity = intersection / union
        
        # Scale to 0-100
        score = similarity * 100
        
        return round(score, 2)
    
    def evaluate_all(self, reference, hypothesis):
        """
        Calculate all evaluation metrics
        
        Args:
            reference: Reference translation (original text)
            hypothesis: Hypothesis translation (translated text)
            
        Returns:
            Dictionary with all metric scores
        """
        if not reference or not hypothesis:
            return {
                'bleu': 0.0,
                'chrf': 0.0,
                'meteor': 0.0,
                'bertscore': 0.0,
                'error': 'Empty input'
            }
        
        try:
            bleu = self.calculate_bleu(reference, hypothesis)
            chrf = self.calculate_chrf(reference, hypothesis)
            meteor = self.calculate_meteor(reference, hypothesis)
            bertscore = self.calculate_bertscore(reference, hypothesis)
            
            return {
                'bleu': bleu,
                'chrf': chrf,
                'meteor': meteor,
                'bertscore': bertscore
            }
        except Exception as e:
            return {
                'bleu': 0.0,
                'chrf': 0.0,
                'meteor': 0.0,
                'bertscore': 0.0,
                'error': str(e)
            }


def main():
    """Test the evaluation metrics"""
    evaluator = TranslationEvaluator()
    
    # Test examples
    reference = "The cat is sitting on the mat"
    hypothesis = "A cat sits on the mat"
    
    print("Translation Evaluation Metrics Test")
    print("=" * 60)
    print(f"Reference:  {reference}")
    print(f"Hypothesis: {hypothesis}")
    print("=" * 60)
    
    metrics = evaluator.evaluate_all(reference, hypothesis)
    
    print(f"\nBLEU Score:      {metrics['bleu']:.2f}")
    print(f"ChrF Score:      {metrics['chrf']:.2f}")
    print(f"METEOR Score:    {metrics['meteor']:.2f}")
    print(f"BERTScore:       {metrics['bertscore']:.2f}")
    print("\nNote: Higher scores indicate better translation quality")
    print("=" * 60)


if __name__ == '__main__':
    main()