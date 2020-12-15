#!/usr/bin/env python
# coding: utf-8


import re
import sys
import os
from pprint import pprint
from pandas import Series, DataFrame
import pandas as pd
import numpy as np
import argparse


REGEX1 = r'\[\w+/\*?\w+\W*\w+\]'

def annot_prep(annot_text):      # s'applique aux textes dans l'annotation (Chaîne de caractères) -- tester l'existence d'une prep
    if len(annot_text) >= 3:
        if annot_text[:3] in prep:
            annot_text_new = annot_text[:3]
        elif annot_text[:2] in prep:
            annot_text_new = annot_text[:2]
        elif annot_text[0] in prep:
            annot_text_new = annot_text[0]
        else:
            annot_text_new = None
    elif len(annot_text) == 2:
        if annot_text in prep:
            annot_text_new = annot_text
        elif annot_text[0] in prep:
            annot_text_new = annot_text[0]
        else:
            annot_text_new = None
    elif len(annot_text) == 1:
        if annot_text in prep:
            annot_text_new = annot_text
        else:
            annot_text_new = None
    else:
        annot_text_new = None
    return annot_text_new

def annot_post(annot_text):         # s'applique aux textes dans l'annotation (Chaîne de caractères) -- tester l'existence d'une post
    if len(annot_text) >= 2:
        if annot_text[-2:] in post:
            annot_text_new = annot_text[-2:]
        elif annot_text[-1:] in post:
            annot_text_new = annot_text[-1:]
        else:
            annot_text_new = None
    elif len(annot_text) == 1:
        if annot_text in post:
            annot_text_new = annot_text
        else:
            annot_text_new = None
    else:
        annot_text_new = None
    return annot_text_new

def adp_out(annot):                                              # e.x. annot = '[經由大使館的那個門上/Entrance]'
    ind_slash = annot.index('/')
    annot_text = annot[1:ind_slash]
    if annot_prep(annot_text) and annot_post(annot_text):         # prep and post
        prep = annot_prep(annot_text)
        post = annot_post(annot_text)
        annot = list(annot)
        prep = list(prep)
        post = list(post)
        move_prep = "".join([annot.pop(annot.index(prep[i])) for i in range(len(prep))])
        annot.insert(0,move_prep)
        move_post = "".join([annot.pop(annot.index(post[i])) for i in range(len(post))])
        annot.append(move_post)
        annot = "".join(annot)
    elif annot_prep(annot_text) and not annot_post(annot_text):   # prep and not post
        prep = annot_prep(annot_text)
        annot = list(annot)
        prep = list(prep)
        move_prep = "".join([annot.pop(annot.index(prep[i])) for i in range(len(prep))])
        annot.insert(0,move_prep)
        annot = "".join(annot)
    elif not annot_prep(annot_text) and annot_post(annot_text):   # not prep but post
        post = annot_post(annot_text)
        annot = list(annot)
        post = list(post)
        move_post = "".join([annot.pop(annot.index(post[i])) for i in range(len(post))])
        annot.append(move_post)
        annot = "".join(annot)
    return annot

def new_annotlist(example):
    list_annot = re.findall(REGEX1,example)
    list_annot_new = [None]*len(list_annot)
    for annot in list_annot:                        # e.x. '[由大使館的那個門/Entrance]'
        ind_annot = list_annot.index(annot)
        ind_slash = annot.index('/')
        if annot[ind_slash:].isupper():             # éliminer les mots-clés
            list_annot_new[ind_annot] = annot
        elif not annot[ind_slash:].isupper():
            annot_new = adp_out(annot)
            list_annot_new[ind_annot] = annot_new
    return list_annot_new                           # e.x. ['[江澤民/Self-Mover]', '由[後門/Entrance]', '[進去/PATH-DEICTIC]']

def load_patterns(filename):
    with open(filename,'r') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()!='']
    patterns = {}
    regex = r'^%%PATTERN: (.+)\(\d+/\d+\)$'
    for line in lines:
        if line.startswith('##') or line == '':
            continue
        elif line.startswith('%%PATTERN') and '+nom' not in line:       # nominalized verbs deleted
            name = re.search(regex,line).group(1)
            patterns[name] = []
        elif '+nom' in line:
            continue
        else:
            patterns[name].append(line)
    
    for pattern in patterns.keys():                                     # asterisk
        for example in patterns[pattern]:
            if '*' in example:
                list_ex = patterns[pattern]
                ind_ex = list_ex.index(example)
                example_new = re.sub(r'\[(\w+)/\*\w+\W*\w+\]',r'\1',example)
                list_ex[ind_ex] = example_new
    return patterns

def adp_outannot(patterns):
    for pattern in patterns.keys():                                     # annotation corrected(adp in annotation)
        for example in patterns[pattern]:
            list_ex = patterns[pattern]
            ind_ex = list_ex.index(example)
            list_annot = re.findall(REGEX1,example)
            list_annot_new = new_annotlist(example)
            if list_annot_new != list_annot:
                for i in range(len(list_annot)):
                    if list_annot_new[i-1] != list_annot[i-1]:
                        example_new2 = example.replace(list_annot[i-1],list_annot_new[i-1]).replace(list_annot[i],list_annot_new[i])
                        list_ex[ind_ex] = example_new2
    return patterns

# Segmenter chaque exemple en tuple de None (..., None) ou de rôle (..., Speaker)
def segment(ex):
    segments = []
    segment = ''
    annotated = False
    for char in ex:
            if char == '[': # start of annotated segment
                if annotated:
                    raise SyntaxError(ex)
                if segment != '':
                    segments.append((segment, None))
                    segment = ''
                annotated = True
            elif char == ']': # end of annotated segment
                if not annotated:
                    raise SyntaxError(ex)
                segments.append(tuple(segment.split('/')))
                segment = ''
                annotated = False
            else:
                segment += char
    if segment != '':
        segments.append((segment, None))
    return segments

# Définir une fonction qui va s'applique à tous les fichier 'tag'.
def tup_seg(filename):
    dic_tag = load_patterns(filename)
    pat_tup = {}
    for key in dic_tag.keys():
        pat_tup[key] = []
        for example in dic_tag[key]:
            try:
                tup = segment(example)
            except SyntaxError as SE:
                tup = ('', None)
                ex = SE.args[0]
                print(filename, ':', ex)
            pat_tup[key].append(tup)
    return pat_tup


# Deux fonctions à faire pour obtenir tuple ((..., rôle), Left, Right)
def replace(list_tup_ex):       # list_tup_ex --- liste de tuples qui composent un exemple
    list_tupLRtup_ex = [(tup,list_tup_ex[list_tup_ex.index(tup)-1],list_tup_ex[list_tup_ex.index(tup)+1]) for tup in list_tup_ex if tup[1] and not tup[1][1:].isupper()]
    return list_tupLRtup_ex

def del_rep(tupLRtup_ex):      # tupLRtup_ex --- tuples de 3 éléments ((...,R),(...,None),(...,R)) du résultat de la fonction replace(list_tup_ex)
    if tupLRtup_ex[1][1] and not tupLRtup_ex[2][1]:                # L taggé, R non taggé
        tupLR_ex = (tupLRtup_ex[0],'',tupLRtup_ex[2][0])
    elif (not tupLRtup_ex[1][1]) and tupLRtup_ex[2][1]:            # L non, R taggé
        tupLR_ex = (tupLRtup_ex[0],tupLRtup_ex[1][0],'')
    elif (not tupLRtup_ex[1][1]) and (not tupLRtup_ex[2][1]):      # L et R non taggés
        tupLR_ex = (tupLRtup_ex[0],tupLRtup_ex[1][0],tupLRtup_ex[2][0])
    else:                                                          # L et R taggés
        tupLR_ex = (tupLRtup_ex[0],'','')
    return tupLR_ex


# Trois fonctions à faire pour obtenir tuple ((..., rôle), prep, post)
def l_prep(L):      # s'applique aux éléments à gauche (Chaîne de caractères) -- tester l'existence d'une prep
    if len(L) >= 3:
        if L[-3:] in prep:
            L_new = L[-3:]
        elif L[-2:] in prep:
            L_new = L[-2:]
        elif L[-1] in prep:
            L_new = L[-1]
        else:
            L_new = None
    elif len(L) == 2:
        if L in prep:
            L_new = L
        elif L[-1] in prep:
            L_new = L[-1]
        else:
            L_new = None
    elif len(L) == 1:
        if L in prep:
            L_new = L
        else:
            L_new = None
    else:
        L_new = None
    return L_new

def r_post(R):         # s'applique aux éléments à droit (Chaîne de caractères) -- tester l'existence d'une post
    if len(R) >= 2:
        if R[:2] in post:
            R_new = R[:2]
        elif R[0] in post:
            R_new = R[0]
        else:
            R_new = None
    elif len(R) == 1:
        if R in post:
            R_new = R
        else:
            R_new = None
    else:
        R_new = None
    return R_new

def transf(tupLR_ex):   # s'applique aux tuples de 3 éléments(tupLR_ex) pour les transformer en tuple ((..., rôle), prep, post)
    tup_pr_po = (tupLR_ex[0],l_prep(tupLR_ex[1]),r_post(tupLR_ex[2]))
    return tup_pr_po

# Dictionnaire de fréquence et de pourcentage
# Définir une fonction qui s'applique à chaque valeur de la clé (pattern) de mvn_adp --- x qui est une grande liste
# examples are a list of lists of tuples

def freq_adp(examples):
    freq = {}
    for example in examples:   # example is a list of tuples
        for ((_, role), prep, post) in example: # a tag is a tuple ((text, role), prep, post)
            if role not in freq.keys():
                freq[role] = {'prep': {}, 'post': {}}
            if prep not in freq[role]['prep']:
                freq[role]['prep'][prep] = 1
            else:
                freq[role]['prep'][prep] += 1
            if post not in freq[role]['post']:
                freq[role]['post'][post] = 1
            else:
                freq[role]['post'][post] += 1
    for role in freq:                   # rôle
        for pos in freq[role]:          # 'prep' ou 'post'
            n = sum(freq[role][pos].values())
            for adp in freq[role][pos]: # une adposition
                freq[role][pos][adp] /= n
    return freq

# basé sur le dictionnaire 'mvn_adp'
#---------------------------------------------------------------#
# Définir une fonction (s'appliquant à un dic qui est en fait la valeur de la clé: une entrée du dic mvn_adp) pour lister tous les rôles (sans répétition) d'un caractère
def roles(dic_word):
    list_roles = []
    for key_pat in dic_word.keys():
        for list_t in dic_word[key_pat]:
            for t in list_t:
                list_roles.append(t[0][1])
    list_roles = list(set(list_roles))
    return list_roles

def group(dic_word):
    dic_adp_word = {}
    dic_adp_word_rel = {}
    for role in roles(dic_word):
        dic_adp_word[role] = {}
        for (pos, j) in [('prep', 1), ('post', 2)]:
            dic_adp_word[role][pos] = []
            for key_pat in dic_word.keys():
                for list_t in dic_word[key_pat]:
                    for t in list_t:
                        if t[0][1] == role:
                            dic_adp_word[role][pos].append(t[j])
            dic_adp_word[role][pos] = {a:dic_adp_word[role][pos].count(a) for a in dic_adp_word[role][pos]}
    return dic_adp_word

# Définir une fonction pour calculer la fréquence relative de chaque adposition dans le dictionnaire dic_adp:
def freqrel(dic_prpo):
    dic_prpo_freqrel = {}
    for adp in dic_prpo:
        freqrel_adp = dic_prpo[adp]/sum(dic_prpo.values())
        dic_prpo_freqrel[adp] = freqrel_adp
    return dic_prpo_freqrel



# 20200927 ajouter le contenu de {'None':{}, ...}

def returnSum(myDict):
    
    sum = 0
    for i in myDict:
        sum = sum + myDict[i]
    
    return sum


# 20201029 définir une fonction pour filtrer un dictionnaire avec le seuil déterminé
# En même temps, on doit vérifier s'il y a des mots disparaissent.
def filter(dic, threshold):
    dic_filtered = {}
    for key_word in dic.keys():
        dic_filtered[key_word] = {}
        for key_role in dic[key_word]:
            dic_filtered[key_word][key_role] = {}
            for key_prpo in dic[key_word][key_role]:
                for key_adp in dic[key_word][key_role][key_prpo]:
                    if dic[key_word][key_role][key_prpo][key_adp] >= threshold:
                        dic_filtered[key_word][key_role][key_adp] = dic[key_word][key_role][key_prpo][key_adp]
    return dic_filtered


# PROCESS CORPUS
# ==============================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-c', '--corpus', help = 'mandarin verbnet database', required=True)
    parser.add_argument('-pr', '--prep', help = 'list of prepositions', required=True)
    parser.add_argument('-po', '--post', help = 'list of postpositions', required=True)
    parser.add_argument('-t', '--threshold', default=0, type=float, help = 'threshold selected according to the objective')
    #parser.add_argument('-o', '--output', help = 'the dictionary generated')

    args = parser.parse_args()

    # Dictionnaire de mvn_tup
    files = [f for f in os.listdir(args.corpus) if f.endswith('.tag')]
    mvn_tup = {}
    t = []
    for file in files:
        filename = args.corpus + file
        t.append(tup_seg(filename))
    for i in range(len(files)):
        mvn_tup[files[i][:-4]] = t[i]

    # padding: ajouter deux ('', None) au début et à la fin de la liste.
    for key_word in mvn_tup.keys():
        for key_pat in mvn_tup[key_word]:
            for list_tup in mvn_tup[key_word][key_pat]:
                list_tup.insert(0,('', None))
                list_tup.append(('', None))

    # mvn_LR : Dictionnaire de tuples de trois élément((..., rôle), Left, Right)
    mvn_LR = {}
    for key_word in mvn_tup.keys():
        mvn_LR[key_word] = {}
        for key_pat in mvn_tup[key_word]:
            mvn_LR[key_word][key_pat] = []
            for list_old in mvn_tup[key_word][key_pat]:
                list_new = [del_rep(t) for t in replace(list_old)]
                mvn_LR[key_word][key_pat].append(list_new)

    # Ouvrir deux documents d'adp et puis chercher l'adp dans tuple de 3 éléments(tupLR_ex), L --- prep, R --- post
    # on obtient puis un dictionnaire d'adp ((..., rôle), prep, post)
    with open(args.prep, 'r') as f:
        prep = [line.strip() for line in f.readlines()]
    with open(args.post, 'r') as f:
        post = [line.strip() for line in f.readlines()]

    # Dictionnaire mvn_adp（basé sur mvn_LR）
    mvn_adp = {}
    for key_word in mvn_LR.keys():
        mvn_adp[key_word] = {}
        for key_pat in mvn_LR[key_word]:
            mvn_adp[key_word][key_pat] = []
            for list_tup in mvn_LR[key_word][key_pat]:
                list_tup_adp = [transf(t) for t in list_tup]
                mvn_adp[key_word][key_pat].append(list_tup_adp)

    # Dictionnaire mvn_adp_freq（basé sur mvn_adp）
    mvn_adp_freq = {}
    for key_word in mvn_adp.keys():
        mvn_adp_freq[key_word] = {}
        for key_pat in mvn_adp[key_word]:
            mvn_adp_freq[key_word][key_pat] = freq_adp(mvn_adp[key_word][key_pat])

    # le nouveau dictionnaire: dic_adp, basé sur le dictionnaire mvn_adp
    dic_adp = {}
    for key_word in mvn_adp.keys():
        dic_adp[key_word] = group(mvn_adp[key_word])

    for key_word in dic_adp.keys():
        for key_role in dic_adp[key_word]:
            for key_prpo in dic_adp[key_word][key_role]:
                dic_adp[key_word][key_role][key_prpo] = freqrel(dic_adp[key_word][key_role][key_prpo])

    # 20200927 modifier le dictionnaire dic_adp [3 possibilité : None, prep, postp]
    for key_word in dic_adp.keys():
        for key_role in dic_adp[key_word]:
            dic_adp[key_word][key_role]['None'] = {}
            for key_prpo in dic_adp[key_word][key_role]:
                if key_prpo == 'post':
                    for key_adp in dic_adp[key_word][key_role][key_prpo]:
                        if not key_adp == None:
                            dic_adp[key_word][key_role][key_prpo][key_adp] = (dic_adp[key_word][key_role][key_prpo][key_adp])/2
                        else:
                            continue
                elif key_prpo == 'prep':
                    for key_adp in dic_adp[key_word][key_role][key_prpo]:
                        if not key_adp == None:
                            dic_adp[key_word][key_role][key_prpo][key_adp] = (dic_adp[key_word][key_role][key_prpo][key_adp])/2
                        else:
                            continue
                else:
                    continue

    # 20200927 supprimer les keys None dans {'prep/post': {None: ...}, ...}
    for key_word in dic_adp.keys():
        for key_role in dic_adp[key_word]:
            for key_prpo in dic_adp[key_word][key_role]:
                if None in dic_adp[key_word][key_role][key_prpo].keys():
                    del dic_adp[key_word][key_role][key_prpo][None]

    for key_word in dic_adp.keys():
        for key_role in dic_adp[key_word]:
            for key_prpo in dic_adp[key_word][key_role]:
                if dic_adp[key_word][key_role]['post'] != {} and dic_adp[key_word][key_role]['prep'] != {}:
                     dic_adp[key_word][key_role]['None'][None] = 1 - (returnSum(dic_adp[key_word][key_role]['post']) + returnSum(dic_adp[key_word][key_role]['prep']))
                elif dic_adp[key_word][key_role]['post'] != {} and dic_adp[key_word][key_role]['prep'] == {}:
                    dic_adp[key_word][key_role]['None'][None] = 1 - returnSum(dic_adp[key_word][key_role]['post'])
                elif dic_adp[key_word][key_role]['post'] == {} and dic_adp[key_word][key_role]['prep'] != {}:
                    dic_adp[key_word][key_role]['None'][None] = 1 - returnSum(dic_adp[key_word][key_role]['prep'])
                elif dic_adp[key_word][key_role]['post'] == {} and dic_adp[key_word][key_role]['prep'] == {}:
                    dic_adp[key_word][key_role]['None'][None] = 1

    df = pd.DataFrame(columns = ['lemma', 'role','adp', 'freq'])
    for lemma, lemma_dic in filter(dic_adp, args.threshold).items():
        for role, role_dic in lemma_dic.items():
            for adp, freq in role_dic.items():
                df.loc[-1] = [lemma, role, adp, freq]
                df.index = df.index + 1
    df = df.sort_index()
    df.to_csv('dic_v.csv', index = False)
