import sys
import spacy
import time
import pandas as pd

# setup spacy nlp
nlp = spacy.load('de_core_news_sm', disable=['tagger', 'parser', 'ner', 'textcat'])


def pipe_lemmatize(source_corpus, target_corpus, batch_size=512, n_process=1):
    df = pd.read_csv(source_corpus, sep='\t', names=['en', 'de'])
    df_de = df['de'].fillna("")

    t0 = time.time()
    results = []
    for doc in nlp.pipe(df_de, batch_size=batch_size, n_process=n_process,
                        disable=['tagger', 'parser', 'ner', 'textcat']):
        results.append(' '.join([x.lemma_ for x in doc]))
    t1 = time.time()
    print("Time to get lemmas from {}: {}".format(source_corpus, (t1-t0)))

    df['lemma'] = results
    df.to_csv(target_corpus, sep='\t', header=False, index=False)

    return df


if __name__ == "__main__":
    pipe_lemmatize(sys.argv[1], sys.argv[1] + "_lemma")

