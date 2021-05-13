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
keywords = st.text_input('Keywords separated by a comma: ')
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
# refs = 'Walker, 2008'
# keywords = 'clandestine'

# Define the class and associated functions
class pdf_scraper(object):
    def __init__(self, file, refs, keywords):
        self.file     = file
        self.refs     = refs
        
        # take references as input and parse
        refs = refs.replace(' and ', ', ') # remove 'and's at the beginning to make parsing easier
        refs = refs.replace(',,', ',') # remove double commas coming from above
        
        # check if value has been given before turning into list
        if not refs:
            self.empty_ref = True # give a value to be checked later if empty
        else:
            self.empty_ref = False
            
        # check if keyword values have been given
        if not keywords:
            self.empty_kw = True # give a value to be checked later if empty
        else:
            self.empty_kw = False
                
        # Make refs into a list
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
                
        #split the keywords and clean up for searching
        keywords = keywords.split(',')
        keywords = [k.strip() for k in keywords]
        
        
        self.keywords    = keywords
        self.reflist     = reflist
        self.intext_refs = intext_refs

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
        
        # Create lists of works cited paragraphs and regular paragraphs
        works_cited = []
        paras  = []
        last_page   = []
        for pag in range(len(text)):
            if pag == pg:
                for p in range(par + 1, len(text[pag][1])):
                    works_cited += [text[pag][1][p][4]]
                for i in range(par):
                    last_page   += [[text[pag][0], 
                                     text[pag][1][i][4].replace('\n', ' ').replace('- ', '')]]
            elif pag > pg:
                works_cited += [i[4] for i in text[pag][1]]
            else:
                for p in range(len(text[pag][1])):
                    paras +=[[text[pag][0],
                                   text[pag][1][p][4].replace('\n', ' ').replace('- ', '')]]
        
        paras += last_page
        
        # retrieve abstract in case needed later
        try:
            abstract = [i for pg, i in paras if i.startswith('ABSTRACT ')][0]
        
            if not abstract.endswith('. '):
                ix = paras.index([1,abstract])
                abstract = abstract + paras[ix+1][1]
        except:
            abstract = []
        
        # make sure the abstract is not orphaned!!
        
        # Remove all paragraphs that are entirely in upper case (headers)
        paras = [i for i in paras if not i[1].isupper()]
        
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
        paras = [i for i in paras if not i[1].startswith('KEY WORDS ')]
        paras = [i for i in paras if not i[1].startswith('ABSTRACT ')]
        paras = [i for i in paras if not i[1].startswith('Article history: ')]
        
        paras = [i for i in paras if not i[1].endswith(', Inc. ')]
        
        paras = [i for i in paras if not ' All rights reserved. ' in i[1]] # ending with this is also how you find the abstract in some journals
        paras = [i for i in paras if not '@' in i[1]]
        paras = [i for i in paras if not ' www.'  in i[1]]
        paras = [i for i in paras if not ' w ww.' in i[1]]
        
        # Remove paragraphs that are mostly digits since they represent a table
        for i in paras:
            numcount = sum(c.isdigit() for c in i[1])
            letcount = sum(c.isalpha() for c in i[1])
            if numcount > letcount:
                paras.remove(i)

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
        
        # Delete all sections shorter than 61 characters since likely not part of paragraph
        paras = [i for i in paras if len(i[1]) > 61]
               
        
        # Now to work on references
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

        # use regex to find where number ranges between brackets may include cite nums
        range_cite = []
        for paragraph in paras:
            for num in cite_nums:
                pattern    = r'[\[|\(|,](\d+[-|–]\d+)[\]|\)|,)]' # either long or short dash
                posranges  = re.findall(pattern, paragraph[1])
                for dash in posranges:
                    rango     = re.split(r'-|–', dash)
                    if int(rango[0]) <= int(num) <= int(rango[1]):
                        range_cite += [f'{dash}']
        
        self.range_cite = range_cite                
        self.cite_nums = cite_nums
        
        # Checking if the numbered refs return anything and then creating citations
        # based on that. Use function for in-text citations
        '''
        if not cite_nums:
            citations = []
            for authors, year in self.intext_refs:
                citations += [authors + ', ' + str(year), 
                              authors + ' (%s)' % str(year),
                              authors + ' ' + str(year)]
        '''
        """
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
        
        # Orphan is still orphaning some paragraphs leading to duplications not being caught by the dups search
    
        """
        
        #self.paras = paras
        #self.citations = citations
        
        return paras
            
    def find_citations(self, paras, reflist):
        
        # defining regex function to find sentences with in-text citations
        def intext_match(paragraph, ref):
            pattern = rf'({ref[0]}[^A-Za-z]+{ref[1]})'
            citations = re.findall(pattern, paragraph[1])
            sentences = []
            temp_i = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            for s in temp_i:
                for cite in set(citations):
                    if s.find(cite) != -1:
                        sentences += [s]
            return sentences
        
        # defining regex function to find sentences with numbered citations
        # def numbered_citations(paragraph, refnum):
        def num_match(paragraph, refnum):
            pattern = r'[\[|\(|,]' + refnum + '[\]|\)|,)](?!\d{3})'
            sentences = []
            temp_i = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            for s in temp_i:
                if re.search(pattern, s):
                    sentences += [s]
            return sentences
        
        # defining function that finds sentences with the ref intervals
        def range_match(paragraph, ref_interval):
            pattern = rf'[\[|\(|,]({ref_interval})[\]|\)|,]'
            sentences = []
            temp_i = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            for s in temp_i:
                if re.search(pattern, s):
                    sentences += [s]
            return sentences
        
        # Get sentences in which the match occurred for in-text citations   
        if not self.cite_nums:
            sentences = []
            for ref in reflist:
                for paragraph in paras:
                    sentences += intext_match(paragraph, ref)
        
        # Get sentences if citations are numbered or have a range
        if self.cite_nums:
            sentences = []
            for ref in self.cite_nums:
                for paragraph in paras:
                    sentences += num_match(paragraph, ref)
                    
        if self.range_cite:
            for ref in self.range_cite:
                for paragraph in paras:
                    sentences += range_match(paragraph, ref)
        
        # remove any duplication of sentences
        ref_sentences = list(set(sentences))

        return ref_sentences
    
    def find_keywords(self, paras, keywords):
        
        def keyword_match(paragraph, word):
            sentences = []
            temp_i    = re.split(r'\.\s(?=[A-Z])', paragraph[1])
            pattern   = rf'{word}[\s|\W]'
            for s in temp_i:
                if re.search(pattern, s, re.IGNORECASE):
                    sentences += [s]
            return sentences
        
        # Get sentences in which the match occurred for keywords
        # Get sentences related to all keywords     
        sentences = []
        for word in keywords:
            for paragraph in paras:
                sentences += keyword_match(paragraph, word)
        
        # remove any duplication of sentences
        kw_sentences = list(set(sentences))
        
        return kw_sentences

    def find_match(self, together):
        
        paras  = self.read_pdf()

        # check if either refs or keywords are empty
        if not self.empty_ref:
            ref_sentences = self.find_citations(paras, self.reflist)
        else:
            ref_sentences = []

        if not self.empty_kw:
            kw_sentences = self.find_keywords(paras, self.keywords)
        else:
            kw_sentences = []
        
        sentences = []
        if together == True:
            sentences = list(set(kw_sentences) & set(ref_sentences))
        elif together == False:
            sentences = list(set(kw_sentences + ref_sentences))
            
        # Get matching paragraphs that include at least one of the sentences
        match = []
        for paragraph in paras:
            if any(sentence in paragraph[1] for sentence in sentences):
                match += [[paragraph[0], paragraph[1]]]
                
        # Sort matches by page number
        match = sorted(match, key=lambda x: x[0])
        
        return match, sentences
    
    def return_match(self, together):
    
        match, sentences = self.find_match(together)
        
        st.title(self.file.name + ' Finding: ' + str(self.refs))
        
        # Add note to 
        if self.cite_nums:
            st.markdown('**References numbered in this text as:**')
            for cite in self.num_refs:
                st.markdown(f'**_{cite[0]} -> {cite[1]}_**')
        
        # Separating by sentence to rejoin as output
        
        for i in match:
            output = []
            st.markdown('**Page %s**' % i[0])
            temp_i    = re.split(r'\.\s(?=[A-Z])', i[1])
            for s in temp_i:
                if any(sentence in s for sentence in sentences):
                    highlight = '**' + s.strip() + '.**' #add markdown bold
                    output   += [highlight]
                else:
                    output   += [s +'.']
            st.markdown(' '.join(output)) # Flatten ouput list and output
            
        '''
        - fix orphaning at reading of text, not at match
        '''
#------------------------------------------------------------------------------

hover_text = 'Click Run to start the scraping'

# Run the program if all criteria are met
if refs or keywords and uploaded_files:
    run = st.button('Run', help=hover_text)
    if run:
        for uploaded_file in uploaded_files: 
            pdf_scraper(uploaded_file, refs, keywords).return_match(together=simult)




