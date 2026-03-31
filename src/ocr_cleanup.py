"""OCR text cleanup module.

Cleans up common OCR artifacts from scanned PDFs, specifically:
- Single-character internal spaces (e.g., "wo rds" -> "words")
- Common OCR substitutions and misreads
"""

import re
from typing import Set


class OCRCleanup:
    """Clean OCR artifacts from scanned PDF text."""

    # Common OCR artifacts: patterns where OCR inserted spaces between characters
    # These are single characters that OCR often misplaces spaces around
    OCR_SPACE_CHARS = {
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm',
        'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z',
        'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
        'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    }

    # Common prepositions/articles that OCR breaks
    OCR_BROKEN_WORDS = {
        'o f': 'of', 't h e': 'the', 'a n d': 'and', 'i n': 'in',
        't o': 'to', 'a s': 'as', 'i t': 'it', 'i s': 'is', 'w a s': 'was',
        'f o r': 'for', 'w i t h': 'with', 't h a t': 'that', 'h a s': 'has',
        'h a v e': 'have', 'w h i c h': 'which', 't h e y': 'they',
        't h e i r': 'their', 'w o u l d': 'would', 'c o u l d': 'could',
        's h o u l d': 'should', 'o n': 'on', 'a t': 'at', 'b e': 'be',
        'b y': 'by', 'n o t': 'not', 'b u t': 'but', 'w h a t': 'what',
        'w h e n': 'when', 'w h e r e': 'where', 'h o w': 'how', 'w h o': 'who',
        'w i l l': 'will', 'f r o m': 'from', 't h e r e': 'there',
        'w o u l d': 'would', 't h i s': 'this', 't h a t': 'that',
        'a r e': 'are', 'w e r e': 'were', 'h a d': 'had', 'd i d': 'did',
        'd o': 'do', 'd o e s': 'does', 'c a n': 'can', 'm a y': 'may',
        'm i g h t': 'might', 'm u s t': 'must', 's h a l l': 'shall',
        'a b l e': 'able', 'g o i n g': 'going', 'k n o w': 'know',
        't h i n k': 'think', 'l o o k': 'look', 't a k e': 'take',
        'g e t': 'get', 'm a k e': 'make', 'c o m e': 'come', 'g o': 'go',
        's e e': 'see', 'u s e': 'use', 'f i n d': 'find', 'g i v e': 'give',
        't e l l': 'tell', 't r y': 'try', 'a s k': 'ask', 'w o r k': 'work',
        'l i v e': 'live', 'p l a y': 'play', 's t a y': 'stay',
        'b e g i n': 'begin', 's h o w': 'show', 'h e l p': 'help',
        'p u t': 'put', 'r u n': 'run', 'm o v e': 'move', 'l i k e': 'like',
        'n e e d': 'need', 'f e e l': 'feel', 'b e c o m e': 'become',
        'l e a v e': 'leave', 'c a l l': 'call', 'k e e p': 'keep',
        'b r i n g': 'bring', 'b e g i n': 'begin', 's i t': 'sit',
        's t a n d': 'stand', 'l o s e': 'lose', 'p a y': 'pay',
        'm e e t': 'meet', 'p a y': 'pay', 's a y': 'say', 's e e k': 'seek',
        's p e a k': 'speak', 't e l l': 'tell', 'c o n t i n u e': 'continue',
        'o w n': 'own', 'c o n s i d e r': 'consider', 'r e q u i r e': 'require',
        'a p p e a r': 'appear', 'b e c o m e': 'become', 'c a r r y': 'carry',
        'c h a n g e': 'change', 'c h o o s e': 'choose', 'c l a i m': 'claim',
        'c l e a n': 'clean', 'c l o s e': 'close', 'c o m p l e t e': 'complete',
        'c o n t a i n': 'contain', 'd e c i d e': 'decide', 'd e s c r i b e': 'describe',
        'd e v e l o p': 'develop', 'd i s c u s s': 'discuss', 'e n c o u r a g e': 'encourage',
        'e n s u r e': 'ensure', 'e x p e c t': 'expect', 'e x p l a i n': 'explain',
        'f o l l o w': 'follow', 'h a p p e n': 'happen', 'i n c l u d e': 'include',
        'i n c r e a s e': 'increase', 'i n d i c a t e': 'indicate', 'm a i n t a i n': 'maintain',
        'n e c e s s a r y': 'necessary', 'n o t i c e': 'notice', 'o b t a i n': 'obtain',
        'o c c u r': 'occur', 'o f f e r': 'offer', 'o r d i n a r y': 'ordinary',
        'p a r t i c u l a r': 'particular', 'p e r h a p s': 'perhaps', 'p e r m a n e n t': 'permanent',
        'p o s s i b l e': 'possible', 'p r a c t i c a l': 'practical', 'p r e s e n t': 'present',
        'p r i v a t e': 'private', 'p r o d u c e': 'produce', 'p r o v i d e': 'provide',
        'p u r p o s e': 'purpose', 'r e a d': 'read', 'r e a s o n': 'reason',
        'r e c e i v e': 'receive', 'r e c o g n i s e': 'recognise', 'r e d u c e': 'reduce',
        'r e f e r': 'refer', 'r e l a t e': 'relate', 'r e m a i n': 'remain',
        'r e m e m b e r': 'remember', 'r e p r e s e n t': 'represent', 'r e q u e s t': 'request',
        'r e s u l t': 'result', 'r e t u r n': 'return', 'r e v i e w': 'review',
        's i g n i f i c a n t': 'significant', 's i m i l a r': 'similar', 's i t u a t i o n': 'situation',
        's o l u t i o n': 'solution', 's u p p o r t': 'support', 's u r e': 'sure',
        't a k e': 'take', 't a r g e t': 'target', 'u n d e r': 'under',
        'u n d e r s t a n d': 'understand', 'u s u a l l y': 'usually', 'v a r i o u s': 'various',
        'w i t h i n': 'within', 'w o r k': 'work', 'w o r t h': 'worth',
        # Additional common broken words (government reports)
        'c o u n c i l': 'council', 'c o u n c i l s': 'councils',
        's e r v i c e s': 'services', 's e r v i c e': 'service',
        'c o m m u n i t y': 'community', 'c o m m u n i t i e s': 'communities',
        'g o v e r n m e n t': 'government', 'g o v e r n m e n t s': 'governments',
        'l o c a l': 'local', 'p u b l i c': 'public',
        'e n v i r o n m e n t': 'environment', 'e n v i r o n m e n t a l': 'environmental',
        'd e v e l o p m e n t': 'development', 'd e v e l o p m e n t s': 'developments',
        'p r o j e c t': 'project', 'p r o j e c t s': 'projects',
        'p r o g r a m': 'program', 'p r o g r a m s': 'programs',
        'p r o g r a m m e': 'programme', 'p r o g r a m m e s': 'programmes',
        's u s t a i n a b i l i t y': 'sustainability', 's u s t a i n a b l e': 'sustainable',
        'i n f r a s t r u c t u r e': 'infrastructure',
        'p e r f o r m a n c e': 'performance',
        'm a n a g e m e n t': 'management',
        'a c t i v i t i e s': 'activities', 'a c t i v i t y': 'activity',
        'i m p l e m e n t a t i o n': 'implementation',
        'c o n s u l t a t i o n': 'consultation',
        'c o l l a b o r a t i o n': 'collaboration',
        'p a r t i c i p a t i o n': 'participation',
        'e n g a g e m e n t': 'engagement',
        'r e c r e a t i o n': 'recreation',
        'e m e r g e n c y': 'emergency',
        'p r i o r i t i e s': 'priorities', 'p r i o r i t y': 'priority',
        's t r a t e g i e s': 'strategies', 's t r a t e g y': 'strategy',
        'o b j e c t i v e s': 'objectives', 'o b j e c t i v e': 'objective',
        'a s s e s s m e n t': 'assessment', 'a s s e s s m e n t s': 'assessments',
        'c o m p l e t e d': 'completed', 'c o m p l e t i o n': 'completion',
        'd e l i v e r e d': 'delivered', 'd e l i v e r y': 'delivery', 'd e l i v e r i n g': 'delivering',
        'i m p l e m e n t e d': 'implemented', 'i m p l e m e n t': 'implement',
        'c o n t r i b u t e': 'contribute', 'c o n t r i b u t i n g': 'contributing',
        'p a r t n e r s h i p': 'partnership', 'p a r t n e r s h i p s': 'partnerships',
        'o r g a n i s a t i o n': 'organisation', 'o r g a n i s a t i o n s': 'organisations',
        'o r g a n i z a t i o n': 'organization', 'o r g a n i z a t i o n s': 'organizations',
        'r e s i d e n t s': 'residents', 'r e s i d e n t': 'resident',
        'e m p l o y m e n t': 'employment',
        'a g r i c u l t u r e': 'agriculture',
        'h o u s i n g': 'housing', 'a f f o r d a b l e': 'affordable',
        't r a n s p o r t': 'transport', 't r a n s p o r t a t i o n': 'transportation',
        'w a t e r': 'water', 'w a t e r s u p p l y': 'water supply',
        'w a s t e': 'waste', 'w a s t e w a t e r': 'wastewater',
        'e n e r g y': 'energy', 'r e n e w a b l e': 'renewable',
        'h e r i t a g e': 'heritage',
        'c u l t u r a l': 'cultural', 'c u l t u r e': 'culture',
        't o u r i s m': 'tourism',
        'e d u c a t i o n': 'education',
        'h e a l t h': 'health', 'h e a l t h c a r e': 'healthcare',
        's o c i a l': 'social', 's o c i a l s e r v i c e s': 'social services',
        'b u s i n e s s': 'business', 'b u s i n e s s e s': 'businesses',
        'e c o n o m i c': 'economic', 'e c o n o m y': 'economy',
        's a f e t y': 'safety',
        'r o a d s': 'roads', 'r o a d': 'road',
        'b r i d g e s': 'bridges', 'b r i d g e': 'bridge',
        'f a c i l i t i e s': 'facilities', 'f a c i l i t y': 'facility',
        'p a r k s': 'parks', 'p a r k': 'park',
        'l i b r a r i e s': 'libraries', 'l i b r a r y': 'library',
        'c e n t r e s': 'centres', 'c e n t r e': 'centre',
        'c e n t e r s': 'centers', 'c e n t e r': 'center',
        'i n d i g e n o u s': 'indigenous',
        'a b o r i g i n a l': 'aboriginal',
        't r a d i t i o n a l': 'traditional',
        'c h i l d r e n': 'children', 'c h i l d': 'child',
        'f a m i l i e s': 'families', 'f a m i l y': 'family',
        'y o u t h': 'youth', 's e n i o r s': 'seniors', 's e n i o r': 'senior',
        'd i s a b i l i t i e s': 'disabilities', 'd i s a b i l i t y': 'disability',
        'a c c e s s i b l e': 'accessible', 'a c c e s s i b i l i t y': 'accessibility',
        'c o m p l i a n c e': 'compliance',
        'r e g u l a t o r y': 'regulatory', 'r e g u l a t i o n s': 'regulations',
        'r e q u i r e m e n t s': 'requirements', 'r e q u i r e m e n t': 'requirement',
        's t a t u t o r y': 'statutory',
        'l e g i s l a t i o n': 'legislation',
        'p o l i c i e s': 'policies', 'p o l i c y': 'policy',
        'p r o c e d u r e s': 'procedures', 'p r o c e d u r e': 'procedure',
        'g u i d e l i n e s': 'guidelines', 'g u i d e l i n e': 'guideline',
        'f r a m e w o r k': 'framework', 'f r a m e w o r k s': 'frameworks',
        's t a n d a r d s': 'standards', 's t a n d a r d': 'standard',
        'i n i t i a t i v e s': 'initiatives', 'i n i t i a t i v e': 'initiative',
        'a c h i e v e m e n t s': 'achievements', 'a c h i e v e m e n t': 'achievement',
        'o u t c o m e s': 'outcomes', 'o u t c o m e': 'outcome',
        'c h a l l e n g e s': 'challenges', 'c h a l l e n g e': 'challenge',
        'o p p o r t u n i t i e s': 'opportunities', 'o p p o r t u n i t y': 'opportunity',
        'b e n e f i t s': 'benefits', 'b e n e f i t': 'benefit', 'b e n e f i c i a l': 'beneficial',
        'i m p r o v e m e n t s': 'improvements', 'i m p r o v e m e n t': 'improvement',
        'p r o g r e s s': 'progress', 'p r o g r e s s e d': 'progressed',
        'a v a i l a b l e': 'available',
        'e f f e c t i v e': 'effective', 'e f f e c t i v e l y': 'effectively',
        'e f f i c i e n t': 'efficient', 'e f f i c i e n t l y': 'efficiently',
        'e s s e n t i a l': 'essential', 'e s s e n t i a l l y': 'essentially',
        'v i t a l': 'vital', 'c r i t i c a l': 'critical',
        's i g n i f i c a n t': 'significant', 's i g n i f i c a n t l y': 'significantly',
        'r e l e v a n t': 'relevant',
        'a p p r o p r i a t e': 'appropriate', 'a p p r o p r i a t e l y': 'appropriately',
        'c o m m i t t e d': 'committed', 'c o m m i t m e n t': 'commitment',
        'c o n t i n u e': 'continue', 'c o n t i n u i n g': 'continuing', 'c o n t i n u e d': 'continued',
        'o n g o i n g': 'ongoing',
        'c u r r e n t': 'current', 'c u r r e n t l y': 'currently',
        'p r e s e n t': 'present', 'p r e s e n t l y': 'currently',
        'f u t u r e': 'future',
        'r e c o g n i s e': 'recognise', 'r e c o g n i s e d': 'recognised', 'r e c o g n i t i o n': 'recognition',
        'r e c o g n i z e': 'recognize', 'r e c o g n i z e d': 'recognized',
        'a c k n o w l e d g e': 'acknowledge', 'a c k n o w l e d g e d': 'acknowledged',
        'e n s u r i n g': 'ensuring', 'e n s u r e d': 'ensured',
        'm a i n t a i n i n g': 'maintaining', 'm a i n t e n a n c e': 'maintenance',
        'r e d u c i n g': 'reducing', 'r e d u c t i o n': 'reduction',
        'i n c r e a s i n g': 'increasing', 'i n c r e a s e': 'increase',
        'd e c r e a s i n g': 'decreasing', 'd e c r e a s e': 'decrease',
        'm o n i t o r i n g': 'monitoring', 'm o n i t o r': 'monitor',
        'r e v i e w i n g': 'reviewing', 'r e v i e w e d': 'reviewed',
        'a s s e s s i n g': 'assessing', 'a s s e s s e d': 'assessed',
        'e v a l u a t i n g': 'evaluating', 'e v a l u a t e d': 'evaluated',
        'p l a n n i n g': 'planning', 'p l a n n e d': 'planned',
        'd e v e l o p i n g': 'developing', 'd e v e l o p e d': 'developed',
        'c o n d u c t i n g': 'conducting', 'c o n d u c t e d': 'conducted',
        'p r o v i d i n g': 'providing', 'p r o v i d e d': 'provided',
        's u p p o r t i n g': 'supporting', 's u p p o r t e d': 'supported',
        'a s s i s t i n g': 'assisting', 'a s s i s t e d': 'assisted',
        'c o o r d i n a t i n g': 'coordinating', 'c o o r d i n a t e d': 'coordinated',
        'm a n a g i n g': 'managing', 'm a n a g e d': 'managed',
        'a d m i n i s t e r i n g': 'administering', 'a d m i n i s t e r e d': 'administered',
        'e s t a b l i s h i n g': 'establishing', 'e s t a b l i s h e d': 'established',
        'c r e a t i n g': 'creating', 'c r e a t e d': 'created',
        'i m p l e m e n t i n g': 'implementing', 'i m p l e m e n t e d': 'implemented',
        'l a u n c h i n g': 'launching', 'l a u n c h e d': 'launched',
        's t a r t i n g': 'starting', 's t a r t e d': 'started',
        'c o m p l e t i n g': 'completing', 'c o m p l e t e d': 'completed',
        'f i n i s h i n g': 'finishing', 'f i n i s h e d': 'finished',
        'o p e n i n g': 'opening', 'o p e n e d': 'opened',
        'b u i l d i n g': 'building', 'b u i l t': 'built',
        'c o n s t r u c t i n g': 'constructing', 'c o n s t r u c t e d': 'constructed',
        'i n s t a l l i n g': 'installing', 'i n s t a l l e d': 'installed',
        'r e n o v a t i n g': 'renovating', 'r e n o v a t e d': 'renovated',
        'u p g r a d i n g': 'upgrading', 'u p g r a d e d': 'upgraded',
        'r e p a i r i n g': 'repairing', 'r e p a i r e d': 'repaired',
        'r e p l a c i n g': 'replacing', 'r e p l a c e d': 'replaced',
        'u p d a t i n g': 'updating', 'u p d a t e d': 'updated',
        'i m p r o v i n g': 'improving', 'i m p r o v e d': 'improved',
        'e n h a n c i n g': 'enhancing', 'e n h a n c e d': 'enhanced',
        'e x t e n d i n g': 'extending', 'e x t e n d e d': 'extended',
        'e x p a n d i n g': 'expanding', 'e x p a n d e d': 'expanded',
        'd e v e l o p i n g': 'developing', 'd e v e l o p e d': 'developed',
        'd e s i g n i n g': 'designing', 'd e s i g n e d': 'designed',
        'p l a n t i n g': 'planting', 'p l a n t e d': 'planted',
    }

    # Common OCR number substitutions (e.g., l -> 1, O -> 0)
    OCR_LETTER_TO_NUMBER = {
        'l': '1', 'O': '0', 'o': '0', 'I': '1', 'i': '1',
        'e': '3', 'a': '4', 's': '5', 'b': '6', 'g': '9',
    }

    # Number to letter (for context-aware correction)
    OCR_NUMBER_TO_LETTER = {
        '0': 'O', '1': 'I', '3': 'E', '4': 'A', '5': 'S', '6': 'G', '8': 'B', '9': 'g',
    }

    def __init__(self, use_dictionary: bool = True):
        """
        Initialize OCR cleanup.

        Args:
            use_dictionary: Whether to use dictionary-based word validation
        """
        self.use_dictionary = use_dictionary
        self._word_set = None

    def _load_words(self) -> Set[str]:
        """Lazily load common English words for validation."""
        if self._word_set is None:
            # Common English words (subset for performance)
            words = [
                'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
                'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
                'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
                'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their', 'what',
                'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go', 'me',
                'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know', 'take',
                'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other',
                'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over', 'think', 'also',
                'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first', 'well', 'way',
                'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us',
                'is', 'was', 'are', 'were', 'been', 'being', 'has', 'had', 'does', 'did',
                'doing', 'should', 'must', 'might', 'shall', 'may', 'need', 'used', 'ought',
                'going', 'coming', 'looking', 'taking', 'making', 'giving', 'showing', 'trying',
                'having', 'being', 'doing', 'saying', 'getting', 'making', 'coming', 'going',
                'support', 'supporting', 'supported', 'provide', 'provides', 'provided', 'providing',
                'council', 'community', 'councils', 'local', 'government', 'public', 'services',
                'project', 'projects', 'program', 'programs', 'planning', 'development', 'developments',
                'environment', 'environmental', 'sustainability', 'sustainable', 'infrastructure',
                'health', 'education', 'housing', 'transport', 'waste', 'water', 'energy', 'social',
                'economic', 'cultural', 'governance', 'performance', 'report', 'annual', 'financial',
                'aboriginal', 'indigenous', 'traditional', 'residents', 'people', 'families', 'children',
                'seniors', 'youth', 'disabilities', 'access', 'affordable', 'heritage', 'recreation',
                'sport', 'culture', 'arts', 'tourism', 'employment', 'business', 'agriculture',
                'emergency', 'services', 'safety', 'roads', 'bridges', 'buildings', 'facilities',
                'parks', 'libraries', 'museums', 'centres', 'centers', 'clubs', 'groups', 'organisations',
                'organisations', 'government', 'statutory', 'compliance', 'regulatory', 'requirements',
                'partners', 'partnership', 'collaboration', 'consultation', 'engagement', 'participation',
                'opportunity', 'challenges', 'achievements', 'outcomes', 'objectives', 'strategies',
                'priority', 'priorities', 'focus', 'focused', 'committed', ' commitment', 'ensure',
                'ensuring', 'maintain', 'maintaining', 'improved', 'improvement', 'improvements',
                'increase', 'increasing', 'decrease', 'decreasing', 'reduce', 'reducing', 'reduction',
                'recognise', 'recognised', 'recognition', 'acknowledge', 'acknowledged',
                'importance', 'important', 'significant', 'significantly', 'essential', 'vital',
                'critical', 'necessary', 'required', 'requirements', 'activities', 'activity',
                'delivery', 'delivered', 'delivering', 'completed', 'completion', 'implement',
                'implemented', 'implementation', 'progress', 'advancing', 'advance', 'progressed',
                'continue', 'continued', 'continuing', 'ongoing', 'current', 'present', 'future',
                'available', 'accessible', 'appropriate', 'relevant', 'effective', 'efficient',
                'successful', 'successfully', 'beneficial', 'benefits', 'benefit',
            ]
            self._word_set = set(w.lower() for w in words)
        return self._word_set

    def is_ocr_text(self, text: str, sample_size: int = 5000) -> bool:
        """
        Detect if text is likely from an OCR-scanned PDF.

        Scans for common OCR artifacts:
        - Broken words with internal spaces (e.g., "c o u n c i l")
        - Known OCR misread patterns (e.g., "o f", "t h e")

        Args:
            text: Text to analyze
            sample_size: Number of characters to sample (0 for full text)

        Returns:
            True if text appears to be OCR-generated, False if native text
        """
        if not text:
            return False

        # Sample text if it's very long (for performance)
        if sample_size > 0 and len(text) > sample_size:
            # Sample from beginning, middle, and end
            text = text[:sample_size]

        # Count OCR artifacts
        broken_word_pattern = re.compile(r'\b([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\s+')
        broken_word_matches = len(broken_word_pattern.findall(text))

        # Count known broken word patterns (e.g., "t h e", "o f")
        broken_known_count = 0
        for pattern in self.OCR_BROKEN_WORDS.keys():
            # Count occurrences of spaced pattern
            spaced_count = len(re.findall(r'\b' + re.escape(pattern) + r'\b', text, re.IGNORECASE))
            broken_known_count += spaced_count

        # Count short lines (1-3 chars) followed by content (OCR fragment indicator)
        short_line_pattern = re.compile(r'^([A-Za-z]{1,3})\s+$', re.MULTILINE)
        short_lines = len(short_line_pattern.findall(text))

        # Calculate OCR likelihood score
        # Normalize by text length
        text_len = len(text)
        word_count = len(text.split())

        # If we find significant OCR artifacts relative to text size, it's OCR
        # Threshold: more than 0.5% broken words or 1% short line fragments
        ocr_score = (
            (broken_word_matches / max(word_count, 1) * 100) +
            (short_lines / max(word_count, 1) * 100) +
            (broken_known_count / max(word_count, 1) * 100)
        )

        # Also check for specific OCR indicators
        # Native PDFs rarely have words broken across lines
        if broken_word_matches > word_count * 0.005:  # 0.5% threshold
            return True
        if short_lines > word_count * 0.01:  # 1% threshold
            return True
        if broken_known_count > word_count * 0.01:  # 1% threshold
            return True

        return False

    def get_ocr_confidence(self, text: str, sample_size: int = 5000) -> float:
        """
        Get a confidence score (0.0 to 1.0) that text is OCR-generated.

        Args:
            text: Text to analyze
            sample_size: Number of characters to sample (0 for full text)

        Returns:
            Float between 0.0 (definitely native) and 1.0 (definitely OCR)
        """
        if not text:
            return 0.0

        # Sample text if it's very long (for performance)
        if sample_size > 0 and len(text) > sample_size:
            text = text[:sample_size]

        broken_word_pattern = re.compile(r'\b([A-Za-z])\s+([A-Za-z])\s+([A-Za-z])\s+')
        broken_word_matches = len(broken_word_pattern.findall(text))

        broken_known_count = 0
        for pattern in self.OCR_BROKEN_WORDS.keys():
            spaced_count = len(re.findall(r'\b' + re.escape(pattern) + r'\b', text, re.IGNORECASE))
            broken_known_count += spaced_count

        short_line_pattern = re.compile(r'^([A-Za-z]{1,3})\s+$', re.MULTILINE)
        short_lines = len(short_line_pattern.findall(text))

        word_count = max(len(text.split()), 1)

        # Calculate confidence based on artifact density
        confidence = min(1.0, (
            (broken_word_matches / word_count * 2) +
            (short_lines / word_count * 1) +
            (broken_known_count / word_count * 2)
        ))

        return confidence

    def _is_valid_word(self, word: str) -> bool:
        """Check if word is valid English or appears common enough."""
        word_lower = word.lower().strip('.,!?;:\'"()[]{}')
        if not word_lower:
            return False
        if len(word_lower) <= 1:
            return word_lower in {'a', 'i', 'o'}
        if self.use_dictionary:
            return word_lower in self._load_words()
        return True

    def _fix_single_char_spaces(self, text: str) -> str:
        """
        Generic fixer for single-character internal spaces.

        Finds patterns like "c o u n c i l" and joins them, then validates
        against dictionary to avoid false positives.
        """
        # Pattern: sequence of single letters separated by spaces
        # e.g., "c o u n c i l" or "w i t h"
        pattern = r'\b([A-Za-z])(?:\s+([A-Za-z]))+\b'

        def try_join(match):
            word = match.group(0)
            # Remove spaces to get potential word
            joined = word.replace(' ', '')
            # Check if valid (handles multi-char like "w i t h" -> "with")
            if self._is_valid_word(joined):
                return joined
            # Also check title case for proper nouns
            if self._is_valid_word(joined.title()):
                return joined.title()
            # Check if it's all consonants/vowels pattern (likely broken)
            return word.replace(' ', '')

        return re.sub(pattern, try_join, text)

    def _fix_generic_broken_words(self, text: str) -> str:
        """
        Fix broken words that aren't in the specific_fixes list.

        Handles arbitrary single-character internal spaces by joining and validating.
        This catches OCR errors like "prac tic al" where specific patterns don't exist.
        """
        # Find any word with internal single-character tokens
        # Pattern: word-start, then sequences of (single char + space) or just space-separated single chars
        words = re.findall(r'\b\w+\b', text)

        for word in words:
            # Skip if already valid
            if self._is_valid_word(word.lower()):
                continue

            # Check if this looks like a broken word (has spaces or is all single chars)
            if ' ' in word:
                joined = word.replace(' ', '')
                if self._is_valid_word(joined.lower()):
                    # Only fix if joining makes it valid
                    pattern = re.escape(word)
                    text = re.sub(pattern, joined, text, count=1)

        return text

    def _fix_ocr_spaces(self, text: str) -> str:
        """
        Fix OCR artifacts where spaces were inserted between characters.

        Handles patterns like:
        - "o f" -> "of", "t h e" -> "the" (broken common words)
        - "practic al" -> "practical" (single space in word)
        """
        # Strategy 1: Fix common broken multi-word OCR breaks (prepositions, articles)
        # Sort by length descending to match longer patterns first
        for broken, fixed in sorted(self.OCR_BROKEN_WORDS.items(), key=lambda x: -len(x[0])):
            # Match with word boundaries to avoid false positives
            pattern = r'\b' + re.escape(broken) + r'\b'
            text = re.sub(pattern, fixed, text, flags=re.IGNORECASE)

        # Strategy 2: Fix specific known OCR patterns that are common in government reports
        specific_fixes = [
            # LEP related
            (r'\bL\s*E\s*P\b', 'LEP'),
            # Plumbing/drainage
            (r'\bPlumb\s*ing\b', 'Plumbing'),
            (r'\bPlumb\s*er\b', 'Plumber'),
            (r'\bDrain\s*age\b', 'Drainage'),
            (r'\bDrain\s*lay\s*er\b', 'Drainlayer'),
            (r'\bPlumb\s*er\s*\/\s*Drain\s*lay\s*er\b', 'Plumber/Drainlayer'),
            # Self-certification
            (r'\bself[-\s]*cert\s*ific\s*at\s*ion\b', 'self-certification'),
            (r'\bself[-\s]*cert\s*ification\b', 'self-certification'),
            (r'\bli\s*cens\s*ed\b', 'licensed'),
            (r'\bli\s*censed\b', 'licensed'),
            # Words with single internal spaces (pattern: consonant-vowel-consonant pattern)
            (r'\bprac\s*tic\s*al\b', 'practical'),
            (r'\bpracti\s*cal\b', 'practical'),
            (r'\bappli\s*ca\s*tion\b', 'application'),
            (r'\bapplica\s*tion\b', 'application'),
            (r'\bencou\s*rage\b', 'encourage'),
            (r'\bencoura\s*ge\b', 'encourage'),
            (r'\ben\s*cour\s*age\b', 'encourage'),
            (r'\bfacilit\s*ate\b', 'facilitate'),
            (r'\bfacilitat\s*ed\b', 'facilitated'),
            (r'\bfacilita\s*te\b', 'facilitate'),
            (r'\bincorpora\s*ted\b', 'incorporated'),
            (r'\bincorpor\s*ated\b', 'incorporated'),
            (r'\bin\s*cor\s*po\s*rate\b', 'incorporate'),
            (r'\bamen\s*dment\b', 'amendment'),
            (r'\bamen\s*d\s*ment\b', 'amendment'),
            (r'\bamendmen\s*t\b', 'amendment'),
            (r'\bamendm\s*ent\b', 'amendment'),
            (r'\bdeve\s*lop\s*ment\b', 'development'),
            (r'\bdevel\s*op\s*ment\b', 'development'),
            (r'\bcur\s*rent\b', 'current'),
            (r'\bcur\s*ren\s*t\b', 'current'),
            (r'\bcur\s*ently\b', 'currently'),
            (r'\bnot\s*been\b', 'not been'),
            (r'\bhas\s*not\b', 'has not'),
            (r'\bhave\s*not\b', 'have not'),
            (r'\bbeen\s*done\b', 'been done'),
            (r'\bwith\s*reliance\b', 'with reliance'),
            (r'\breliance\s*on\b', 'reliance on'),
            (r'\binspections\b', 'inspections'),
            (r'\binspec\s*tions\b', 'inspections'),
            (r'\bconsult\s*ant\b', 'consultant'),
            (r'\bpart\s*time\b', 'part time'),
            (r'\bterms\s*of\b', 'terms of'),
            (r'\bamend\s*ments\b', 'amendments'),
            (r'\bamend\s*ment\s*s\b', 'amendments'),
            (r'\blegal\b', 'legal'),
            (r'\ble\s*gal\b', 'legal'),
            (r'\bleisure\b', 'leisure'),
            (r'\blei\s*sure\b', 'leisure'),
            (r'\ben\s*viron\s*men\s*tal\b', 'environmental'),
            (r'\ben\s*viron\s*men\s*tal\b', 'environmental'),
            (r'\benvi\s*ron\s*men\s*tal\b', 'environmental'),
            (r'\bsus\s*tain\s*able\b', 'sustainable'),
            (r'\bsustain\s*able\b', 'sustainable'),
            (r'\bsustain\s*ably\b', 'sustainably'),
            (r'\brec\s*og\s*nose\b', 'recognise'),
            (r'\brecog\s*nise\b', 'recognise'),
            (r'\brec\s*og\s*nise\b', 'recognise'),
            (r'\bcol\s*lab\s*o\s*ration\b', 'collaboration'),
            (r'\bcollabo\s*ration\b', 'collaboration'),
            (r'\bcon\s*sul\s*ta\s*tion\b', 'consultation'),
            (r'\bconsulta\s*tion\b', 'consultation'),
            (r'\bop\s*er\s*a\s*tion\s*al\b', 'operational'),
            (r'\bopera\s*tional\b', 'operational'),
            (r'\bper\s*for\s*mance\b', 'performance'),
            (r'\bperf ormance\b', 'performance'),
            (r'\bman\s*age\s*ment\b', 'management'),
            (r'\bmana\s*gement\b', 'management'),
            (r'\bac\s*tiv\s*i\s*ties\b', 'activities'),
            (r'\bactivi\s*ties\b', 'activities'),
            (r'\bac\s*tiv\s*i\s*ty\b', 'activity'),
            (r'\bcom\s*mu\s*ni\s*ty\b', 'community'),
            (r'\bcommu\s*nity\b', 'community'),
            (r'\bgov\s*ern\s*ance\b', 'governance'),
            (r'\bgove\s*rnance\b', 'governance'),
            (r'\ben\s*viron\s*ment\b', 'environment'),
            (r'\bin\s*fra\s*struc\s*ture\b', 'infrastructure'),
            (r'\binfras\s*tructure\b', 'infrastructure'),
            (r'\btrans\s*port\b', 'transport'),
            (r'\beco\s*nom\s*ic\b', 'economic'),
            (r'\bcul\s*tu\s*ral\b', 'cultural'),
            (r'\brec\s*re\s*a\s*tion\b', 'recreation'),
            (r'\brecrea\s*tion\b', 'recreation'),
            (r'\bem\s*er\s*gen\s*cy\b', 'emergency'),
            (r'\bemer\s*gency\b', 'emergency'),
            (r'\bsa\s*fe\s*ty\b', 'safety'),
            (r'\bsafety\b', 'safety'),
            (r'\bmajor\b', 'major'),
            (r'\bmaj\s*or\b', 'major'),
            (r'\bsig\s*ni\s*fi\s*cant\b', 'significant'),
            (r'\bsigni\s*ficant\b', 'significant'),
            (r'\bapp\s*ro\s*pri\s*ate\b', 'appropriate'),
            (r'\bappro\s*priate\b', 'appropriate'),
            (r'\bneces\s*sa\s*ry\b', 'necessary'),
            (r'\bneces\s*sary\b', 'necessary'),
            (r'\bpos\s*si\s*ble\b', 'possible'),
            (r'\bpossi\s*ble\b', 'possible'),
            (r'\bcon\s*ti\s*nue\b', 'continue'),
            (r'\bconti\s*nue\b', 'continue'),
            (r'\brep\s*re\s*sent\b', 'represent'),
            (r'\brepre\s*sent\b', 'represent'),
            (r'\bmain\s*tain\b', 'maintain'),
            (r'\bmaint\s*ain\b', 'maintain'),
            (r'\bmain\s*te\s*nance\b', 'maintenance'),
            (r'\bmainte\s*nance\b', 'maintenance'),
            (r'\bimple\s*ment\b', 'implement'),
            (r'\bimple\s*men\s*ta\s*tion\b', 'implementation'),
            (r'\bimplemen\s*tation\b', 'implementation'),
            (r'\bdeliv\s*ery\b', 'delivery'),
            (r'\bdeli\s*very\b', 'delivery'),
            (r'\bcom\s*pre\s*hen\s*sive\b', 'comprehensive'),
            (r'\bcompre\s*hensive\b', 'comprehensive'),
            (r'\brecom\s*mend\b', 'recommend'),
            (r'\brecommen\s*dations\b', 'recommendations'),
            (r'\bcon\s*si\s*de\s*ra\s*tion\b', 'consideration'),
            (r'\bconsi\s*dera\s*tion\b', 'consideration'),
            (r'\bpri\s*vate\b', 'private'),
            (r'\bpriv\s*ate\b', 'private'),
            (r'\bpub\s*lic\b', 'public'),
            (r'\bpubli\s*c\b', 'public'),
            (r'\brele\s*vant\b', 'relevant'),
            (r'\brele\s*vant\b', 'relevant'),
            (r'\binter\s*nal\b', 'internal'),
            (r'\bexters\s*nal\b', 'external'),
            (r'\bnational\b', 'national'),
            (r'\bregional\b', 'regional'),
            # Additional government report terms
            (r'\bdeliv\s*ered\b', 'delivered'),
            (r'\bdeliver\s*ing\b', 'delivering'),
            (r'\bimple\s*men\s*ted\b', 'implemented'),
            (r'\bcom\s*pleted\b', 'completed'),
            (r'\bcom\s*ple\s*ted\b', 'completed'),
            (r'\bprogress\b', 'progress'),
            (r'\bpro\s*gress\b', 'progress'),
            (r'\bachieve\s*ment\b', 'achievement'),
            (r'\bachieve\s*ments\b', 'achievements'),
            (r'\bobjec\s*tive\b', 'objective'),
            (r'\bobjec\s*tives\b', 'objectives'),
            (r'\bstra\s*tegy\b', 'strategy'),
            (r'\bstra\s*te\s*gies\b', 'strategies'),
            (r'\bpriority\b', 'priority'),
            (r'\bprior\s*ities\b', 'priorities'),
            (r'\bcommit\s*ment\b', 'commitment'),
            (r'\bcommit\s*ted\b', 'committed'),
            (r'\bavail\s*able\b', 'available'),
            (r'\baccess\s*ible\b', 'accessible'),
            (r'\bafford\s*able\b', 'affordable'),
            (r'\beffec\s*tive\b', 'effective'),
            (r'\beffi\s*cient\b', 'efficient'),
            (r'\bsuccess\s*ful\b', 'successful'),
            (r'\bsuccess\s*fully\b', 'successfully'),
            (r'\bbenefi\s*cial\b', 'beneficial'),
            (r'\bneces\s*sary\b', 'necessary'),
            (r'\bessen\s*tial\b', 'essential'),
            (r'\bcriti\s*cal\b', 'critical'),
            (r'\bvit\s*al\b', 'vital'),
            (r'\bsigni\s*fi\s*cant\b', 'significant'),
            (r'\bparti\s*cular\b', 'particular'),
            (r'\bpartic\s*ular\b', 'particular'),
            (r'\bappro\s*pri\s*ate\b', 'appropriate'),
            (r'\brepre\s*sen\s*ta\s*tion\b', 'representation'),
            (r'\bpartic\s*ipa\s*tion\b', 'participation'),
            (r'\bconsul\s*ta\s*tion\b', 'consultation'),
            (r'\bcollabo\s*ra\s*tion\b', 'collaboration'),
            (r'\bpartnership\b', 'partnership'),
            (r'\bpartner\s*ships\b', 'partnerships'),
            (r'\borgani\s*sa\s*tion\b', 'organisation'),
            (r'\borgani\s*sa\s*tions\b', 'organisations'),
            (r'\bcoordi\s*na\s*tion\b', 'coordination'),
            (r'\bcollabora\s*tion\b', 'collaboration'),
            (r'\bconsulta\s*tion\b', 'consultation'),
            (r'\bengage\s*ment\b', 'engagement'),
            (r'\bparticipa\s*tion\b', 'participation'),
            (r'\binclusi\s*on\b', 'inclusion'),
            (r'\bdiver\s*si\s*ty\b', 'diversity'),
            (r'\baccessi\s*bili\s*ty\b', 'accessibility'),
            (r'\bwellbeing\b', 'wellbeing'),
            (r'\brepresenta\s*tion\b', 'representation'),
            (r'\bopportuni\s*ty\b', 'opportunity'),
            (r'\bopportuni\s*ties\b', 'opportunities'),
            (r'\bchallenge\s*s\b', 'challenges'),
            (r'\bachievement\s*s\b', 'achievements'),
            (r'\boutcome\s*s\b', 'outcomes'),
            (r'\bstrateg\s*y\b', 'strategy'),
            (r'\bstrategies\b', 'strategies'),
            (r'\bpriority\s*s\b', 'priorities'),
            (r'\bassess\s*ment\b', 'assessment'),
            (r'\bassess\s*ments\b', 'assessments'),
            (r'\bevalu\s*ation\b', 'evaluation'),
            (r'\bmonitor\s*ing\b', 'monitoring'),
            (r'\bperformance\b', 'performance'),
            (r'\baccounta\s*bili\s*ty\b', 'accountability'),
            (r'\btransparen\s*cy\b', 'transparency'),
            (r'\bsustaina\s*bili\s*ty\b', 'sustainability'),
            (r'\benvi\s*ron\s*men\s*tal\b', 'environmental'),
            (r'\bconserva\s*tion\b', 'conservation'),
            (r'\bbiodiver\s*si\s*ty\b', 'biodiversity'),
            (r'\brenewa\s*ble\b', 'renewable'),
            (r'\bemission\s*s\b', 'emissions'),
            (r'\bcarbon\s*neu\s*tral\b', 'carbon neutral'),
            (r'\bclimate\s*change\b', 'climate change'),
            (r'\bdisaster\s*preparen\b', 'disaster preparedness'),
            (r'\bemergen\s*cy\s*manage\s*ment\b', 'emergency management'),
            (r'\bland\s*use\b', 'land use'),
            (r'\bur\s*ban\s*design\b', 'urban design'),
            (r'\bzoning\b', 'zoning'),
            (r'\bhousing\b', 'housing'),
            (r'\bafford\s*able\s*housing\b', 'affordable housing'),
            (r'\bhomeless\s*ness\b', 'homelessness'),
            (r'\bchild\s*care\b', 'childcare'),
            (r'\baged\s*care\b', 'aged care'),
            (r'\bhealth\s*care\b', 'healthcare'),
            (r'\bsocial\s*services\b', 'social services'),
            (r'\bcommu\s*nity\s*services\b', 'community services'),
            (r'\bpub\s*lic\s*transport\b', 'public transport'),
            (r'\broad\s*net\s*work\b', 'road network'),
            (r'\bwater\s*sup\s*ply\b', 'water supply'),
            (r'\bwaste\s*water\b', 'wastewater'),
            (r'\bwaste\s*manage\s*ment\b', 'waste management'),
            (r'\brecy\s*cling\b', 'recycling'),
            (r'\benergy\s*effi\s*cien\s*cy\b', 'energy efficiency'),
            (r'\brenew\s*able\s*energy\b', 'renewable energy'),
            (r'\bsolar\s*panels\b', 'solar panels'),
            (r'\btouri\s*sm\b', 'tourism'),
            (r'\bher\s*itage\b', 'heritage'),
            (r'\bcultu\s*ral\b', 'cultural'),
            (r'\brecrea\s*tional\b', 'recreational'),
            (r'\bsport\s*ing\b', 'sporting'),
            (r'\blei\s*sure\b', 'leisure'),
            (r'\bparks\s*and\s*gar\s*dens\b', 'parks and gardens'),
            (r'\blib\s*raries\b', 'libraries'),
            (r'\bmuse\s*ums\b', 'museums'),
            (r'\bgaller\s*ies\b', 'galleries'),
            (r'\bcom\s*mu\s*ni\s*ca\s*tion\b', 'communication'),
            (r'\bcoordi\s*na\s*tion\b', 'coordination'),
            (r'\bconsulta\s*tion\b', 'consultation'),
            (r'\benga\s*gement\b', 'engagement'),
            (r'\bpartici\s*pa\s*tion\b', 'participation'),
            (r'\binclusi\s*ve\b', 'inclusive'),
            (r'\bempower\s*ment\b', 'empowerment'),
            (r'\bcapa\s*city\s*build\s*ing\b', 'capacity building'),
            (r'\bprofes\s*sional\b', 'professional'),
            (r'\bdevel\s*op\s*men\s*tal\b', 'developmental'),
            (r'\bgovernance\b', 'governance'),
            (r'\blead\s*er\s*ship\b', 'leadership'),
            (r'\bstewardship\b', 'stewardship'),
            (r'\baccounta\s*ble\b', 'accountable'),
            (r'\btransparen\s*t\b', 'transparent'),
            (r'\bcollabo\s*ra\s*tive\b', 'collaborative'),
            (r'\binnova\s*tion\b', 'innovation'),
            (r'\bcreativ\s*ity\b', 'creativity'),
            (r'\bresili\s*ence\b', 'resilience'),
            (r'\badapti\s*on\b', 'adaptation'),
            (r'\bmitiga\s*tion\b', 'mitigation'),
            (r'\bprepar\s*ed\s*ness\b', 'preparedness'),
            (r'\brespon\s*se\b', 'response'),
            (r'\brecov\s*ery\b', 'recovery'),
            (r'\bris\s*k\b', 'risk'),
            (r'\brisks\b', 'risks'),
            (r'\bevalu\s*ation\b', 'evaluation'),
            (r'\bmoni\s*tor\s*ing\b', 'monitoring'),
            (r'\breview\b', 'review'),
            (r'\breviews\b', 'reviews'),
            (r'\breporting\b', 'reporting'),
            (r'\breporting\b', 'reporting'),
            (r'\bcompliance\b', 'compliance'),
            (r'\bregula\s*tions\b', 'regulations'),
            (r'\bstan\s*dards\b', 'standards'),
            (r'\bguideli\s*nes\b', 'guidelines'),
            (r'\bprocedures\b', 'procedures'),
            (r'\bprotocols\b', 'protocols'),
            (r'\bpolicies\b', 'policies'),
            (r'\bframe\s*work\b', 'framework'),
            (r'\bframe\s*works\b', 'frameworks'),
            (r'\bstrat\s*egic\b', 'strategic'),
            (r'\btacti\s*cal\b', 'tactical'),
            (r'\bopera\s*tional\b', 'operational'),
            (r'\bcor\s*po\s*rate\b', 'corporate'),
            (r'\bstatutory\b', 'statutory'),
            (r'\bregu\s*latory\b', 'regulatory'),
            (r'\blegis\s*lation\b', 'legislation'),
            (r'\bstatutes\b', 'statutes'),
            (r'\bordinances\b', 'ordinances'),
            (r'\bby-laws\b', 'bylaws'),
            (r'\bresolutions\b', 'resolutions'),
            (r'\bminutes\b', 'minutes'),
            (r'\bagenda\b', 'agenda'),
            (r'\bnotices\b', 'notices'),
            (r'\bannounce\s*ments\b', 'announcements'),
            (r'\bcommu\s*ni\s*ca\s*tions\b', 'communications'),
            (r'\bmedia\b', 'media'),
            (r'\bpublica\s*tions\b', 'publications'),
            (r'\bnews\s*letters\b', 'newsletters'),
            (r'\bwebsites\b', 'websites'),
            (r'\bportals\b', 'portals'),
            (r'\bdatabases\b', 'databases'),
            (r'\brecords\b', 'records'),
            (r'\barchives\b', 'archives'),
            (r'\bdocuments\b', 'documents'),
            (r'\breports\b', 'reports'),
            (r'\bplans\b', 'plans'),
            (r'\bprograms\b', 'programs'),
            (r'\bprojects\b', 'projects'),
            (r'\binitiatives\b', 'initiatives'),
            (r'\bprograms\b', 'programs'),
            (r'\bservices\b', 'services'),
            (r'\bfacilities\b', 'facilities'),
            (r'\binfrastructure\b', 'infrastructure'),
            (r'\bassets\b', 'assets'),
            (r'\bresources\b', 'resources'),
            (r'\bfunding\b', 'funding'),
            (r'\bbudgets\b', 'budgets'),
            (r'\bexpenditure\b', 'expenditure'),
            (r'\brevenue\b', 'revenue'),
            (r'\bincome\b', 'income'),
            (r'\bassets\b', 'assets'),
            (r'\bliabilities\b', 'liabilities'),
            (r'\bequity\b', 'equity'),
            (r'\bcapital\b', 'capital'),
            (r'\binvestments\b', 'investments'),
            (r'\bgrants\b', 'grants'),
            (r'\bsubsidies\b', 'subsidies'),
            (r'\bdonations\b', 'donations'),
            (r'\bsponsorships\b', 'sponsorships'),
            (r'\bcontracts\b', 'contracts'),
            (r'\btenders\b', 'tenders'),
            (r'\bprocurement\b', 'procurement'),
            (r'\bpurchasing\b', 'purchasing'),
            (r'\bsupply\b', 'supply'),
            (r'\blogistics\b', 'logistics'),
            (r'\bprocurement\b', 'procurement'),
            (r'\bcontract\s*ing\b', 'contracting'),
            (r'\bservice\s*con\s*tracts\b', 'service contracts'),
            (r'\bworks\s*con\s*tracts\b', 'works contracts'),
            (r'\bconsultancy\b', 'consultancy'),
            (r'\bconsultants\b', 'consultants'),
            (r'\badvisors\b', 'advisors'),
            (r'\badvisers\b', 'advisers'),
            (r'\bspecialists\b', 'specialists'),
            (r'\bexperts\b', 'experts'),
            (r'\bcontractors\b', 'contractors'),
            (r'\bsubcontractors\b', 'subcontractors'),
            (r'\bsuppliers\b', 'suppliers'),
            (r'\bproviders\b', 'providers'),
            (r'\bdeliverers\b', 'deliverers'),
        ]

        for pattern, replacement in specific_fixes:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text

    def _fix_ocr_misc(self, text: str) -> str:
        """Fix miscellaneous OCR artifacts."""
        # Fix common letter/number confusions in context
        # e.g., "l" vs "1" in word context

        # Fix "O" -> "0" errors in words (less common, more risky)
        # Only apply in specific known patterns
        text = re.sub(r'\bO\b', '0', text)  # Standalone O -> 0 (for page numbers etc)

        # Fix double letters broken by space
        text = re.sub(r'([A-Za-z])\s+\1{2,}', r'\1\1', text)  # "s  s  s" -> "ss"
        text = re.sub(r'([A-Za-z])\s+\1', r'\1\1', text)  # "s s" -> "ss"

        # Fix hyphenation at end of lines (word-)
        text = re.sub(r'(\w)-\s*\n\s*(\w)', r'\1\2', text)

        # Clean up any remaining multiple spaces
        text = re.sub(r' {2,}', ' ', text)

        return text

    def _spell_check_corrections(self, text: str) -> str:
        """
        Apply spell-checking corrections for common OCR errors.

        Uses pyspellchecker to identify and correct misspelled words that are
        likely OCR errors (not in dictionary but close to valid words).
        """
        try:
            from spellchecker import SpellChecker
        except ImportError:
            # If pyspellchecker not installed, skip
            return text

        spell = SpellChecker()
        # Find words that are likely misspellings
        words = re.findall(r'\b[A-Za-z]+\b', text)
        unknowns = spell.unknown(words)

        for unknown in unknowns:
            # Only correct if confident (lowest distance)
            candidates = spell.candidates(unknown)
            if candidates:
                # Check if the correction has edit distance <= 1
                correction = spell.correction(unknown)
                if correction and correction != unknown:
                    # Apply correction with word boundaries
                    pattern = re.escape(unknown)
                    text = re.sub(pattern, correction, text, count=1)

        return text

    def cleanup(self, text: str) -> str:
        """
        Apply all OCR cleanup operations to text.

        Args:
            text: Raw OCR text

        Returns:
            Cleaned text
        """
        if not text:
            return text

        # Step 1: Pre-process broken patterns - join newlines in middle of words
        # Pattern: alphanumeric followed by newline followed by alphanumeric
        # This fixes "peop\nle" -> "people" and "o\nf" -> "of"
        text = re.sub(r'([A-Za-z])\n([A-Za-z])', r'\1\2', text)
        text = re.sub(r'([A-Za-z])\n\s*([A-Za-z])', r'\1\2', text)

        # Step 2: Handle multi-line fragments (very short lines 1-3 chars)
        text = self._join_short_fragments(text)

        # Step 3: Apply OCR space fixes (specific patterns first)
        text = self._fix_ocr_spaces(text)

        # Step 4: Apply generic single-char space fixer for arbitrary broken words
        text = self._fix_single_char_spaces(text)
        text = self._fix_generic_broken_words(text)

        # Step 5: Apply spell-checking correction
        text = self._spell_check_corrections(text)

        # Step 6: Apply miscellaneous fixes
        text = self._fix_ocr_misc(text)

        # Step 7: Normalize whitespace
        text = re.sub(r' {2,}', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def _join_short_fragments(self, text: str) -> str:
        """
        Join very short lines (1-3 chars) that are likely broken word fragments.

        E.g., when OCR splits "people" across lines as:
        peop
        le
        """
        lines = text.split('\n')
        result = []
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Check if this line is a short fragment
            if len(line) <= 3 and line.isalnum():
                # Check if previous line exists and ends with alphanumeric
                if result:
                    prev = result[-1]
                    if prev and prev[-1].isalnum():
                        # Join with previous line
                        result[-1] = prev + line
                        i += 1
                        continue
                    # Check if next line exists
                    elif i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line and next_line[0].isalnum():
                            # Join current fragment with next line
                            lines[i + 1] = line + next_line
                            i += 1
                            continue

                # Even if no join, don't add fragment as separate line
                i += 1
                continue

            result.append(lines[i])
            i += 1

        return '\n'.join(result)


# Standalone function for easy use
def clean_ocr_text(text: str) -> str:
    """
    Clean OCR artifacts from scanned PDF text.

    Args:
        text: Raw text extracted from scanned PDF

    Returns:
        Cleaned text with OCR artifacts fixed
    """
    cleaner = OCRCleanup()
    return cleaner.cleanup(text)
