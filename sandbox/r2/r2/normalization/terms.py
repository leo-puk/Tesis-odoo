"""Reproducible lexical frequencies and corpus-scoped TF-IDF, never edges."""
from collections import Counter
import re
from importlib.metadata import version
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfTransformer
from ..records import streaming_fingerprint

STOP_WORDS = tuple(sorted({'a','an','and','are','as','at','be','by','for','from','in','is','it',
    'of','on','or','that','the','this','to','was','were','with',
    'al','con','de','del','el','en','es','la','las','los','o','para','por','que','un','una','y'}))
TOKEN_PATTERN = r'[^\W\d]\w*'


def term_counts(text):
    # Inputs: text.
    # Does: Tokenize text and count its normalized terms.
    # Output: Term frequencies.
    return Counter(t for t in re.findall(TOKEN_PATTERN,text.lower(),re.UNICODE) if t not in STOP_WORDS)


def attach_terms(units):
    # Inputs: units.
    # Does: Attach corpus-level term statistics to each normalized unit.
    # Output: The corpus term metadata and updated units.
    ordered = sorted(units,key=lambda u:u['id'])
    counts = [term_counts(u['text']) for u in ordered]
    vocabulary = sorted({t for row in counts for t in row})
    positions = {term:i for i,term in enumerate(vocabulary)}
    rows,cols,values = [],[],[]
    for i,row in enumerate(counts):
        for term,count in sorted(row.items()):
            rows.append(i); cols.append(positions[term]); values.append(count)
    config = dict(token_pattern=TOKEN_PATTERN,lowercase=True,stop_words=list(STOP_WORDS),
                  stemming=False,norm='l2',use_idf=True,smooth_idf=True,sublinear_tf=False,
                  library='scikit-learn',library_version=version('scikit-learn'))
    scope = dict(unit_ids=[u['id'] for u in ordered],
                 text_revision=streaming_fingerprint([(u['id'],u['text']) for u in ordered]))
    corpus_id = 'corpus-'+streaming_fingerprint([scope,config])[:32]
    idfs = []
    if ordered and vocabulary:
        matrix=csr_matrix((values,(rows,cols)),shape=(len(ordered),len(vocabulary)),dtype=float)
        transformer=TfidfTransformer(norm='l2',use_idf=True,smooth_idf=True,sublinear_tf=False)
        weights=transformer.fit_transform(matrix)
        idfs=[float(v) for v in transformer.idf_]
        for i,unit in enumerate(ordered):
            start, end = weights.indptr[i:i + 2]
            row_weights = dict(zip(weights.indices[start:end], weights.data[start:end]))
            unit['terms']=[dict(term=t,frequency=n,tfidf=float(row_weights[positions[t]]))
                           for t,n in sorted(counts[i].items())]
    for unit in ordered:
        unit['terms_corpus_id']=corpus_id
    return dict(corpus_id=corpus_id,scope=scope,document_count=len(ordered),config=config,
                vocabulary=vocabulary,idf=idfs)
