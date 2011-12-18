#!/usr/bin/python

import math
import os.path

MORSE = dict(zip('ABCDEFGHIJKLMNOPQRSTUVWXYZ', [
    '.-', '-...', '-.-.', '-..', '.', '..-.', '--.', '....',
    '..', '.---', '-.-', '.-..', '--', '-.', '---', '.--.',
    '--.-', '.-.', '...', '-', '..-', '...-', '.--', '-..-',
    '-.--', '--..'
]))

# Read a file containing A-Z only English words, one per line.
WORDS = set(word.strip().upper() for word in open('dict.en').readlines())
WORDS.add('JILL')
# A set of all possible prefixes of English words.
PREFIXES = set(word[:j+1] for word in WORDS for j in xrange(len(word)))

def translate(msg, c_sep=' ', w_sep=' / '):
    """Turn a message (all-caps space-separated words) into morse code."""
    return w_sep.join(c_sep.join(MORSE[c] for c in word)
                      for word in msg.split(' '))

def encode(msg):
    """Turn a message into timing-less morse code."""
    return translate(msg, '', '')

def c_trans(morse):
    """Construct a map of char transitions.

    The return value is a dict, mapping indexes into the morse code stream
    to a dict of possible characters at that location to where they would go
    in the stream. Transitions that lead to dead-ends are omitted.
    """
    result = [{} for i in xrange(len(morse))]
    for i_ in xrange(len(morse)):
        i = len(morse) - i_ - 1
        for c, m in MORSE.iteritems():
            if i + len(m) < len(morse) and not result[i + len(m)]:
                continue
            if morse[i:i+len(m)] != m: continue
            result[i][c] = i + len(m)
    return result

def find_words(ctr, i, prefix=''):
    """Find all legal words starting from position i.

    We generate all possible words starting from position i in the
    morse code stream, assuming we already have the given prefix.
    ctr is a char transition dict, as produced by c_trans.
    """
    if prefix in WORDS:
        yield prefix, i
    if i == len(ctr): return
    for c, j in ctr[i].iteritems():
        if prefix + c in PREFIXES:
            for w, j2 in find_words(ctr, j, prefix + c):
                yield w, j2

def w_trans(ctr):
    """Like c_trans, but produce a word transition map."""
    result = [{} for i in xrange(len(ctr))]
    for i_ in xrange(len(ctr)):
        i = len(ctr) - i_ - 1
        for w, j in find_words(ctr, i):
            if j < len(result) and not result[j]:
                continue
            result[i][w] = j
    return result

def shortest_sentence(wt):
    """Given a word transition map, find the shortest possible sentence.

    We find the sentence that uses the entire morse code stream, and has
    the fewest number of words. If there are multiple sentences that
    satisfy this, we return the one that uses the smallest number of
    characters.
    """
    result = [-1 for _ in xrange(len(wt))] + [0]
    words = [None] * len(wt)
    for i_ in xrange(len(wt)):
        i = len(wt) - i_ - 1
        for w, j in wt[i].iteritems():
            if result[j] == -1: continue
            if result[i] == -1 or result[j] + 1 + len(w) / 30.0 < result[i]:
                result[i] = result[j] + 1 + len(w) / 30.0
                words[i] = w
    i = 0
    result = []
    while i < len(wt):
        result.append(words[i])
        i = wt[i][words[i]]
    return result

def sentence_count(wt):
    result = [0] * len(wt) + [1]
    for i_ in xrange(len(wt)):
        i = len(wt) - i_ - 1
        for j in wt[i].itervalues():
            result[i] += result[j]
    return result[0]

def bad_word(w):
    return len(w) == 1 and w not in 'IA'

def score_ngram(ws, ngrams):
    if any(bad_word(w) for w in ws):
        return -10000
    if len([w for w in ws if len(w) == 1]) > 1: return -1000
    if ws in ngrams:
        p = (ngrams[ws] + 1) / 500.0
        if p > 0.999: p = 0.999
        return math.log(p)
    return math.log(0.01)

def ngrammy_sentence(wt, previous, i, ngrams, cache):
    if i == len(wt):
        return 0, ()
    key = (tuple(previous), i)
    if key not in cache:
        best = None
        best_ws = None
        for w, j in wt[i].iteritems():
            score = score_ngram(previous + (w,), ngrams)
            score_rest, ws = ngrammy_sentence(wt, (previous + (w,))[-2:], j, ngrams, cache)
            wlen = len(ws)
            score = score + score_rest
            if score > best:
                best = score
                best_ws = (w,) + ws
        cache[key] = (best, best_ws)
    return cache[key]

def grab_ngrams(words):
    filename = 'ngrams-%X' % abs(hash(frozenset(words)))
    if not os.path.exists(filename):
        c = 0
        with open(filename, 'w') as out_f:
            with open('gutenberg_ngrams.counted.sorted', 'r') as f:
                for line in f:
                    ws = line.upper().strip().split()
                    if all(w in words for w in ws[1:]):
                        out_f.write(line.upper().strip() + '\n')
                        if c % 100 == 0:
                            print c, ws
                        c += 1
    result = {}
    with open(filename, 'r') as f:
        for line in f:
            ws = line.upper().strip().split()
            result[tuple(ws[1:])] = int(ws[0])
    return result

for msg in ([encode('THIS IS A SECRET MESSAGE')] +
            [encode('THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG')] +
            [encode('PAUL HANKIN')] +
            ['-..-...-...-...-..-.-.-.-.-..-.-.-.-.-.-.-.-.-.-..-...-.']):
    print msg
    # print sorted(set().union(*map(set, w_trans(c_trans(msg)))))
    print sentence_count(w_trans(c_trans(msg)))
    print shortest_sentence(w_trans(c_trans(msg)))
    ng = grab_ngrams(set().union(*map(set, w_trans(c_trans(msg)))))
    r = ngrammy_sentence(w_trans(c_trans(msg)), (), 0, ng, {})
    print r
    for i in xrange(len(r[1]) - 2):
        print score_ngram(tuple(r[1][i:i+2]), ng)


