# -*- coding: utf-8 -*-
"""
Created on Tue Mar 23 16:26:51 2021

@author: Armando Anzellini

Find paper on logistic regression over discriminant function for sex estimation

We'll have search terms as well to search and how they change over time to be
able to really follow it back

"""
import fitz
import streamlit as st
import re
from copy import deepcopy


st.title('PDF Citation Scraper')
# Get authors and years to look for
refs  = st.text_input('Last names and years separated by comas with a semicolon denoting a new reference (e.g., Walker, 2005; Saini et al., 2012): ')
# year   = st.number_input('Year of citation: ', value = 1950, step = 1)
keywords = st.text_input('Keywords separated by a semicolon: ')
simult   = st.checkbox('Check box if keywords and authors should be searched in the same sentence.')

# Ask user to upload a file
uploaded_files = st.file_uploader("Upload single or multiple PDFs...", type="pdf", accept_multiple_files=True)

# direct = 'C:\\Users\\Armando\\Desktop\\'
# file = open(direct + 'Pringle-2012-Establishing forensic search meth.pdf', 'rb')
# file = open(direct + 'Grosman et al 2008 Sahman burial from Levant.pdf', 'rb')
# file = open(direct + 'Garvin et al 2014 Dimorphism cranial trait scores.pdf', 'rb')
# refs = 'Saini, Srivastava, Rai, Shamal, Singh, and Tripathi, 2012; Walker, 2005; Van Gerven, Sheridan, and Adams, 1995'
# refs = 'Witten, Brooks, Fenner, 2000; Schultz, 2008'
# refs = 'Schultz, 2008'
# refs = 'Walker, 2005'

# Define the class and associated functions
class pdf_scraper(object):
    def __init__(self, file, refs, keywords):
        self.file     = file
        self.refs     = refs
        self.keywords = keywords
               
        # take references as input and parse
        refs = refs.replace(' and ', ', ') # remove 'and's at the beginning to make parsing easier
        refs = refs.replace(',,', ',') # remove double commas coming from above
        reflist = refs.split(';')
        reflist = [i.split(',') for i in reflist]
        
        # strip blank spaces within the reference lists to clean up
        for ix in range(len(reflist)):
            reflist[ix] = [i.strip() for i in reflist[ix]]
        
        # if researcher provided full list of authors, provide refs with et al
        # or AAA style if 2 or 3 authors
        intext_refs = []
        for j in reflist:
            if len(j) < 2:
                Exception('At least one of your references is not in the right format!')
            if len(j) == 2:
                intext_refs += [[j[0], j[1]]]
            if len(j) > 3:
                intext_refs += [[j[0] + ' et al.', j[-1]]]
            if len(j) == 3:
                co_auth1 = f'{j[0]} and {j[1]}'
                co_auth2 = f'{j[0]}, {j[1]}'
                intext_refs += [[co_auth1, j[-1]], [co_auth2, j[-1]]]
            if len(j) == 4:
                aaa_style1 = f'{j[0]}, {j[1]}, and {j[2]}'
                aaa_style2 = f'{j[0]}, {j[1]}, {j[2]}'
                intext_refs += [[aaa_style1, j[-1]],[aaa_style2, j[-1]]]
        
        self.reflist     = reflist
        self.intext_refs = intext_refs
     
    def findall(string, substring):
        # function finds all locations of a substring in a string without regex
        locs = []               # start logging locations
        l = len(substring)      # get the length of the substring
        i = string.find(substring) #find the first instance
        while i != -1: #if found first append to locations then restart from previous location
            locs += [i]
            i = string.find(substring, i+l)
        return locs
        
    def read_pdf(self):
        
        # Open the pdf as text per page and per paragraph (return [page, paragraph])
        with fitz.open(stream=self.file.read(), filetype = "pdf") as doc: # opening BytesIO stream
            text = []
            for page in doc:
                text += [[page.number + 1, page.get_text("blocks")]]
        
        # Separate Reference paragraphs from text paragraphs
        # create function to easily return necessary indices and break out of loop
        def workscited(txt):
            for i in reversed(range(len(txt))):
                for j in range(len(txt[i][1])):
                    for k in txt[i][1][j]:
                        if 'references' in str(k).casefold():
                            return i,j
                        elif 'literature cited' in str(k).casefold():
                            return i,j
                for j in range(len(txt[i][1])):
                    for k in txt[i][1][j]:
                        if 'acknowledgments' in str(k).casefold():
                            return i,j
                        elif 'acknowledgment' in str(k).casefold():
                            return i,j
                        
        pg, par = workscited(text)
        
        # Create list of works cited paragraphs
        works_cited = []
        for pag in range(pg, len(text)): 
            if pag == pg:
                for p in range(par + 1, len(text[pag][1])):
                    works_cited += [text[pag][1][p][4]]
            else:
                works_cited += [i[4] for i in text[pag][1]]
        
        # Split into individual references using REGEX
        references = []
        for i in works_cited:
            references += re.split(r'\n(?=[\[|\d|\(])', i)
        
        # Replace line break characters for each citation
        for ix in range(len(references)):
            references[ix] = references[ix].replace('\n', ' ').replace('- ', '')
        
        # 
        references_fixed = []
        for ix in range(len(references)-2):
            pattern1 = r'\d{1,2}[^\.\]]'
            if re.match(pattern1, references[ix+1]):
                references_fixed += [' '.join(references[ix:ix+2])]
                ix += 2
            elif re.match(pattern1, references[ix]):
                pass
            else:
                references_fixed += [references[ix]]
        
          
            """
            this one still shows up as separated in references, how to fix?
            Year has to be in the same line as authors!!!
            '[17] B.B. Ellwood, D.W. Owsley, S.H. Ellwood, P.A. Mercado-Allinger, Search for the grave of the hanged Texas gunfighter, William Preston Longley, Hist. Arch. 28',
            '(1994) 94–112.',
             """
             
        # Separate the reading portion from the finding matches portion in order to create a "find keyword" function
        
        # find out if pdf has numbered citations or in-text citations
        # function that finds location of reference authors and year and gets ref number
        def ref_num(paragraph, ref):
            year         = ref[-1]
            foo = r''    # start regex expression for ref number
            for i in ref[:-1]:
                foo += '(?:%s)\D+' % i # add all authors to regex exp 
            foo += '.*' + f'(?:{year}).+[^[\d]'     # add year at the end of the regex expression
            found = re.search(foo, paragraph)    # find starting location
            if found:
                loc     = found.span()
                cite    = paragraph[0:loc[1]]
                r_num   = re.match(r'\W*(\d{1,2})[\.|\]]', cite) # extract reference number
                ref_num = re.findall(r'\d{1,2}', r_num.group())[0]
            else:
                ref_num = ''
            return ref_num, ', '.join(ref)
            
        # use func to find the ref_num if numbered references present
        try:
            cite_nums = []
            num_refs  = []
            for reference in deepcopy(references):
                for ref in self.reflist:
                    cite_num, cite = ref_num(reference, ref)
                    if cite_num:
                        cite_nums += [cite_num]
                        num_refs  += [[cite_num, cite]]
        except:
            cite_nums = []
            num_refs  = []
        
        self.num_refs = num_refs
        
        # Remove unneccessary tuple values from paragraph and clean up for readability
        paras = []
        for i in text:
            for j in i[1]:
                paras += [[i[0],j[4].replace('\n', ' ').replace('- ', '')]]
                
        # Remove any paragraphs that are smaller than 50 characters
        # This prevents titles of journals and headers from being included
        paras = [i for i in paras if len(i[1]) > 61]
        
        # Remove any paragraph beginning with Fig and image
        paras = [i for i in paras if not i[1].startswith('Fig')]
        paras = [i for i in paras if not i[1].startswith('<image')]
        
        # Remove any paragraph that is just affiliation or information or abstract
        paras = [i for i in paras if not i[1].startswith('Grant sponsor:')]
        paras = [i for i in paras if not i[1].startswith('*Correspondence')]
        paras = [i for i in paras if not i[1].startswith('* Corresponding author')]
        paras = [i for i in paras if not i[1].startswith('Received')]
        paras = [i for i in paras if not i[1].startswith('DOI:')]
        paras = [i for i in paras if not i[1].startswith('DOI ')]
        paras = [i for i in paras if not i[1].startswith('TABLE')]
        paras = [i for i in paras if not i[1].startswith('Keywords: ')]
        paras = [i for i in paras if not i[1].startswith('Article history: ')]
        
        paras = [i for i in paras if not ' All rights reserved. ' in i[1]] # ending with this is also how you find the abstract in some journals
        paras = [i for i in paras if not '@' in i[1]]
        paras = [i for i in paras if not ' www.'  in i[1]]
        paras = [i for i in paras if not ' w ww.' in i[1]]
        
               
        # find and remove duplicated paragraphs since they're usually metadata
        # use length to reduce number of possible duplicates
        non_dups = [paras[0][1][:-5]] # have to do -5 to remove page numbers from duplicates
        dups     = []
        for ix in range(1, len(paras)):
            if paras[ix][1][:-5] in non_dups:
                dups += [ix]
            elif paras[ix][1] not in non_dups:
                non_dups += [paras[ix][1][:-5]]
        
        # find the first instance of the duplication in order to remove all dups
        if dups:
            for ix in range(len(paras)):
                if paras[ix][1][:-5] == paras[dups[0]][1][:-5] and ix not in dups:
                    dups += [ix]
                
        # sort dups index list to prepare to drop the items in the paras list
        # reverse to avoid changing index while deleting
        dups.sort(reverse=True)
        
        # go through paras and remove by index
        for i in dups:
            del paras[i]
        
        # Remove paragraphs that are mostly digits since they represent a table
        for i in paras:
            numcount = sum(c.isdigit() for c in i[1])
            letcount = sum(c.isalpha() for c in i[1])
            if numcount > letcount:
                paras.remove(i)


        # use regex to find where number ranges between brackets may include cite nums
        range_cite = []
        for paragraph in paras:
            for num in cite_nums:
                pattern    = r'[\[|\(|,](\d+[-|–]\d+)[\]|\|,)]' # either long or short dash
                posranges  = re.findall(pattern, paragraph[1])
                for dash in posranges:
                    rango     = re.split(r'-|–', dash)
                    if int(rango[0]) <= int(num) <= int(rango[1]):
                        range_cite += [f'{dash}']
                
        # Now add citation numbers in generalized formats to be found in txt                
        if range_cite:
            citations = range_cite
        else:
            citations = []
            
        if cite_nums:
            for num in cite_nums:
                citations += [f'({num})', f', {num})', f'({num},', f', {num},', 
                              f',{num})', f',{num},', f'[{num}]', f', {num}]',
                              f'[{num},', f', {num},', f',{num}]', f',{num},']
                
        self.cite_nums = cite_nums
        
        # Checking if the numbered refs return anything and then creating citations
        # based on that. Use function for in-text citations
        if not cite_nums:
            citations = []
            for authors, year in self.intext_refs:
                citations += [authors + ', ' + str(year), 
                              authors + ' (%s)' % str(year),
                              authors + str(year)]
                     
        orphan = []
        for ix in range(3, len(paras)):
            page = paras[ix][0]
            text = paras[ix][1]
            while text[-2] != '.':
                text += paras[ix + 1][1]
                ix += 1
            while text[0].islower() == True:
                text = paras[ix - 1][1] + text
                ix-= 1
            orphan += [[page, text]]
            
        # find duplicates in orphan to reduce size of list
        # using the same proceedure as above
        non_dups = [orphan[0][1]] 
        dups     = []
        for ix in range(1, len(orphan)):
            if orphan[ix][1] in non_dups:
                dups += [ix]
            elif orphan[ix][1] not in non_dups:
                non_dups += [orphan[ix][1]]
                
        # sort dups index list to prepare to drop the items in the paras list
        # reverse to avoid changing index while deleting
        dups.sort(reverse=True)
        
        # go through paras and remove by index
        for i in dups:
            del orphan[i]
            
        return orphan, citations
            
        # Orphan is still orphaning some paragraphs leading to duplications not being caught by the dups search
    
    
    def find_match(self):
        
        orphan, citations  = self.read_pdf()
        
        # Find all paragraphs where citation is found and return paragraph and page in list  
        match  = [s for s in deepcopy(orphan) if citations[0] in s[1]]
        for r in citations[1:]:
            match += [s for s in deepcopy(orphan) if r in s[1]]
        
        
        # Sort matches by page number prior to finding sentences
        match = sorted(match, key=lambda x: x[0])
        
        # define function that finds the index of a duplicated value in a list
        def duplicates(lst, item):
            return [i for i, x in enumerate(lst) if x == item]
        
        # split match list into pages and txt to find duplicated texts
        pgs = []
        txt = []        
        for i in match:
            pgs += [i[0]]
            txt += [i[1]]
            
        # go through txt to find duplicated values and drop from pgs and txt
        dup_ix = []
        for j in range(len(txt)):
            x = duplicates(txt, txt[j]) # use function above to get ix of dups
            dup_ix  += [[y for y in x if len(x) >=2]] #only collect dupd ixs
            
        dup_ix  = list(filter(None, dup_ix)) # remove all empty items
        dup_ix  = set([item[1] for item in dup_ix]) # remove duplicate ixs keep last
            
        # Now use collected indices to remove the duplicated values from match
        for i in sorted(list(dup_ix), reverse=True):    # reversed to avoid changing indices
            match.pop(i)
            
        # Get sentences in which the match occurred for citations
        # Get sentences related to all citations
        sentences = []
        for i in match:
            temp_i = re.split(r'\.\s(?=[A-Z])', i[1])
            for s in temp_i:
                for cite in citations:
                    if s.find(cite) != -1:
                        sentences += [s]
            
        sentences = list(set(sentences)) # reduces matches when exactly the same
        
        # Remove items in sentences if shorter than 6 characters long
        for ix in reversed(range(len(sentences))):
            if len(sentences[ix]) <= 6:
                del sentences[ix]
                
        # go through and find partial duplicates in sentences
        duplist = []
        for i in range(len(sentences)):
            for j in range(i+1, len(sentences)):
                if sentences[i] in sentences[j] and len(sentences[i]) <= len(sentences[j]):
                    duplist += [i]
                elif sentences[i] in sentences[j] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                elif sentences[j] in sentences[i] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                elif sentences[j] in sentences[i] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                    
        # ensure matchdup has unique values
        duplist = list(set(duplist))
       
        # Remove items in sentences by index from duplist
        duplist.sort(reverse=True)
        
        for i in duplist:
            del sentences[i]
        
        # go through and find partial duplicates in matches
        matchdup = []
        for i in range(len(match)):
            for j in range(i+1, len(match)):
                if match[i][1] in match[j][1] and len(match[i][1]) <= len(match[j][1]):
                    matchdup += [i]
                elif match[i][1] in match[j][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                elif match[j][1] in match[i][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                elif match[j][1] in match[i][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                    
        # ensure matchdup has unique values
        matchdup = list(set(matchdup))
        
        # Remove items in sentences by index from duplist
        matchdup.sort(reverse=True)
        
        for i in matchdup:
            del match[i]
        
        # only keep matches that match to items in sentences
        real_match = []
        for s in sentences:
            for p in match:
                if s in p[1]:
                    if p not in real_match:
                        real_match += [p]
                        
        real_match.sort()
        
        
        return real_match, sentences
    
    def find_keyword(self):
        
        orphan, citation = self.read_pdf()
        
        kwords = self.keywords
        
        # Find all paragraphs where citation is found and return paragraph and page in list  
        match  = [s for s in deepcopy(orphan) if kwords[0] in s[1]]
        for r in kwords[1:]:
            match += [s for s in deepcopy(orphan) if r in s[1]]
        
        
        # Sort matches by page number prior to finding sentences
        match = sorted(match, key=lambda x: x[0])
        
        # define function that finds the index of a duplicated value in a list
        def duplicates(lst, item):
            return [i for i, x in enumerate(lst) if x == item]
        
        # split match list into pages and txt to find duplicated texts
        pgs = []
        txt = []        
        for i in match:
            pgs += [i[0]]
            txt += [i[1]]
            
        # go through txt to find duplicated values and drop from pgs and txt
        dup_ix = []
        for j in range(len(txt)):
            x = duplicates(txt, txt[j]) # use function above to get ix of dups
            dup_ix  += [[y for y in x if len(x) >=2]] #only collect dupd ixs
            
        dup_ix  = list(filter(None, dup_ix)) # remove all empty items
        dup_ix  = set([item[1] for item in dup_ix]) # remove duplicate ixs keep last
            
        # Now use collected indices to remove the duplicated values from match
        for i in sorted(list(dup_ix), reverse=True):    # reversed to avoid changing indices
            match.pop(i)
            
        # Get sentences in which the match occurred for kwords
        # Get sentences related to all kwords
        sentences = []
        for i in match:
            temp_i = deepcopy(i[1].split('. '))
            for s in temp_i:
                for cite in kwords:
                    if s.find(cite) != -1:
                        sentences += [s]
            
        sentences = list(set(sentences)) # reduces matches when exactly the same
        
        # Remove items in sentences if shorter than 6 characters long
        for ix in reversed(range(len(sentences))):
            if len(sentences[ix]) <= 6:
                del sentences[ix]
                
        # go through and find partial duplicates in sentences
        duplist = []
        for i in range(len(sentences)):
            for j in range(i+1, len(sentences)):
                if sentences[i] in sentences[j] and len(sentences[i]) <= len(sentences[j]):
                    duplist += [i]
                elif sentences[i] in sentences[j] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                elif sentences[j] in sentences[i] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                elif sentences[j] in sentences[i] and len(sentences[i]) > len(sentences[j]):
                    duplist += [j]
                    
        # ensure matchdup has unique values
        duplist = list(set(duplist))
       
        # Remove items in sentences by index from duplist
        duplist.sort(reverse=True)
        
        for i in duplist:
            del sentences[i]
        
        # go through and find partial duplicates in matches
        matchdup = []
        for i in range(len(match)):
            for j in range(i+1, len(match)):
                if match[i][1] in match[j][1] and len(match[i][1]) <= len(match[j][1]):
                    matchdup += [i]
                elif match[i][1] in match[j][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                elif match[j][1] in match[i][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                elif match[j][1] in match[i][1] and len(match[i][1]) > len(match[j][1]):
                    matchdup += [j]
                    
        # ensure matchdup has unique values
        matchdup = list(set(matchdup))
        
        # Remove items in sentences by index from duplist
        matchdup.sort(reverse=True)
        
        for i in matchdup:
            del match[i]
        
        # only keep matches that match to items in sentences
        real_match = []
        for s in sentences:
            for p in match:
                if s in p[1]:
                    if p not in real_match:
                        real_match += [p]
                        
        real_match.sort()
        
        
        return real_match, sentences

    def return_match(self):
                     
        match, sentences = self.find_match()
        
        st.title(self.file.name + ' Finding: ' + str(self.refs))
        
        # Add note to 
        if self.cite_nums:
            st.markdown('**References numbered in this text as:**')
            for cite in self.num_refs:
                st.markdown(f'**_{cite[0]} -> {cite[1]}_**')
        
        # Loop over all matches and return the formatted paragraphs
        for i in match:
            output = []
            sent_ixs = []
            for j in sentences:
                strt = i[1].find(j)
                if strt != -1:
                    end  = strt + len(j)
                    sent_ixs += [strt, end]
            sent_ixs.sort()
            st.markdown('**Page %s**' % i[0])
            if sent_ixs[0] != 0:
                output += [i[1][:sent_ixs[0]]] #add beginning of string to output
            for k, l in enumerate(sent_ixs[:-1]):
                #enumerate to subsequently add the sentences and between sentences to output
                output += [i[1][l:sent_ixs[k+1]]]
            if sent_ixs[-1] != 0:
                output += [i[1][sent_ixs[-1]:]] # add end of string to output
            if sent_ixs[0] == 0: # if match sentences start @ beginning of paragraph
                for x in range(len(output)): 
                    if x % 2 == 0:  # if the index of output is even
                        output[x] = '**' + output[x] + '**' # add markdown bold
            elif sent_ixs[0] != 0: # if match sentences start @ beginning of paragraph
                for x in range(len(output)): 
                    if x % 2 != 0:  # if the index of output is odd
                        output[x] = '**' + output[x] + '**' # add markdown bold
            # Flatten ouput list into a single string for output and write to st
            st.markdown(''.join(output))
                         
#------------------------------------------------------------------------------

hover_text = 'Click Run to start the scraping'

# Run the program if all criteria are met
if refs and uploaded_files:
    if st.button('Run', help=hover_text):
        for uploaded_file in uploaded_files: 
            pdf_scraper(uploaded_file, refs, keywords).return_match()
            
if keywords and uploaded_files:
    if st.button('Run', help=hover_text):
        for uploaded_file in uploaded_files: 
            pdf_scraper(uploaded_file, refs, keywords).return_match()
            


