"""Text processing and cleaning module.

Handles text cleaning, normalization, and segmentation.
"""

import re
import string
from typing import List, Dict, Any, Tuple, Optional
import spacy

from src.exceptions import DependencyError


class TextProcessor:
    """Process and clean extracted text for NLP analysis."""

    def __init__(self, min_activity_length: int = 20, max_activity_length: int = 500, spacy_model: str = "en_core_web_sm"):
        """
        Initialize the text processor.

        Args:
            min_activity_length: Minimum word count for an activity
            max_activity_length: Maximum word count for an activity
            spacy_model: Name of spaCy model to load (default: en_core_web_sm)
        """
        self.min_activity_length = min_activity_length
        self.max_activity_length = max_activity_length
        self.spacy_model_name = spacy_model

        # Load spaCy model for sentence structure analysis
        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            # Fallback if model not installed
            self.nlp = None
            print(f"Warning: spaCy model '{spacy_model}' not found. Install with: python -m spacy download {spacy_model}")

        # Enhanced action verbs with priority levels
        self.priority_verbs = {
            # High priority - clear implementation actions (base forms)
            "implement", "deliver", "complete", "construct", "build",
            "establish", "create", "launch", "initiate", "introduce",
            "develop", "install", "upgrade", "renew", "refurbish",
            "purchase", "acquire", "commission", "open", "start",
            "appoint", "award", "grant", "fund", "construct",
            # Past tense forms
            "implemented", "delivered", "completed", "constructed", "built",
            "established", "created", "launched", "initiated", "introduced",
            "developed", "installed", "upgraded", "renewed", "refurbished",
            "purchased", "acquired", "commissioned", "opened", "started",
            "appointed", "awarded", "granted", "funded"
        }

        self.standard_verbs = {
            # Standard action verbs (base forms)
            "improve", "enhance", "expand", "upgrade", "design",
            "plan", "strategize", "manage", "coordinate", "facilitate",
            "support", "provide", "engage", "collaborate", "partner",
            "consult", "involve", "promote", "encourage", "enable",
            "empower", "strengthen", "maintain", "preserve", "protect",
            "conserve", "monitor", "evaluate", "assess", "prepare",
            "produce", "publish", "release", "communicate",
            "update", "review", "adopt", "approve", "endorse",
            # Past tense forms
            "improved", "enhanced", "expanded", "designed",
            "planned", "strategized", "managed", "coordinated", "facilitated",
            "supported", "provided", "engaged", "collaborated", "partnered",
            "consulted", "involved", "promoted", "encouraged", "enabled",
            "empowered", "strengthened", "maintained", "preserved", "protected",
            "conserved", "monitored", "evaluated", "assessed", "prepared",
            "produced", "published", "released", "communicated",
            "updated", "reviewed", "adopted", "approved", "endorsed"
        }

        self.weak_verbs = {
            # State-of-being/auxiliary verbs
            "was", "were", "is", "are", "been", "be", "being",
            "had", "has", "have",
            # Mental/cognitive verbs — base forms for spaCy lemma matching
            "consider", "considered", "review", "reviewed", "discuss", "discussed",
            "note", "noted", "acknowledge", "acknowledged",
            "recognize", "recognized", "identify", "identified",
            "analyze", "analyzed", "examine", "examined",
            # Passive/descriptive verbs
            "reflect", "reflected", "appear", "appeared", "seem", "seemed",
            "remain", "remained", "continue", "continued",
        }

    def is_model_loaded(self) -> bool:
        """Check if spaCy model was successfully loaded.

        Returns:
            True if spaCy model is loaded, False otherwise
        """
        return self.nlp is not None

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded spaCy model.

        Returns:
            Dictionary with model name, type, accuracy level, and loaded status
        """
        model_info = {
            "name": self.spacy_model_name,
            "loaded": self.nlp is not None,
            "type": "spacy"
        }

        # Determine accuracy level based on model name
        if "trf" in self.spacy_model_name:
            model_info["accuracy"] = "highest"
        elif "lg" in self.spacy_model_name:
            model_info["accuracy"] = "high"
        elif "md" in self.spacy_model_name:
            model_info["accuracy"] = "medium"
        else:
            model_info["accuracy"] = "standard"

        return model_info

    def clean_text(self, text: str, remove_headers: bool = True) -> str:
        """
        Clean extracted text by removing artifacts and normalizing.

        Args:
            text: Raw extracted text
            remove_headers: Whether to remove header/footer lines

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove headers and footers
        if remove_headers:
            lines = text.split('\n')
            cleaned_lines = []
            for line in lines:
                line_stripped = line.strip()
                if not self._is_header_footer(line_stripped):
                    cleaned_lines.append(line)
            text = '\n'.join(cleaned_lines)

        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n+', '\n\n', text)

        # Remove bullet points and numbering at start of lines
        text = re.sub(r'^\s*[•·\-–—*]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+[.):]\s+', '', text, flags=re.MULTILINE)

        return text.strip()

    def _is_header_footer(self, line: str) -> bool:
        """Check if a line is likely a header or footer."""
        if not line:
            return True

        # Common header/footer patterns
        patterns = [
            r'^\d+$',  # Just a number (page number)
            r'^\d+\s+of\s+\d+$',  # "X of Y"
            r'^page\s+\d+$',  # "Page X"
            r'^\d+\s*/\s*\d+$',  # "X/Y"
            r'^(?:annual\s+report|report\s+annual)$',  # "Annual Report"
            r'^\d{4}[-–/]\d{2,4}$',  # Year patterns
            r'^\d{4}\s+annual\s+report$',  # "2023 Annual Report"
            r'^annual\s+report\s+\d{4}$',  # "Annual Report 2023"
            r'^\d{4}[-–]\d{2}\s+annual\s+report$',  # "2022-23 Annual Report"
            r'^financial\s+(?:statements?|summary|report)',  # Financial headers
            r'^service\s+performance\s+indicators?',  # Performance headers
            r'^for\s+the\s+year\s+ended\s+\d+',  # "For the year ended..."
            r'^performance\s+statement',  # Performance statement
        ]

        for pattern in patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True

        # Check for line ending with page number (e.g., "Financial summary 42")
        # Exclude lines where the trailing number looks like a year (4-digit starting 19/20)
        if re.search(r'\w+.*?\d+\s*$', line) and len(line) < 80:
            words_before = re.sub(r'\d+\s*$', '', line).strip()
            if words_before:
                word_count = len(words_before.split())
                if 2 <= word_count <= 8:
                    # Skip if trailing number is a year (e.g. "... in 2023")
                    if re.search(r'(?:19|20)\d{2}\s*$', line):
                        return False
                    return True

        return False

    def segment_into_paragraphs(self, text: str) -> List[str]:
        """
        Segment text into paragraphs.

        Args:
            text: Cleaned text

        Returns:
            List of paragraph strings
        """
        if not text:
            return []

        # Split on double newlines (paragraph breaks)
        paragraphs = re.split(r'\n\s*\n', text)

        # Clean each paragraph - NO MERGING of short paragraphs
        # This prevents unrelated content from being combined
        paragraphs = [p.strip() for p in paragraphs if p.strip()]

        return paragraphs

    def _split_on_bullets(self, text: str) -> List[str]:
        """
        Split text on bullet point characters.

        Handles bullets embedded in text from PDF extraction issues.

        Args:
            text: Text that may contain embedded bullets

        Returns:
            List of text segments split by bullets
        """
        # Split on various bullet characters
        # Using a pattern that catches bullet chars with optional surrounding whitespace
        bullet_pattern = r'\s*[•·\-\–—*•]\s+'
        segments = re.split(bullet_pattern, text)

        # Clean and filter
        segments = [s.strip() for s in segments if s.strip()]
        return segments

    def segment_into_sentences(self, text: str, split_on_bullets: bool = True) -> List[str]:
        """
        Segment text into sentences.

        Uses simple heuristics with optional bullet point splitting.

        Args:
            text: Text to segment
            split_on_bullets: Whether to also split on bullet characters

        Returns:
            List of sentences
        """
        if not text:
            return []

        # First split on bullets if requested
        if split_on_bullets:
            bullet_segments = self._split_on_bullets(text)
        else:
            bullet_segments = [text]

        all_sentences = []

        for segment in bullet_segments:
            # Common abbreviations that shouldn't end sentences
            abbreviations = ['dr', 'mr', 'mrs', 'ms', 'prof', 'sr', 'jr', 'st', 'ave',
                            'blvd', 'rd', 'inc', 'ltd', 'corp', 'llc', 'eg', 'ie',
                            'etc', 'vol', 'vols', 'pg', 'pp', 'ed', 'eds', 'no', 'nos',
                            'fig', 'figs', 'et al']

            # Replace periods in abbreviations temporarily
            text_clean = segment
            for abbr in abbreviations:
                text_clean = re.sub(rf'\b{abbr}\.', f'{abbr}█', text_clean, flags=re.IGNORECASE)

            # Split on sentence endings
            sentences = re.split(r'[.!?]+\s+', text_clean)

            # Restore abbreviation periods
            sentences = [s.replace('█', '.') for s in sentences]

            # Clean and filter
            sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            all_sentences.extend(sentences)

        return all_sentences

    def _smart_sentence_join(self, sentences: List[str]) -> List[str]:
        """
        Intelligently join related sentences that form a single activity.

        Joins sentences if:
        - Second sentence starts with reference words (This, It, The, These, Those)
        - Second sentence starts with continuation words (and, or, but, also)
        - Combined length is still under max_activity_length

        Args:
            sentences: List of sentences

        Returns:
            List of joined sentence groups
        """
        if not sentences:
            return []

        # Words that indicate the sentence depends on previous context
        reference_words = {'this', 'it', 'the', 'these', 'those', 'which', 'that', 'such'}

        # Words that indicate continuation from previous sentence
        continuation_words = {'and', 'or', 'but', 'also', 'additionally', 'furthermore',
                             'moreover', 'therefore', 'thus', 'consequently', 'as', 'with',
                             'however', 'further', 'similarly', 'likewise', 'meanwhile',
                             'subsequently', 'alternatively', 'nevertheless', 'nonetheless',
                             'otherwise', 'instead', 'besides', 'accordingly'}

        # Subordinate conjunctions that typically start dependent clauses
        # These indicate the sentence is incomplete without previous context
        dependent_clause_starters = {'given', 'although', 'while', 'whereas', 'since',
                                      'unless', 'until', 'whether', 'once', 'though',
                                      'because', 'after', 'before', 'when', 'if',
                                      'even', 'despite', 'notwithstanding', 'providing',
                                      'assuming', 'supposing', 'granted', 'albeit'}

        joined = []
        current = sentences[0]

        for i in range(1, len(sentences)):
            next_sent = sentences[i]

            # Check if next sentence starts with a reference/continuation word
            next_lower = next_sent.lower().lstrip()
            first_word = next_lower.split()[0] if next_lower.split() else ''

            should_join = False

            # Join if starts with reference word (demonstratives, pronouns)
            if first_word in reference_words:
                should_join = True

            # Join if starts with continuation/conjunctive words
            if first_word in continuation_words:
                should_join = True

            # Join if starts with subordinate conjunction (dependent clause)
            if first_word in dependent_clause_starters:
                should_join = True

            # Check combined length
            combined_words = len(current.split()) + len(next_sent.split())
            if combined_words > self.max_activity_length:
                should_join = False

            if should_join:
                current = current + " " + next_sent
            else:
                joined.append(current)
                current = next_sent

        # Don't forget the last one
        joined.append(current)

        return joined

    def _iter_candidate_groups(self, text: str):
        """
        Shared segmentation pipeline: paragraph → sentence → smart join.

        Yields (text, word_count) tuples for every candidate group.
        Single source of truth for both BERT and spaCy extraction paths.
        """
        segments = self.segment_into_paragraphs(text)

        for segment in segments:
            word_count = len(segment.split())
            if word_count < self.min_activity_length:
                continue

            sentences = self.segment_into_sentences(segment, split_on_bullets=True)
            joined_groups = self._smart_sentence_join(sentences)

            for group in joined_groups:
                group_wc = len(group.split())

                if group_wc < self.min_activity_length:
                    continue
                if group_wc > self.max_activity_length:
                    individual_sentences = self.segment_into_sentences(group, split_on_bullets=False)
                    for sent in individual_sentences:
                        sent_wc = len(sent.split())
                        if self.min_activity_length <= sent_wc <= self.max_activity_length:
                            yield sent, sent_wc
                    continue

                yield group, group_wc

    def extract_candidate_sentences(self, text: str) -> List[str]:
        """
        Run Phase 1 only: segmentation + cleaning filters.

        Returns candidate sentences that pass all cleaning filters but have NOT
        been classified yet (no spaCy/BERT validation). These are the raw inputs
        for Phase 2 classification.
        """
        candidates = []
        for candidate_text, _ in self._iter_candidate_groups(text):
            if self._passes_cleaning_filters(candidate_text):
                candidates.append(candidate_text)
        return candidates

    def _passes_cleaning_filters(self, text: str) -> bool:
        """Check if text passes all Phase 1 cleaning filters."""
        if self._looks_like_table(text):
            return False
        if self._is_mostly_numbers(text):
            return False
        if not self._has_meaningful_content(text):
            return False
        if self._is_structural_content(text):
            return False
        if self._is_fragmented_start(text):
            return False
        if self._is_non_activity_content(text):
            return False
        if self._is_generic_text(text):
            return False
        return True

    def extract_activities(
        self,
        text: str,
        use_heuristics: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Extract potential activity descriptions from text.

        Uses shared _iter_candidate_groups() for segmentation, then validates
        each candidate through _create_activity (cleaning filters + spaCy structure check).
        """
        activities = []
        for candidate_text, _ in self._iter_candidate_groups(text):
            activity = self._create_activity(candidate_text, use_heuristics)
            if activity:
                activities.append(activity)
        return activities

    def _create_activity(self, text: str, use_heuristics: bool) -> Optional[Dict[str, Any]]:
        """Create an activity dictionary from text if it passes strict filters."""
        # Skip if looks like a table
        if self._looks_like_table(text):
            return None

        # Skip if mostly numbers
        if self._is_mostly_numbers(text):
            return None

        # Skip if no meaningful content
        if not self._has_meaningful_content(text):
            return None

        # Skip structural content (TOC, headers, etc.)
        if self._is_structural_content(text):
            return None

        # Skip if starts with a fragment indicator
        if self._is_fragmented_start(text):
            return None

        # Skip non-activity content (financial, personnel, audit)
        if self._is_non_activity_content(text):
            return None

        # Use spaCy for detailed analysis if available
        if self.nlp is not None and use_heuristics:
            validation_result = self._validate_sentence_structure(text)

            # Strict requirement: Must have valid sentence structure
            if not validation_result['is_valid_activity']:
                return None

            # Additional check: Must have strong action verb (not just weak verbs)
            if not validation_result['has_action_verb']:
                return None

            # Build activity with detailed metadata
            activity = {
                "text": text,
                "word_count": len(text.split()),
                "confidence": validation_result['confidence'],
                "has_action_verb": validation_result['has_action_verb'],
                "is_active_voice": validation_result['is_active_voice'],
                "has_subject": validation_result['has_subject'],
                "has_object": validation_result['has_object'],
                "is_completed": validation_result['is_completed'],
                "specificity_score": validation_result['specificity_score'],
                "main_verb": validation_result['main_verb'],
                "validation_details": validation_result['details']
            }

            return activity
        else:
            # Fallback to simple heuristic when spaCy not available
            return self._create_simple_activity(text, use_heuristics)

    def has_action_verb_quick(self, text: str) -> bool:
        """
        Regex-based action verb check — no spaCy needed.
        Returns True if text contains at least one priority or standard verb as a whole word.
        Used as lightweight guard for BERT classifier results.
        """
        text_lower = text.lower()
        for verb in self.priority_verbs:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                return True
        for verb in self.standard_verbs:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                return True
        return False

    def _validate_sentence_structure(self, text: str) -> Dict[str, Any]:
        """
        Validate sentence structure using spaCy to determine if it's a proper activity.

        Checks for:
        - Subject-verb-object structure
        - Active voice (or clear agent)
        - Past/completed tense
        - Specificity (what, where, for whom)
        - Main verb is an action verb

        Returns:
            Dictionary with validation results and confidence score
        """
        doc = self.nlp(text)

        # Get the root verb (main verb of the sentence)
        root = None
        for token in doc:
            if token.dep_ == "ROOT" and token.pos_ == "VERB":
                root = token
                break

        # Criteria tracking
        criteria = {
            'has_root_verb': root is not None,
            'has_subject': False,
            'has_object': False,
            'is_active_voice': False,
            'is_completed': False,
            'is_priority_verb': False,
            'is_standard_verb': False,
            'has_agent': False,
            'has_specificity': False,
            'not_weak_verb': True
        }

        if not root:
            return {
                'is_valid_activity': False,
                'confidence': 0.0,
                'details': criteria
            }

        # Analyze sentence structure
        subject_tokens = []
        object_tokens = []
        agent_tokens = []

        for token in doc:
            # Find subject
            if token.dep_ in ('nsubj', 'nsubjpass'):
                subject_tokens.append(token)
                criteria['has_subject'] = True

            # Find object
            if token.dep_ in ('dobj', 'pobj', 'attr', 'oprd'):
                object_tokens.append(token)
                criteria['has_object'] = True

            # Check for agent (in passive constructions)
            if token.dep_ == 'agent':
                agent_tokens.append(token)
                criteria['has_agent'] = True

        # Check voice
        if root.dep_ == 'ROOT':
            # Active voice: subject performs the action
            if any(t.dep_ == 'nsubj' for t in subject_tokens):
                criteria['is_active_voice'] = True
            # Passive voice with agent (e.g., "was built by Council")
            elif any(t.dep_ == 'nsubjpass' for t in subject_tokens) and agent_tokens:
                criteria['is_active_voice'] = True  # Treat as active-equivalent

        # Check verb type
        lemma = root.lemma_.lower()
        criteria['is_priority_verb'] = lemma in self.priority_verbs
        criteria['is_standard_verb'] = lemma in self.standard_verbs
        criteria['not_weak_verb'] = lemma not in self.weak_verbs

        # Check tense - prefer past/completed
        if root.tag_ in ('VBD', 'VBN'):  # Past tense or past participle
            criteria['is_completed'] = True
        elif root.tag_ in ('VB', 'VBP', 'VBZ') and any(t.text.lower() in ['has', 'have', 'had'] for t in doc if t.i < root.i):
            # Present perfect: has completed, have delivered
            criteria['is_completed'] = True

        # Check specificity - must have location, beneficiary, or quantifiable object
        specificity_indicators = [
            'for', 'in', 'at', 'with', 'to',  # Prepositions
            'community', 'residents', 'people', 'families', 'businesses',
            'area', 'region', 'town', 'city', 'shire', 'municipal',
            'road', 'street', 'park', 'facility', 'center', 'service'
        ]

        prep_count = sum(1 for token in doc if token.pos_ == 'ADP')
        specificity_hits = sum(1 for word in specificity_indicators if word in text.lower())

        # Must have at least 2 prepositional phrases or specific references
        criteria['has_specificity'] = prep_count >= 2 or specificity_hits >= 1

        # Calculate multi-criteria score
        confidence = 0.0

        # REQUIRED criteria (must pass these)
        if not criteria['has_root_verb']:
            confidence = 0.0
        elif not criteria['has_subject']:
            confidence = 0.0
        elif not criteria['has_object'] and not criteria['has_specificity']:
            # Can have no direct object if has specificity (e.g., "met with community groups")
            confidence = 0.0
        elif not criteria['not_weak_verb']:
            confidence = 0.1  # Very low for weak verbs
        else:
            # Calculate confidence based on criteria
            confidence = 0.5  # Base for passing required criteria

            # Boost for active voice
            if criteria['is_active_voice']:
                confidence += 0.1

            # Boost for completed actions
            if criteria['is_completed']:
                confidence += 0.15

            # Boost for priority verbs
            if criteria['is_priority_verb']:
                confidence += 0.2
            elif criteria['is_standard_verb']:
                confidence += 0.1

            # Boost for specificity
            if criteria['has_specificity']:
                confidence += 0.1

        # Validate the root verb is a real word (not symbols like bullets)
        has_valid_verb = root and root.is_alpha and len(root.text) > 1

        # Determine if valid activity
        is_valid = (
            criteria['has_root_verb'] and
            has_valid_verb and
            criteria['has_subject'] and
            (criteria['has_object'] or criteria['has_specificity']) and
            criteria['not_weak_verb'] and
            confidence >= 0.5  # Minimum confidence threshold
        )

        return {
            'is_valid_activity': is_valid,
            'confidence': round(min(confidence, 1.0), 2),
            'has_action_verb': criteria['is_priority_verb'] or criteria['is_standard_verb'],
            'is_active_voice': criteria['is_active_voice'],
            'has_subject': criteria['has_subject'],
            'has_object': criteria['has_object'],
            'is_completed': criteria['is_completed'],
            'specificity_score': prep_count,
            'main_verb': root.text.lower() if root else None,
            'details': criteria
        }

    def _create_simple_activity(self, text: str, use_heuristics: bool) -> Optional[Dict[str, Any]]:
        """Fallback activity creation without spaCy."""
        confidence = 1.0

        if use_heuristics:
            # Check for priority verbs
            has_priority = any(verb in text.lower() for verb in self.priority_verbs)
            has_standard = any(verb in text.lower() for verb in self.standard_verbs)

            if has_priority:
                confidence = 0.9
            elif has_standard:
                confidence = 0.7
            else:
                confidence = 0.5

            # Penalty for weak verbs
            has_weak = any(verb in text.lower() for verb in self.weak_verbs)
            if has_weak and not (has_priority or has_standard):
                confidence = 0.3

        return {
            "text": text,
            "word_count": len(text.split()),
            "confidence": min(confidence, 1.0),
            "has_action_verb": confidence >= 0.7,
            "is_active_voice": None,  # Can't detect without spaCy
            "has_subject": None,
            "has_object": None,
            "is_completed": None,
            "specificity_score": None,
            "main_verb": None,
            "validation_details": {"fallback": True}
        }

    def _looks_like_table(self, text: str) -> bool:
        """Check if text looks like a table row."""
        # High proportion of numbers and special characters (tightened from 0.3)
        digits = sum(c.isdigit() for c in text)
        total_chars = len(text.replace(' ', ''))
        if total_chars > 0 and digits / total_chars > 0.15:
            return True

        # Multiple pipe or tab characters
        if text.count('|') >= 2 or text.count('\t') >= 2:
            return True

        # Multiple asterisks (footnotes in tables) - tightened threshold
        if text.count('*') >= 3:
            return True

        # Multiple percentage signs (table data)
        if text.count('%') >= 2:
            return True

        # Repeated year patterns (award listings like "2025 winners 2024 winners")
        year_matches = re.findall(r'\b(19|20)\d{2}\b', text)
        if len(year_matches) >= 3:
            return True

        # Multiple proper names in sequence (award list pattern)
        if text.count('Award') >= 2 or text.count('Winner') >= 2:
            return True

        # Section markers (financial tables)
        if text.count('§') >= 2:
            return True

        # Financial table pattern: year sequences like "2025 2024 $"
        if re.search(r'\b(19|20)\d{2}\b.*\b(19|20)\d{2}\b.*\$', text):
            return True

        # Currency unit patterns like "$ '000"
        if "$ '000" in text or "000 $" in text:
            return True

        return False

    def _is_mostly_numbers(self, text: str) -> bool:
        """Check if text is mostly numbers."""
        words = text.split()
        if not words:
            return True

        # Count number-like words (including currency symbols and table markers)
        def is_number_like(w):
            cleaned = w.replace(',', '').replace('.', '').replace('$', '').replace('%', '').replace('*', '').replace('|', '').replace('+', '').replace('-', '')
            return cleaned.isdigit()

        number_words = sum(1 for w in words if is_number_like(w))
        return number_words / len(words) > 0.35  # Tightened from 0.5

    def _has_meaningful_content(self, text: str) -> bool:
        """Check if text has meaningful content."""
        # Must have at least some alphabetic characters (tightened from 10)
        alpha_count = sum(c.isalpha() for c in text)
        if alpha_count < 20:
            return False

        # Must have some real words (not just codes/numbers) - tightened
        words = text.split()
        real_words = sum(1 for w in words if len(w) > 2 and w.isalpha())
        return real_words >= 5  # Tightened from 3

    def _is_fragmented_start(self, text: str) -> bool:
        """
        Check if text starts with a word indicating it's a sentence fragment.

        Returns True if the text appears to be a dependent clause or fragment
        that should be joined with previous context.
        """
        text_lower = text.lower().lstrip()
        first_word = text_lower.split()[0] if text_lower.split() else ''

        # Subordinate conjunctions that typically start dependent clauses
        dependent_starters = {
            'given', 'although', 'while', 'whereas', 'since', 'unless', 'until',
            'whether', 'once', 'though', 'because', 'after', 'before', 'when', 'if',
            'even', 'despite', 'notwithstanding', 'providing', 'assuming',
            'supposing', 'granted', 'albeit'
        }

        # Demonstratives that need antecedent
        demonstratives = {'this', 'these', 'those', 'such'}

        # Check for dependent clause starters
        if first_word in dependent_starters:
            return True

        # Check for demonstratives (but allow if followed by "is", "was", etc.)
        # e.g., "This is a project" is okay, "This includes..." might need context
        if first_word in demonstratives:
            # Check if it's a complete sentence
            # "This includes..." needs previous context
            # "This is..." can stand alone
            words = text_lower.split()
            if len(words) > 1:
                second_word = words[1]
                # "This/these includes/includes/are/was/were" usually needs context
                if second_word in {'includes', 'include', 'includes:', 'include:'}:
                    return True

        return False

    def _is_generic_text(self, text: str) -> bool:
        """
        Check if text is generic/vague — lacks both council context and SDG relevance.

        Targets the top remaining quality issue: sentences with action verbs but no
        concrete council or SDG connection. Returns True if text should be filtered.
        """
        text_lower = text.lower()

        # Has a priority verb? Keep it.
        for verb in self.priority_verbs:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                return False

        # Has council context?
        has_council = any(w in text_lower for w in self._COUNCIL_WORDS)
        has_service = any(s in text_lower for s in self._COUNCIL_SERVICES)
        if has_council or has_service:
            return False

        # Has SDG-relevant terms?
        if any(term in text_lower for term in self._SDG_RELEVANT_TERMS):
            return False

        # Has quantitative outcome?
        for pat in self._OUTCOME_PATTERNS:
            if pat.search(text):
                return False

        # Has non-council markers? (definitely keep — we just don't want council context for these)
        if any(m.lower() in text_lower for m in self._NON_COUNCIL_MARKERS):
            return False

        # Text has a standard verb but no council/service/SDG/outcome context → generic filler
        for verb in self.standard_verbs:
            if re.search(r'\b' + re.escape(verb) + r'\b', text_lower):
                return True

        # No standard verb either, but also no context at all → also generic
        return True

    def _is_non_activity_content(self, text: str) -> bool:
        """
        Check if text is non-activity content (descriptive financial, audit reports, etc.).

        Returns True if the text should be filtered as it's purely descriptive
        financial/accounting content rather than an implemented action.

        NOTE: Governance activities (establishing committees, appointments, policies)
        ARE considered activities and should NOT be filtered here.
        """
        text_lower = text.lower()

        # Purely descriptive financial statement text (NOT governance activities)
        descriptive_financial_patterns = [
            # Financial statement descriptions (not the establishment of them)
            r'\bthese\s+(past\s+service\s+)?(general\s+purpose\s+)?financial\s+statements?\s+(have\s+been\s+)?(prepared|are)\b',
            r'\bfinancial\s+statements?\s+have\s+been\s+prepared\s+in\s+accordance\s+with\b',
            r'\bnotes\s+to\s+the\s+financial\s+statements\b',
            r'\babout\s+the\s+notes\s+to\s+the\s+financial\s+statements\b',
            r'\bcontingencies?\s*\(continued\)\b',
            r'\baustralian\s+accounting\s+standards?\b',
            r'\bjudgements?\s+and\s+assumptions\s+made\s+by\s+management\b',
            r'\bmaterial\s+misstatements?\s+are\s+considered\s+material\s+if\b',
            r'\ball\s+(assets|liabilities)\s+for\s+which\s+fair\s+value\s+is\s+measured\b',
            r'\bfair\s+value\s+hierarchy\b',
            r'\baccrued\s+liabilities?\s+are\s+(used|assessed|maintained)\b',
            r'\bpast\s+service\s+contributions?\s+are\s+used\b',
            r'\bfunding\s+position\s+for\s+(the\s+)?accrued\s+liabilities\b',
            r'\bdefined\s+benefit\s+(scheme|superannuation|liabilities?)\b',
            r'\bvision\s+super\s+(has\s+advised|advises)\b',
            r'\bactuarial\s+(investigation|assessment|report)\s+(was\s+)?(held|conducted|completed)\b',
            # Service cost tables
            r'\bservice\s+cost\s*\$\d{1,3}(,\d{3})*\.\d{2}\b',
        ]

        # Audit report descriptions (not the creation of audit committees)
        descriptive_audit_patterns = [
            # Auditor's report text (not the establishment of audit function)
            r'\bindependent\s+auditor["\']?s?\s+report\s+(to\s+the\s+councillors?)\b',
            r'\b(independent\s+)?auditor["\']?s?\s+report\s*[:\-]\s*\bto\s+the\b',
            r'\bconducted\s+my\s+audit\s+in\s+accordance\s+with\s+the\s+audit\s+act\b',
            r'\bbasis\s+(for\s+opinion|of\s+opinion)\s*[:\-]\s*\bI\s+have\s+conducted\b',
            r'\bopinion\s+on\s+the\s+financial\s+statements?\b',
            r'\bmisstatements?\s+are\s+considered\s+material\s+if\b',
            # Auditor describing their work
            r'\bI\s+communicate\s+with\s+the\s+councillors\s+regarding\b',
            r'\bkey\s+areas\s+of\s+focus\s+for\s+the\s+audit\s+committee\s+during\s+the\s+year\s+were\b',
            r'\bthe\s+planned\s+scope\s+and\s+timing\s+of\s+the\s+audit\b',
            # Strategic audit plan as a document (not creation of plan)
            r'\ba\s+risk\s+based\s+four-year\s+strategic\s+internal\s+audit\s+plan\s+is\s+revised\b',
            # Internal audit function description
            r'\bcouncil["\']?s?\s+internal\s+audit\s+function\s+provides\b',
            # Auditor-General description
            r'\bparliament\s+promotes\s+independence\s+by\s+ensuring\s+the\s+auditor-general\b',
        ]

        # Legal/Compliance descriptive text (not compliance activities)
        descriptive_compliance_patterns = [
            # Legal sections describing requirements (not actions to comply)
            r'\bin\s+accordance\s+with\s+section\s+\d+[a-z]*\s+(and\s+\d+[a-z]*)?\s+of\s+the\s+\w+\s+act\b',
            r'\bthe\s+\w+\s+act\s+\d{4}\s+(provides|states|requires)\s+(that|for|a)\s+council\b',
            r'\ba\s+council\s+that\s+is\s+a\s+(collecting|development)\s+agency\s+must\b',
            r'\bthe\s+report\s+must\s+be\s+published\s+in\b',
            r'\bsection\s+\d+\s+of\s+the\s+\w+\s+act\s+\d{4}\s+provides\s+for\b',
            r'\bperformance\s+statement\s+certification\b',
            r'\bin\s+my\s+opinion\s*,?\s+the\s+(accompanying\s+)?(performance\s+statement|schedule)\s+is\s+prepared\b',
            r'\bthe\s+report\s+also\s+includes\s+some\s+information\s+that\s+is\s+prescribed\b',
            r'\boperational\s+plan\s*\(\s*combined\s+document\s*\)\s+is\s+designed\s+as\b',
        ]

        # Purely descriptive personnel listings (not appointments)
        descriptive_personnel_patterns = [
            # Staff lists without action verbs
            r'\b(manager|executive|officer)\s+[a-z\s]+\s+(public\s+and\s+environmental\s+health|strategic\s+planning)\s*$',
            r'\bofficers?\s+reporting\s+directly\s+to\b',
            r'\borganisational\s+structure\s+(at|during)\s+(30\s+june|\d{4})\b',
            r'\bsenior\s+officers?\s+reporting\b',
            r'\b(local\s+)?laws?\s+officer\s+(completed|finished)\s+training\b',
            # Descriptive org chart text
            r'\bdirector\s+(of\s+)?(assets|customer|community|engineering)\s+[a-z\s]+director\b',
        ]

        # Descriptive-only patterns (no action, just description)
        descriptive_only_patterns = [
            # Pure descriptions
            r'^the\s+(council|shire|municipality|community|region|area)\s+is\s+(a|located|situated|in)\b',
            r'^there\s+(is|was|were)\s+(no|not)\s+\w+\s+(that|which)\b',
            r'\bthis\s+consultation\s+was\s+the\s+first\s+step\b',
            # National Competition Policy description
            r'\bcouncil\s+has\s+adopted\s+the\s+principle\s+of\s+[\'"]competitive\s+neutrality[\'"]',
        ]

        all_patterns = (descriptive_financial_patterns +
                     descriptive_audit_patterns +
                     descriptive_compliance_patterns +
                     descriptive_personnel_patterns +
                     descriptive_only_patterns)

        for pattern in all_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _is_structural_content(self, text: str) -> bool:
        """
        Check if text is structural/metadata content (TOC, headers, etc.).

        Returns True if the text appears to be structural content that should be filtered.
        """
        text_lower = text.lower()
        words = text.split()

        # Check for TOC content
        toc_markers = ['contents', 'table of contents', 'page', 'introduction', 'section']
        if any(marker in text_lower for marker in toc_markers):
            # Check for multiple page numbers (TOC pattern)
            page_numbers = re.findall(r'\b\d+\s*$', text, re.MULTILINE)
            if len(page_numbers) >= 2:
                return True

        # Check for header with embedded page numbers (e.g., "Financial summary 2022-2023 42")
        # Pattern: text followed by year pattern followed by number
        if re.search(r'\w+.*?20\d{2}[-–]?\d{0,2}\s+\d+\s*$', text):
            return True

        # Check if mostly uppercase (likely a header)
        alpha_chars = [c for c in text if c.isalpha()]
        if alpha_chars:
            upper_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)
            if upper_ratio > 0.7:
                return True

        # Check for URL/website patterns
        url_patterns = [
            r'https?://\S+',
            r'www\.\S+',
            r'\S+\.gov\.au',
            r'\S+\.com\.au',
            r'\S+\.org\.au',
        ]
        for pattern in url_patterns:
            if re.search(pattern, text_lower):
                return True

        # Check for disclaimer text
        disclaimer_markers = ['disclaimer', 'this report is provided for information', 'does not purport to be complete']
        if any(marker in text_lower for marker in disclaimer_markers):
            return True

        # Check for excessive year patterns (TOC listings)
        year_matches = re.findall(r'\b(19|20)\d{2}\b', text)
        if len(year_matches) >= 3:
            return True

        return False

    def get_validation_stats(self, texts: List[str]) -> Dict[str, Any]:
        """
        Get statistics about text validation for debugging.

        Args:
            texts: List of text strings to analyze

        Returns:
            Dictionary with validation statistics
        """
        if not self.nlp:
            raise DependencyError("spaCy not available. Install with: pip install spacy && python -m spacy download en_core_web_sm")

        stats = {
            "total_texts": len(texts),
            "valid_activities": 0,
            "rejected": {
                "no_root_verb": 0,
                "no_subject": 0,
                "no_object_or_specificity": 0,
                "weak_verb": 0,
                "low_confidence": 0
            },
            "criteria_breakdown": {
                "has_root_verb": 0,
                "has_subject": 0,
                "has_object": 0,
                "is_active_voice": 0,
                "is_completed": 0,
                "is_priority_verb": 0,
                "has_specificity": 0
            }
        }

        for text in texts:
            result = self._validate_sentence_structure(text)

            if result['is_valid_activity']:
                stats["valid_activities"] += 1
            else:
                details = result['details']
                if not details['has_root_verb']:
                    stats["rejected"]["no_root_verb"] += 1
                elif not details['has_subject']:
                    stats["rejected"]["no_subject"] += 1
                elif not (details['has_object'] or details['has_specificity']):
                    stats["rejected"]["no_object_or_specificity"] += 1
                elif not details['not_weak_verb']:
                    stats["rejected"]["weak_verb"] += 1
                else:
                    stats["rejected"]["low_confidence"] += 1

            # Count criteria
            for criterion in stats["criteria_breakdown"]:
                if result['details'].get(criterion, False):
                    stats["criteria_breakdown"][criterion] += 1

        return stats

    def normalize_text(self, text: str) -> str:
        """
        Normalize text for comparison.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        if not text:
            return ""

        # Lowercase
        text = text.lower()

        # Remove punctuation except hyphens
        text = re.sub(r'[^\w\s-]', ' ', text)

        # Normalize whitespace
        text = ' '.join(text.split())

        return text

    # Terms indicating council context
    _COUNCIL_WORDS = {
        "council", "councils", "councillor", "councillors",
        "shire", "city", "municipality", "local government",
        "we", "our", "mayor", "lord mayor",
    }

    _COUNCIL_SERVICES = {
        "library", "libraries", "waste", "recycling", "roads",
        "childcare", "planning permit", "building permit", "parking",
        "pool", "sport", "park", "facility", "facilities",
        "aged care", "community center", "community centre",
        "wastewater", "sewer", "drainage", "footpath", "street",
        "playground", "reserve", "hall", "venue", "service",
    }

    _NON_COUNCIL_MARKERS = {
        "NBN", "Telstra", "state government", "federal government",
        "Australian government", "NSW government", "Victorian government",
        "Queensland government", "Services Australia", "Centrelink",
    }

    # SDG-relevant keywords (cached at class level)
    _SDG_RELEVANT_TERMS = [
        "sustainable", "climate", "environment", "community", "health",
        "education", "infrastructure", "economic", "social", "partnership",
        "innovation", "biodiversity", "renewable", "waste", "recycling",
        "wellbeing", "inclusion", "diversity", "accessibility", "conservation"
    ]

    # Pre-compiled regex for quantitative outcomes
    _OUTCOME_PATTERNS = [
        re.compile(r'\d+\s*(?:percent|%|people|households|residents|jobs|tonnes|units)', re.IGNORECASE),
        re.compile(r'\$[\d,]+(?:\.\d{2})?', re.IGNORECASE),
        re.compile(r'(?:increased|decreased|reduced|improved)\s+by\s+\d+', re.IGNORECASE),
    ]

    def score_relevance(self, text: str) -> float:
        """
        Score text for SDG relevance based on keywords, specificity, and structure.
        Pure text features — no model dependency. Returns 0-1.
        """
        text_lower = text.lower()
        words = text.split()
        if not words:
            return 0.0

        score = 0.3  # neutral base

        # SDG keyword bonus
        sdg_hits = sum(1 for term in self._SDG_RELEVANT_TERMS if term in text_lower)
        score += min(sdg_hits * 0.04, 0.16)

        # Quantitative outcome bonus
        for pat in self._OUTCOME_PATTERNS:
            if pat.search(text):
                score += 0.06
                break

        # Specificity bonus (prepositions + concrete targets)
        specificity_markers = [
            'for', 'in', 'at', 'with', 'to',
            'community', 'residents', 'people', 'families',
            'area', 'region', 'town', 'city'
        ]
        specificity_count = sum(1 for m in specificity_markers if m in text_lower)
        score += min(specificity_count * 0.02, 0.08)

        # Number-heavy penalty (likely table or financial data)
        number_ratio = sum(1 for w in words if any(c.isdigit() for c in w)) / len(words)
        if number_ratio > 0.25:
            score *= 0.6
        elif number_ratio > 0.15:
            score *= 0.8

        return round(min(score, 1.0), 4)

    def detect_section_type(self, text: str) -> str:
        """
        Detect what type of section the text belongs to.

        Returns:
            Section type label
        """
        text_lower = text.lower()

        # Environmental sections
        env_keywords = ['environment', 'sustainability', 'climate', 'carbon', 'green',
                       'conservation', 'biodiversity', 'ecosystem', 'renewable']
        if any(kw in text_lower for kw in env_keywords):
            return 'environmental'

        # Social/Community sections
        social_keywords = ['community', 'social', 'health', 'wellbeing', 'education',
                          'culture', 'recreation', 'sport', 'youth', 'elderly',
                          'disability', 'indigenous', 'aboriginal']
        if any(kw in text_lower for kw in social_keywords):
            return 'social'

        # Economic sections
        econ_keywords = ['economic', 'business', 'employment', 'jobs', 'tourism',
                        'investment', 'development', 'growth', 'enterprise']
        if any(kw in text_lower for kw in econ_keywords):
            return 'economic'

        # Infrastructure sections
        infra_keywords = ['infrastructure', 'roads', 'buildings', 'facilities',
                         'transport', 'utilities', 'maintenance', 'construction']
        if any(kw in text_lower for kw in infra_keywords):
            return 'infrastructure'

        # Governance sections
        gov_keywords = ['governance', 'council', 'meeting', 'policy', 'strategy',
                       'plan', 'report', 'performance', 'audit']
        if any(kw in text_lower for kw in gov_keywords):
            return 'governance'

        return 'general'

    def get_summary_stats(self, text: str) -> Dict[str, Any]:
        """Get summary statistics for text."""
        if not text:
            return {
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "avg_word_length": 0,
                "avg_sentence_length": 0
            }

        words = text.split()
        sentences = self.segment_into_sentences(text)
        paragraphs = self.segment_into_paragraphs(text)

        avg_word_length = sum(len(w) for w in words) / len(words) if words else 0
        avg_sentence_length = len(words) / len(sentences) if sentences else 0

        return {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "avg_word_length": round(avg_word_length, 2),
            "avg_sentence_length": round(avg_sentence_length, 2)
        }
